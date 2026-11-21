const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000/api";
const accessTokenKey = "staynest.accessToken";
const refreshTokenKey = "staynest.refreshToken";

async function apiRequest(path, options = {}) {
  const headers = new Headers(options.headers);
  headers.set("Content-Type", "application/json");

  const accessToken = sessionStorage.getItem(accessTokenKey);
  if (accessToken) {
    headers.set("Authorization", `Bearer ${accessToken}`);
  }

  const response = await fetch(`${apiBaseUrl}${path}`, { ...options, headers });
  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(data.detail || data.message || `API returned ${response.status}`);
  }

  return data;
}

function storeTokens(data) {
  sessionStorage.setItem(accessTokenKey, data.access);
  sessionStorage.setItem(refreshTokenKey, data.refresh);
}

export function getStoredAccessToken() {
  return sessionStorage.getItem(accessTokenKey);
}

export async function getHealthStatus() {
  return apiRequest("/health/");
}

export async function registerUser(payload) {
  const data = await apiRequest("/auth/register/", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  storeTokens(data);
  return data;
}

export async function loginUser(payload) {
  const data = await apiRequest("/auth/login/", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  storeTokens(data);
  return data;
}

export function logoutUser() {
  sessionStorage.removeItem(accessTokenKey);
  sessionStorage.removeItem(refreshTokenKey);
}

export function getCurrentUser() {
  return apiRequest("/auth/me/");
}
