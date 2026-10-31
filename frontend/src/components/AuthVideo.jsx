import { useState } from "react";
import useAuthBlob from "./useAuthBlob";

// fallback: what to show if the clip is missing or the browser can't play it.
export default function AuthVideo({ path, fallback, ...props }) {
  const { url, failed } = useAuthBlob(path);
  const [broken, setBroken] = useState(false);

  if (failed || broken) return fallback;
  if (!url) return <div className="img-placeholder">Loading…</div>;
  return <video src={url} controls autoPlay muted loop playsInline onError={() => setBroken(true)} {...props} />;
}
