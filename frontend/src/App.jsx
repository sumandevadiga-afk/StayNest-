import { useEffect, useState } from "react";

import {
  getCurrentUser,
  getHealthStatus,
  getStoredAccessToken,
  loginUser,
  logoutUser,
  registerUser,
} from "./api";

const emptyForm = { email: "", password: "", first_name: "", last_name: "" };

function App() {
  const [healthState, setHealthState] = useState({ status: "idle", message: "Not checked yet" });
  const [authMode, setAuthMode] = useState("login");
  const [authState, setAuthState] = useState({ status: "idle", message: "" });
  const [form, setForm] = useState(emptyForm);
  const [user, setUser] = useState(null);

  async function checkApiHealth() {
    setHealthState({ status: "loading", message: "Checking StayNest API..." });

    try {
      const health = await getHealthStatus();
      setHealthState({ status: "success", message: `${health.service} is healthy` });
    } catch (error) {
      setHealthState({ status: "error", message: error.message || "StayNest API is unavailable right now" });
    }
  }

  useEffect(() => {
    checkApiHealth();

    if (getStoredAccessToken()) {
      getCurrentUser().then(setUser).catch(logoutUser);
    }
  }, []);

  function handleInputChange(event) {
    setForm((current) => ({ ...current, [event.target.name]: event.target.value }));
  }

  async function handleAuthSubmit(event) {
    event.preventDefault();
    setAuthState({ status: "loading", message: "" });

    try {
      const response = authMode === "login"
        ? await loginUser({ email: form.email, password: form.password })
        : await registerUser(form);
      setUser(response.user);
      setForm(emptyForm);
      setAuthState({ status: "success", message: authMode === "login" ? "Welcome back." : "Account created successfully." });
    } catch (error) {
      setAuthState({ status: "error", message: error.message || "Authentication failed. Please try again." });
    }
  }

  function handleLogout() {
    logoutUser();
    setUser(null);
    setAuthState({ status: "idle", message: "You have been logged out." });
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <header className="border-b border-white/10 bg-slate-950/80 backdrop-blur">
        <nav className="mx-auto flex max-w-7xl items-center justify-between px-6 py-5 lg:px-8" aria-label="Main navigation">
          <a href="/" className="flex items-center gap-3" aria-label="StayNest home">
            <span className="grid size-10 place-items-center rounded-2xl bg-cyan-300 font-black text-slate-950">S</span>
            <span className="text-lg font-bold tracking-tight">StayNest</span>
          </a>
          <div className="hidden items-center gap-8 text-sm font-medium text-slate-300 md:flex">
            <a className="text-white" href="#overview">Overview</a>
            <a className="transition hover:text-white" href="#reservations">Reservations</a>
            <a className="transition hover:text-white" href="#guests">Guests</a>
            <a className="transition hover:text-white" href="#housekeeping">Housekeeping</a>
          </div>
          {user ? (
            <button className="rounded-full border border-white/15 px-4 py-2 text-sm font-semibold text-slate-200 transition hover:border-cyan-300 hover:text-cyan-200" type="button" onClick={handleLogout}>
              Log out
            </button>
          ) : (
            <a className="rounded-full border border-white/15 px-4 py-2 text-sm font-semibold text-slate-200 transition hover:border-cyan-300 hover:text-cyan-200" href="#auth">
              Sign in
            </a>
          )}
        </nav>
      </header>

      <main id="overview" className="mx-auto max-w-7xl px-6 py-16 lg:px-8 lg:py-24">
        <section className="grid items-center gap-14 lg:grid-cols-[1.1fr_0.9fr]">
          <div>
            <p className="mb-5 inline-flex rounded-full border border-cyan-300/25 bg-cyan-300/10 px-4 py-2 text-xs font-bold uppercase tracking-[0.2em] text-cyan-200">
              Local-first hotel operations
            </p>
            <h1 className="max-w-3xl text-5xl font-black tracking-[-0.06em] text-white sm:text-6xl lg:text-8xl">
              Welcome to <span className="text-cyan-300">StayNest</span>
            </h1>
            <p className="mt-6 max-w-2xl text-lg leading-8 text-slate-300 sm:text-xl">Hotel Management System</p>
            <p className="mt-4 max-w-xl text-base leading-7 text-slate-400">
              A focused workspace for reservations, guests, rooms, and the people who make every stay feel effortless.
            </p>
            <div className="mt-9 flex flex-col gap-3 sm:flex-row">
              <a className="rounded-full bg-cyan-300 px-6 py-3.5 text-center font-bold text-slate-950 shadow-lg shadow-cyan-300/10 transition hover:bg-cyan-200" href="#auth">
                Get started
              </a>
              <button className="rounded-full border border-white/15 px-6 py-3.5 font-bold text-white transition hover:border-white/35 hover:bg-white/5" type="button" onClick={checkApiHealth}>
                Check API health
              </button>
            </div>
          </div>

          <aside className="relative overflow-hidden rounded-[2rem] border border-white/10 bg-white/[0.06] p-6 shadow-2xl shadow-cyan-950/30 sm:p-8" aria-label="StayNest status">
            <div className="absolute -right-16 -top-16 size-48 rounded-full bg-cyan-300/20 blur-3xl" />
            <div className="relative">
              <div className="flex items-center justify-between">
                <span className="text-sm font-semibold text-slate-300">Today at StayNest</span>
                <span className="rounded-full bg-emerald-300/15 px-3 py-1 text-xs font-bold text-emerald-200">Ready</span>
              </div>
              <div className="mt-10 grid grid-cols-2 gap-3">
                <div className="rounded-2xl bg-slate-900/70 p-4"><span className="text-xs text-slate-400">Arrivals</span><strong className="mt-2 block text-3xl text-white">—</strong></div>
                <div className="rounded-2xl bg-slate-900/70 p-4"><span className="text-xs text-slate-400">Occupancy</span><strong className="mt-2 block text-3xl text-white">—</strong></div>
              </div>
              <div className="mt-4 rounded-2xl border border-white/10 bg-slate-900/50 p-4" aria-live="polite">
                <span className="text-xs font-bold uppercase tracking-wider text-slate-400">API health check</span>
                <p className={`mt-2 text-sm ${healthState.status === "error" ? "text-amber-200" : "text-slate-200"}`}>{healthState.message}</p>
              </div>
            </div>
          </aside>
        </section>

        <section id="auth" className="mx-auto mt-20 max-w-xl scroll-mt-8 rounded-[2rem] border border-white/10 bg-white/[0.06] p-6 sm:p-8" aria-labelledby="auth-title">
          <div className="flex items-center justify-between gap-4">
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.2em] text-cyan-200">Secure access</p>
              <h2 id="auth-title" className="mt-2 text-2xl font-bold text-white">{user ? `Welcome, ${user.first_name || user.email}` : authMode === "login" ? "Sign in to StayNest" : "Create your account"}</h2>
            </div>
            {!user && <button className="text-sm font-semibold text-cyan-200 hover:text-cyan-100" type="button" onClick={() => { setAuthMode(authMode === "login" ? "register" : "login"); setAuthState({ status: "idle", message: "" }); }}>{authMode === "login" ? "Register" : "Sign in"}</button>}
          </div>

          {user ? (
            <p className="mt-5 text-sm text-slate-300">Signed in as {user.email} · Role: {user.role}</p>
          ) : (
            <form className="mt-6 space-y-4" onSubmit={handleAuthSubmit}>
              {authMode === "register" && <div className="grid gap-4 sm:grid-cols-2"><input className="rounded-xl border border-white/10 bg-slate-900/80 px-4 py-3 text-white outline-none placeholder:text-slate-500 focus:border-cyan-300" name="first_name" placeholder="First name" value={form.first_name} onChange={handleInputChange} /><input className="rounded-xl border border-white/10 bg-slate-900/80 px-4 py-3 text-white outline-none placeholder:text-slate-500 focus:border-cyan-300" name="last_name" placeholder="Last name" value={form.last_name} onChange={handleInputChange} /></div>}
              <input className="w-full rounded-xl border border-white/10 bg-slate-900/80 px-4 py-3 text-white outline-none placeholder:text-slate-500 focus:border-cyan-300" name="email" type="email" placeholder="Email address" required value={form.email} onChange={handleInputChange} />
              <input className="w-full rounded-xl border border-white/10 bg-slate-900/80 px-4 py-3 text-white outline-none placeholder:text-slate-500 focus:border-cyan-300" name="password" type="password" placeholder="Password" minLength="8" required value={form.password} onChange={handleInputChange} />
              <button className="w-full rounded-xl bg-cyan-300 px-5 py-3.5 font-bold text-slate-950 transition hover:bg-cyan-200 disabled:cursor-wait disabled:opacity-60" type="submit" disabled={authState.status === "loading"}>{authState.status === "loading" ? "Working..." : authMode === "login" ? "Sign in" : "Create account"}</button>
              {authState.message && <p className={`text-sm ${authState.status === "error" ? "text-amber-200" : "text-emerald-200"}`} role="alert">{authState.message}</p>}
            </form>
          )}
        </section>
      </main>
    </div>
  );
}

export default App;
