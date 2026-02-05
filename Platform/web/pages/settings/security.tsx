import { useState } from "react";

export default function SecuritySettings() {
  const [qr, setQr] = useState("");
  const [manual, setManual] = useState("");
  const [code, setCode] = useState("");

  const start2FA = async () => {
    const res = await fetch("/api/2fa/setup", { method: "POST" });
    const data = await res.json();
    setQr(data.qr_uri);
    setManual(data.manual_key);
  };

  const verify2FA = async () => {
    await fetch("/api/2fa/verify", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ code })
    });
  };

  return (
    <div>
      <h2>Two-Factor Authentication</h2>
      <button onClick={start2FA}>Enable 2FA</button>

      {qr && (
        <>
          <img src={`https://api.qrserver.com/v1/create-qr-code/?data=${qr}`} />
          <p>Manual key: {manual}</p>
          <input placeholder="Enter code" onChange={e => setCode(e.target.value)} />
          <button onClick={verify2FA}>Verify</button>
        </>
      )}
    </div>
  );
}
