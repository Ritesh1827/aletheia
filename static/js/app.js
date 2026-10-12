function toast(message) {
  const slot = document.getElementById("toasts");
  if (!slot) return;
  const el = document.createElement("div");
  el.className = "toast";
  el.textContent = message;
  slot.appendChild(el);
  setTimeout(() => el.remove(), 2600);
}

async function copyText(value, sourceEl) {
  const announce = (msg) => {
    toast(msg);
    if (sourceEl) {
      const prev = sourceEl.getAttribute("aria-label");
      sourceEl.setAttribute("aria-label", msg);
      setTimeout(() => prev && sourceEl.setAttribute("aria-label", prev), 1500);
    }
  };
  try {
    await navigator.clipboard.writeText(value);
    announce("Copied to clipboard.");
  } catch {
    const ta = document.createElement("textarea");
    ta.value = value;
    document.body.appendChild(ta);
    ta.select();
    try {
      document.execCommand("copy");
      announce("Copied to clipboard.");
    } catch {
      announce("Copy failed — select the value manually.");
    }
    ta.remove();
  }
}
window.copyText = copyText;
window.toast = toast;

document.body.addEventListener("htmx:responseError", (event) => {
  toast("Request failed. Retry — this is not an all-clear.");
});
