import { useEffect, useState } from "react";
import { apiBlob } from "../api";

// Clip and snapshot URLs need the Authorization header, so <img src> can't load them directly.
// Fetch the file and hand back a blob URL instead.
export default function useAuthBlob(path) {
  const [result, setResult] = useState({ path: null, url: null, failed: false });

  useEffect(() => {
    let cancelled = false;
    let objectUrl;
    apiBlob(path)
      .then((blob) => {
        if (cancelled) return;
        objectUrl = URL.createObjectURL(blob);
        setResult({ path, url: objectUrl, failed: false });
      })
      .catch(() => {
        if (!cancelled) setResult({ path, url: null, failed: true });
      });
    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl); // free memory
    };
  }, [path]);

  return result.path === path ? result : { url: null, failed: false };
}
