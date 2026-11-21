import { useState } from "react";

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000/api";

function App() {
  const [healthState, setHealthState] = useState("Not checked");

  async function checkApiHealth() {
    setHealthState("Checking...");

    try {
      const response = await fetch(`${apiBaseUrl}/health/`);
      setHealthState(response.ok ? "API is healthy" : `API returned ${response.status}`);
    } catch {
      setHealthState("API placeholder: backend health endpoint is not available yet");
    }
  }

  return (
    <main className="page-shell">
      <section className="hero-card" aria-labelledby="page-title">
        <span className="eyebrow">Welcome to</span>
        <h1 id="page-title">StayNest</h1>
        <p className="subtitle">Hotel Management System</p>
        <p className="description">
          A calm, local-first workspace for managing hotel operations, guests, and stays.
        </p>

        <div className="health-panel" aria-live="polite">
          <div>
            <span className="panel-label">API health check</span>
            <strong>{healthState}</strong>
          </div>
          <button type="button" onClick={checkApiHealth}>
            Check API
          </button>
        </div>
      </section>
    </main>
  );
}

export default App;
