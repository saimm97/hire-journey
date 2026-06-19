"use strict";

/**
 * Frontend logic for the Career Engine auth page.
 *
 * Talks to the FastAPI backend over HTTP only — there is no shared code or build
 * step between the two. The bearer token returned by /login is kept in
 * localStorage and replayed on authenticated requests.
 */

// Base URL of the backend API. Override here if the backend runs elsewhere.
const API_BASE = "http://localhost:8000/api/v1";
const TOKEN_KEY = "ce_token";

// --- DOM references -------------------------------------------------------
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

/** Return the stored bearer token, or null if the user is not logged in. */
function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

/** Persist the bearer token so it survives page reloads. */
function setToken(token) {
  localStorage.setItem(TOKEN_KEY, token);
}

/** Remove the stored token (used on logout or when a token is rejected). */
function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
}

// --- API calls ------------------------------------------------------------

/**
 * Parse an error body from the API into a human-readable string.
 *
 * FastAPI returns `{detail: "..."}` for raised errors and `{detail: [...]}` for
 * request-validation failures; this normalises both into one message.
 */
function extractError(body, fallback) {
  const detail = body && body.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && detail.length) return detail[0].msg || fallback;
  return fallback;
}

/**
 * Register a new account.
 *
 * @returns {Promise<object>} the created user. Throws an Error with a
 *   user-facing message if registration fails (e.g. username taken).
 */
async function register({ username, email, password }) {
  const res = await fetch(`${API_BASE}/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, email, password }),
  });
  const body = await res.json().catch(() => null);
  if (!res.ok) throw new Error(extractError(body, "Registration failed."));
  return body;
}

/**
 * Log in and store the returned bearer token.
 *
 * Sends the OAuth2 password form the backend expects (`username` carries either
 * the email or the username). Throws an Error on invalid credentials.
 */
async function login(identifier, password) {
  const res = await fetch(`${API_BASE}/auth/login`, {
    method: "POST",
    body: new URLSearchParams({ username: identifier, password }),
  });
  const body = await res.json().catch(() => null);
  if (!res.ok) throw new Error(extractError(body, "Login failed."));
  setToken(body.access_token);
}

/**
 * Fetch the authenticated user's profile using the stored token.
 *
 * @returns {Promise<object|null>} the user, or null if there is no valid token.
 */
async function fetchCurrentUser() {
  const token = getToken();
  if (!token) return null;
  const res = await fetch(`${API_BASE}/auth/me`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) {
    clearToken(); // token missing/expired — force a fresh login
    return null;
  }
  return res.json();
}

/** Fetch public auth config (whether Google sign-in is enabled, and its client id). */
async function fetchAuthConfig() {
  try {
    const res = await fetch(`${API_BASE}/auth/config`);
    return res.ok ? res.json() : null;
  } catch {
    return null; // backend unreachable — degrade to email/password only
  }
}

/**
 * Exchange a Google ID token for our own bearer token and store it.
 *
 * Posts the credential Google handed the browser to the backend, which verifies
 * it and returns a token in the same shape as a normal login.
 */
async function loginWithGoogle(credential) {
  const res = await fetch(`${API_BASE}/auth/google`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ credential }),
  });
  const body = await res.json().catch(() => null);
  if (!res.ok) throw new Error(extractError(body, "Google sign-in failed."));
  setToken(body.access_token);
}

// --- View switching -------------------------------------------------------

/** Show a status message under the forms, styled as an error or success note. */
function showMessage(text, type) {
  els.message.textContent = text;
  els.message.className = `message ${type ? `is-${type}` : ""}`;
}

/** Toggle between the "sign in" and "sign up" forms. */
function switchTab(target) {
  const signin = target === "signin";
  els.tabSignin.classList.toggle("is-active", signin);
  els.tabSignup.classList.toggle("is-active", !signin);
  els.signinForm.classList.toggle("is-hidden", !signin);
  els.signupForm.classList.toggle("is-hidden", signin);
  showMessage("", null);
}

/** Render the logged-in view for the given user and hide the auth forms. */
function showSessionView(user) {
  els.authView.classList.add("is-hidden");
  els.sessionView.classList.remove("is-hidden");
  els.sessionUsername.textContent = user.username;
  els.sessionEmail.textContent = user.email;
}

/** Render the logged-out view (auth forms) and hide the session panel. */
function showAuthView() {
  els.sessionView.classList.add("is-hidden");
  els.authView.classList.remove("is-hidden");
}

/**
 * Run an async form handler while disabling its submit button, so a slow
 * request can't be fired twice and the user gets immediate feedback.
 */
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

/**
 * Resolve once the Google Identity Services library has loaded.
 *
 * The GIS script loads asynchronously, so it may not be ready when the page
 * finishes. Polls briefly and resolves false if it never appears (e.g. the
 * script is blocked), so the page still works with email/password only.
 */
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

/**
 * GIS callback: receives Google's ID token, swaps it for our token, and logs in.
 *
 * Registered with `google.accounts.id.initialize`; `response.credential` is the
 * signed ID token. Errors surface in the shared message area.
 */
async function handleGoogleCredential(response) {
  try {
    await loginWithGoogle(response.credential);
    const user = await fetchCurrentUser();
    showSessionView(user);
  } catch (err) {
    showMessage(err.message, "error");
  }
}

/**
 * Initialise the "Continue with Google" button for the given client id.
 *
 * No-ops if Google sign-in is disabled server-side or the GIS library fails to
 * load, leaving the section hidden.
 */
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
      const user = await fetchCurrentUser();
      showSessionView(user);
    } catch (err) {
      showMessage(err.message, "error");
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
      switchTab("signin"); // clears any prior message...
      showMessage("Account created — please sign in.", "success"); // ...then show success
    } catch (err) {
      showMessage(err.message, "error");
    }
  });
});

els.logoutBtn.addEventListener("click", () => {
  clearToken();
  showAuthView();
  showMessage("", null);
});

/**
 * On load: restore an existing session if the stored token is still valid, and
 * set up "Continue with Google" if the backend has it configured.
 */
(async function init() {
  const user = await fetchCurrentUser();
  if (user) {
    showSessionView(user);
  } else {
    const config = await fetchAuthConfig();
    if (config?.google_enabled) initGoogle(config.google_client_id);
  }
})();
