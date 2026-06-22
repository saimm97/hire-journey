"use strict";

const API_BASE = window.APP_CONFIG.apiBase;
const STRINGS = window.STRINGS;
const TOKEN_KEY = STRINGS.storageKey;
const MESSAGE = { error: "error", success: "success" };

const els = {
  authView: document.getElementById("auth-view"),
  sessionView: document.getElementById("session-view"),
  tabSignin: document.getElementById("tab-signin"),
  tabSignup: document.getElementById("tab-signup"),
  signinForm: document.getElementById("signin-form"),
  signupForm: document.getElementById("signup-form"),
  message: document.getElementById("message"),
  sessionUsername: document.getElementById("session-username"),
  sessionEmail: document.getElementById("session-email"),
  logoutBtn: document.getElementById("logout-btn"),
  googleSection: document.getElementById("google-section"),
  googleBtn: document.getElementById("google-btn"),
};

// --- Token storage --------------------------------------------------------

const getToken = () => localStorage.getItem(TOKEN_KEY);
const setToken = (token) => localStorage.setItem(TOKEN_KEY, token);
const clearToken = () => localStorage.removeItem(TOKEN_KEY);

// --- API calls ------------------------------------------------------------

// FastAPI returns {detail: "..."} for raised errors and {detail: [...]} for
// validation failures; collapse both to a single line.
function extractError(body, fallback) {
  const detail = body && body.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && detail.length) return detail[0].msg || fallback;
  return fallback;
}

async function register({ username, email, password }) {
  const res = await fetch(`${API_BASE}/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, email, password }),
  });
  const body = await res.json().catch(() => null);
  if (!res.ok) throw new Error(extractError(body, STRINGS.messages.registerFailed));
  return body;
}

async function login(identifier, password) {
  const res = await fetch(`${API_BASE}/auth/login`, {
    method: "POST",
    body: new URLSearchParams({ username: identifier, password }),
  });
  const body = await res.json().catch(() => null);
  if (!res.ok) throw new Error(extractError(body, STRINGS.messages.loginFailed));
  setToken(body.access_token);
}

async function loginWithGoogle(credential) {
  const res = await fetch(`${API_BASE}/auth/google`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ credential }),
  });
  const body = await res.json().catch(() => null);
  if (!res.ok) throw new Error(extractError(body, STRINGS.messages.googleFailed));
  setToken(body.access_token);
}

async function fetchCurrentUser() {
  const token = getToken();
  if (!token) return null;
  const res = await fetch(`${API_BASE}/auth/me`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) {
    clearToken();
    return null;
  }
  return res.json();
}

async function fetchAuthConfig() {
  try {
    const res = await fetch(`${API_BASE}/auth/config`);
    return res.ok ? res.json() : null;
  } catch {
    return null;
  }
}

// --- Views ----------------------------------------------------------------

// Fill every [data-str] element from STRINGS using its dotted key path.
function applyStrings() {
  document.title = STRINGS.brand;
  document.querySelectorAll("[data-str]").forEach((el) => {
    const value = el.dataset.str.split(".").reduce((obj, key) => obj?.[key], STRINGS);
    if (value != null) el.textContent = value;
  });
}

function showMessage(text, type) {
  els.message.textContent = text;
  els.message.className = `message ${type ? `is-${type}` : ""}`;
}

function switchTab(target) {
  const signin = target === "signin";
  els.tabSignin.classList.toggle("is-active", signin);
  els.tabSignup.classList.toggle("is-active", !signin);
  els.signinForm.classList.toggle("is-hidden", !signin);
  els.signupForm.classList.toggle("is-hidden", signin);
  showMessage("", null);
}

function showSessionView(user) {
  els.authView.classList.add("is-hidden");
  els.sessionView.classList.remove("is-hidden");
  els.sessionUsername.textContent = user.username;
  els.sessionEmail.textContent = user.email;
}

function showAuthView() {
  els.sessionView.classList.add("is-hidden");
  els.authView.classList.remove("is-hidden");
}

// Disable the submit button while a request is in flight to prevent double submits.
async function withSubmitting(form, fn) {
  const button = form.querySelector("button[type=submit]");
  button.disabled = true;
  try {
    await fn();
  } finally {
    button.disabled = false;
  }
}

// --- Google sign-in -------------------------------------------------------

// The GIS script loads asynchronously; resolve false if it never appears so the
// page still works with email/password only.
function waitForGoogle(timeoutMs = 5000) {
  return new Promise((resolve) => {
    const start = Date.now();
    (function poll() {
      if (window.google?.accounts?.id) return resolve(true);
      if (Date.now() - start > timeoutMs) return resolve(false);
      setTimeout(poll, 100);
    })();
  });
}

async function handleGoogleCredential(response) {
  try {
    await loginWithGoogle(response.credential);
    showSessionView(await fetchCurrentUser());
  } catch (err) {
    showMessage(err.message, MESSAGE.error);
  }
}

async function initGoogle(clientId) {
  if (!clientId || !(await waitForGoogle())) return;
  window.google.accounts.id.initialize({
    client_id: clientId,
    callback: handleGoogleCredential,
  });
  window.google.accounts.id.renderButton(els.googleBtn, {
    theme: "outline",
    size: "large",
    text: "continue_with",
    width: 316,
  });
  els.googleSection.classList.remove("is-hidden");
}

// --- Event wiring ---------------------------------------------------------

els.tabSignin.addEventListener("click", () => switchTab("signin"));
els.tabSignup.addEventListener("click", () => switchTab("signup"));

els.signinForm.addEventListener("submit", (e) => {
  e.preventDefault();
  const data = new FormData(els.signinForm);
  withSubmitting(els.signinForm, async () => {
    try {
      await login(data.get("identifier"), data.get("password"));
      showSessionView(await fetchCurrentUser());
    } catch (err) {
      showMessage(err.message, MESSAGE.error);
    }
  });
});

els.signupForm.addEventListener("submit", (e) => {
  e.preventDefault();
  const data = new FormData(els.signupForm);
  withSubmitting(els.signupForm, async () => {
    try {
      await register({
        username: data.get("username"),
        email: data.get("email"),
        password: data.get("password"),
      });
      els.signupForm.reset();
      switchTab("signin");
      showMessage(STRINGS.messages.signupSuccess, MESSAGE.success);
    } catch (err) {
      showMessage(err.message, MESSAGE.error);
    }
  });
});

els.logoutBtn.addEventListener("click", () => {
  clearToken();
  showAuthView();
  showMessage("", null);
});

(async function init() {
  applyStrings();
  const user = await fetchCurrentUser();
  if (user) {
    showSessionView(user);
    return;
  }
  const config = await fetchAuthConfig();
  if (config?.google_enabled) initGoogle(config.google_client_id);
})();
