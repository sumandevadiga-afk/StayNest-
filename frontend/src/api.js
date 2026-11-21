const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000/api";

export async function getHealthStatus() {
  const response = await fetch(`${apiBaseUrl}/health/`);

  if (!response.ok) {
    throw new Error(`API returned ${response.status}`);
  }

  return response.json();
}
