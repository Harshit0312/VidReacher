import { useEffect, useState } from "react";

function App() {
  const [message, setMessage] = useState("Loading...");

  useEffect(() => {
    const api = import.meta.env.VITE_API_URL || "http://localhost:10000";
    fetch(api)
      .then((res) => res.json())
      .then((data) => setMessage(data.message))
      .catch(() => setMessage("Backend not reachable ❌"));
  }, []);

  return (
    <div style={{ fontFamily: "Inter, sans-serif", padding: "40px" }}>
      <h1>🚀 VidReacher Labs Frontend</h1>
      <p>
        <b>Backend Message:</b> {message}
      </p>
    </div>
  );
}

export default App;
