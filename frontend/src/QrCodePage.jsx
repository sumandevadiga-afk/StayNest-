import { useState } from "react";
import { Link } from "react-router-dom";

import { getBookingQr } from "./api";

function QrCodePage() {
  const [bookingId, setBookingId] = useState("");
  const [qrState, setQrState] = useState({ status: "idle", data: null, message: "" });

  async function handleLoadQr(event) {
    event.preventDefault();
    setQrState({ status: "loading", data: null, message: "Generating your secure QR code..." });
    try {
      const data = await getBookingQr(bookingId);
      setQrState({ status: "success", data, message: "Show this code to reception." });
    } catch (error) {
      setQrState({ status: "error", data: null, message: error.message || "We could not load that booking QR code." });
    }
  }

  return (
    <div className="min-h-screen bg-slate-950 px-6 py-12 text-slate-100">
      <div className="mx-auto max-w-xl">
        <Link className="text-sm font-bold text-cyan-200" to="/">← StayNest home</Link>
        <div className="mt-12 rounded-[2rem] border border-white/10 bg-white/[0.06] p-8 text-center">
          <p className="text-xs font-bold uppercase tracking-[0.2em] text-cyan-200">Customer reception pass</p>
          <h1 className="mt-3 text-4xl font-black text-white">Your booking QR code</h1>
          <p className="mt-4 text-slate-400">Enter your booking ID to generate a short-lived, one-time-use QR code.</p>
          <form className="mt-8 flex gap-3" onSubmit={handleLoadQr}>
            <input className="min-w-0 flex-1 rounded-xl border border-white/10 bg-slate-900/80 px-4 py-3 text-white outline-none placeholder:text-slate-500 focus:border-cyan-300" type="number" min="1" required placeholder="Booking ID" value={bookingId} onChange={(event) => setBookingId(event.target.value)} />
            <button className="rounded-xl bg-cyan-300 px-5 py-3 font-bold text-slate-950 disabled:opacity-60" type="submit" disabled={qrState.status === "loading"}>{qrState.status === "loading" ? "Loading..." : "Show QR"}</button>
          </form>
          {qrState.message && <p className={`mt-5 text-sm ${qrState.status === "error" ? "text-amber-200" : "text-slate-300"}`} role="status">{qrState.message}</p>}
          {qrState.data && <div className="mt-6 rounded-2xl bg-white p-5"><img className="mx-auto size-64 max-w-full" src={qrState.data.qr_code} alt={`Secure QR code for booking ${qrState.data.booking_id}`} /><p className="mt-3 text-xs text-slate-500">Expires {new Date(qrState.data.expires_at).toLocaleString()}</p></div>}
        </div>
      </div>
    </div>
  );
}

export default QrCodePage;
