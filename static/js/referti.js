/* ==========================================================================
   Pagina staff Referti & statistiche (standalone, protetta da password).
   Fornisce gli helper globali usati da reports.js e gestisce il login.
   ========================================================================== */
"use strict";

var state = { isStaff: false };

const loginBox = document.getElementById("staffLogin");
const loginForm = document.getElementById("staffLoginForm");
const loginError = document.getElementById("staffLoginError");
const loginBtn = document.getElementById("staffLoginBtn");
const passwordInput = document.getElementById("staffPassword");
const logoutBtn = document.getElementById("staffLogout");
const reportsBox = document.getElementById("reportsView");
const toastEl = document.getElementById("toast");
let toastTimer = null;

function toast(message) {
  if (!toastEl) return;
  toastEl.textContent = message || "";
  toastEl.classList.add("is-visible");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toastEl.classList.remove("is-visible"), 3200);
}

function showLogin(message) {
  state.isStaff = false;
  if (reportsBox) {
    reportsBox.hidden = true;
    reportsBox.innerHTML = "";
  }
  if (loginBox) loginBox.hidden = false;
  if (logoutBtn) logoutBtn.hidden = true;
  if (loginError) loginError.textContent = message || "";
  if (loginBtn) loginBtn.disabled = false;
  if (passwordInput) {
    passwordInput.value = "";
    passwordInput.focus();
  }
}

function showReports() {
  state.isStaff = true;
  if (loginBox) loginBox.hidden = true;
  if (reportsBox) reportsBox.hidden = false;
  if (logoutBtn) logoutBtn.hidden = false;
  if (loginError) loginError.textContent = "";
  if (window.renderReports) window.renderReports();
}

async function checkSession() {
  try {
    const res = await fetch("/api/admin/me", { credentials: "same-origin" });
    if (!res.ok) throw new Error("no session");
    showReports();
  } catch {
    showLogin("");
  }
}

if (loginForm) {
  loginForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const password = (passwordInput?.value || "").trim();
    if (!password) {
      if (loginError) loginError.textContent = "Inserisci la password.";
      return;
    }
    if (loginBtn) loginBtn.disabled = true;
    if (loginError) loginError.textContent = "";
    try {
      const res = await fetch("/api/admin/login", {
        method: "POST",
        credentials: "same-origin",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ password }),
      });
      if (!res.ok) {
        showLogin(res.status === 401 ? "Password errata. Riprova." : `Accesso non riuscito (${res.status}).`);
        return;
      }
      showReports();
    } catch {
      showLogin("Impossibile contattare il server. Riprova.");
    }
  });
}

if (logoutBtn) {
  logoutBtn.addEventListener("click", async () => {
    logoutBtn.disabled = true;
    try {
      await fetch("/api/admin/logout", { method: "POST", credentials: "same-origin" });
    } catch {
      /* esci comunque */
    } finally {
      window.location.reload();
    }
  });
}

/* Usato da reports.js quando la sessione scade durante l'uso. */
window.cdShowLogin = showLogin;

checkSession();
