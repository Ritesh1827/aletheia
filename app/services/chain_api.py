"""Live chain client: trust-fabric backend -> UI models.

Same typed interface as mock_verify (raises UnknownSerialError, never None).
Backend down -> ChainUnavailableError (route renders error state, never all-clear).
"""

from __future__ import annotations

from datetime import datetime, timezone

import httpx

from app import config
from app.models.verify import (
    AnchorProof,
    CheckResult,
    EvidenceFinding,
    ProductIdentity,
    ProvenanceEvent,
    VerificationVerdict,
)
from app.services.mock_verify import UnknownSerialError

CUSTODY_TYPES = {"MANUFACTURED", "HANDOVER_OFFER", "HANDOVER_ACCEPT", "SOLD"}

CHECK_LABELS = {
    "LOT_COMMITMENT": "Lot commitment",
    "CHAIN_INTEGRITY": "Chain integrity",
    "R01": "Identity uniqueness",
    "R02": "Seal / secret",
    "R03": "Lot inclusion",
    "R04": "Movement plausibility",
    "R05": "Quantity overflow",
    "R06": "Route order",
    "R07": "Custody sequence",
    "R08": "Actor authorization",
    "R09": "Integrity",
    "R11": "Lifecycle",
    "R12": "Lifecycle",
    "R13": "Tap counter",
    "R14": "Seal / device",
}

_SEV = {"critical": "critical", "high": "watch", "medium": "watch", "low": "info"}


class ChainUnavailableError(Exception):
    def __init__(self, correlation_id: str = "chain-unreachable") -> None:
        super().__init__("Chain backend unreachable")
        self.correlation_id = correlation_id


def _get(path: str) -> dict:
    base = config.chain_api_base().rstrip("/")
    try:
        r = httpx.get(f"{base}{path}", timeout=15.0)
    except Exception as exc:
        raise ChainUnavailableError() from exc
    if r.status_code == 404:
        raise UnknownSerialError(path)
    if r.status_code >= 500:
        raise ChainUnavailableError(correlation_id=f"chain-{r.status_code}")
    r.raise_for_status()
    return r.json()


def _short(ref: str) -> str:
    return ref[:12] if isinstance(ref, str) and ref.startswith("0x") else str(ref)[:24]


def verify_serial(serial: str) -> VerificationVerdict:
    """Fetch live verdict + bundle + anchor, map to UI models."""
    key = serial.strip()
    try:
        v = _get(f"/products/{key}/verify")
    except UnknownSerialError:
        raise
    if v.get("verdict") == "UNKNOWN":
        raise UnknownSerialError(serial=key)

    try:
        bundle = _get(f"/products/{key}/bundle")
    except (UnknownSerialError, ChainUnavailableError):
        bundle = {"events": [], "lot_proof": {}}
    try:
        anchor = _get(f"/products/{key}/anchor")
    except (UnknownSerialError, ChainUnavailableError):
        anchor = {"anchored": False}

    prod = v.get("product") or {}
    failed = [c for c in v.get("checks", []) if c.get("status") == "fail"]

    checks = []
    for c in v.get("checks", []):
        st = c.get("status", "unknown")
        checks.append(CheckResult(
            id=c.get("id", "?"),
            label=CHECK_LABELS.get(c.get("id", ""), c.get("id", "?")),
            status=st if st in ("pass", "fail", "warn") else "unknown",
            detail=(c.get("reason") or c.get("status", "") or "")[:300]
            or f"Check {c.get('id')} {st}.",
        ))

    findings = [
        EvidenceFinding(
            rule_id=c.get("id", "?"),
            severity=_SEV.get(c.get("severity", "low"), "info"),
            reason=c.get("reason", "")[:500],
            references=[_short(e) for e in c.get("evidence_refs", [])][:6],
            uncertainty="",
            next_step=(c.get("next_step", "") or "")[:300],
        )
        for c in failed
    ]

    timeline = []
    for e in (bundle.get("events") or [])[-12:]:
        ts = e.get("ts")
        when = (datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
                if isinstance(ts, int) else "undated")
        lat, lon = e.get("lat_mdeg"), e.get("lon_mdeg")
        loc = f"{lat / 1000:.3f}, {lon / 1000:.3f}" if lat is not None and lon is not None else ""
        timeline.append(ProvenanceEvent(
            event_id=_short(e.get("event_hash", "?")),
            timestamp=when,
            kind="custody" if e.get("type") in CUSTODY_TYPES else "observation",
            actor=str(e.get("actor", "?"))[:48],
            summary=f"{e.get('type', '?')} · {e.get('biz_step', '')}"[:120],
            location=loc,
        ))

    lot = anchor.get("lot", {}) or bundle.get("lot_proof", {})
    proof = AnchorProof(
        anchor_id=str(anchor.get("anchor_id", "pending")),
        merkle_root=str(lot.get("root", "—"))[:66],
        transaction_hash=str(anchor.get("tx", "batch anchor pending"))[:66],
        block_height=int(anchor.get("block") or 0),
        proof_status="PROOF VALID" if lot.get("status") == "pass" and anchor.get("anchored") else "NOT VERIFIED",
        leaf_count=len(bundle.get("events", [])),
    )

    fails = "; ".join(c.get("reason", "") for c in failed)[:600]
    explanation = (v.get("display", "") + ". " + fails).strip()
    now = datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return VerificationVerdict(
        serial=key,
        verdict=v.get("verdict", "UNKNOWN"),
        explanation=explanation or v.get("display", ""),
        risk_score=int(v.get("risk_score", 0)),
        confidence=f"{v.get('confidence', '?').title()} — risk {v.get('risk_score', 0)}/100.",
        uncertainty="; ".join(v.get("uncertainty", []))[:300],
        retrieved_at=now,
        identity=ProductIdentity(
            serial=key,
            lot_id=str(prod.get("lot_id", "—")),
            product="Unit " + key,
            lifecycle_status=str(prod.get("status", "—")),
            permitted_custodian=str(prod.get("custodian", "—"))[:48],
        ),
        checks=checks,
        findings=findings,
        timeline=timeline,
        proof=proof,
    )
