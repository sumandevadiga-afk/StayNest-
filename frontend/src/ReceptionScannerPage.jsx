import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { Html5QrcodeScanner } from "html5-qrcode";

import { consumeQrToken } from "./api";

function ReceptionScannerPage() {
  const [action, setAction] = useState("check_in");
  const [scanState, setScanState] = useState({ status: "idle", message: "Point the camera at a StayNest QR code." });
  const busyRef = useRef(false);

  useEffect(() => {
    const scanner = new Html5QrcodeScanner("staynest-qr-reader", { fps: 10, qrbox: { width: 250, height: 250 } }, false);
    scanner.render(async (decodedText) => {
      if (busyRef.current) return;
      busyRef.current = true;
      setScanState({ status: "loading", message: `Processing ${action.replace("_", " ")}...` });
      try {
        const result = await consumeQrToken(decodedText, action);
        setScanState({ status: "success", message: `Booking ${result.booking.id} ${action.replace("_", " ")} completed.` });
      } catch (error) {
        setScanState({ status: "error", message: error.message || "That QR code could not be used." });
      } finally {
        window.setTimeout(() => { busyRef.current = false; }, 1500);
      }
    }, () => {});

    return () => {
      scanner.clear().catch(() => {});
    };
  }, [action]);

  return (
    <div className="min-h-screen bg-slate-950 px-6 py-12 text-slate-100">
      <div className="mx-auto max-w-xl">
        <Link className="text-sm font-bold text-cyan-200" to="/">← StayNest home</Link>
        <div className="mt-12 rounded-[2rem] border border-white/10 bg-white/[0.06] p-8">
          <p className="text-xs font-bold uppercase tracking-[0.2em] text-cyan-200">Reception operations</p>
          <h1 className="mt-3 text-4xl font-black text-white">QR scanner</h1>
          <label className="mt-6 block text-sm font-semibold text-slate-300" htmlFor="scan-action">Action</label>
          <select id="scan-action" className="mt-2 w-full rounded-xl border border-white/10 bg-slate-900 px-4 py-3 text-white" value={action} onChange={(event) => setAction(event.target.value)}><option value="check_in">Check in</option><option value="check_out">Check out</option></select>
          <div className="mt-6 overflow-hidden rounded-2xl bg-white p-3"><div id="staynest-qr-reader" /></div>
          <p className={`mt-5 text-sm ${scanState.status === "error" ? "text-amber-200" : scanState.status === "success" ? "text-emerald-200" : "text-slate-300"}`} role="status">{scanState.message}</p>
        </div>
      </div>
    </div>
  );
}

export default ReceptionScannerPage;
