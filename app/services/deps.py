"""Service seam for M1–M2 (mock-only; real backend plugs in later)."""

from __future__ import annotations

from app import config
from app.models.operations import ActionLogEntry, IncidentDetail, OverviewData
from app.models.verify import VerificationVerdict
from app.services import chain_api, mock_operations, mock_verify

_DEMO_SERIALS = {"TT-DEMO-0001", "TT-DEMO-0002", "TT-DEMO-ERR"}


def get_verification(serial: str) -> VerificationVerdict:
    if config.is_demo() or serial.strip().upper() in _DEMO_SERIALS:
        return mock_verify.verify_serial(serial)
    return chain_api.verify_serial(serial)


def get_overview(severity: str = "all", status: str = "all", fail: bool = False) -> OverviewData:
    return mock_operations.get_overview(severity=severity, status=status, fail=fail)


def get_incident(incident_id: str) -> IncidentDetail:
    return mock_operations.get_incident(incident_id)


def record_incident_action(incident_id: str, action_id: str, note: str = "") -> ActionLogEntry:
    return mock_operations.record_action(incident_id, action_id, note=note)
