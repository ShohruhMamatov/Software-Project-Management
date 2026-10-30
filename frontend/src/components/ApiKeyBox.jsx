import { useState } from "react";

// The API key is only ever shown once, so make it easy to copy.
export default function ApiKeyBox({ apiKey }) {
  const [label, setLabel] = useState("Copy");

  async function copy() {
    try {
      await navigator.clipboard.writeText(apiKey);
      setLabel("Copied");
      setTimeout(() => setLabel("Copy"), 2000);
    } catch {
      setLabel("Select and copy manually");
    }
  }

  return (
    <div className="key-box">
      <code>{apiKey}</code>
      <button type="button" className="btn" onClick={copy}>
        {label}
      </button>
    </div>
  );
}
