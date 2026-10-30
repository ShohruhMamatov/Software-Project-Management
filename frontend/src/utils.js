// Shared formatting and validation helpers.

export const formatTime = (iso) =>
  iso ? new Date(iso).toLocaleString("en-GB", { timeZone: "Asia/Tashkent" }) : "—";

export const percent = (score) => `${Math.round(score * 100)}%`;

export function timeAgo(iso) {
  if (!iso) return "Never";
  const minutes = Math.floor((Date.now() - new Date(iso)) / 60000);
  if (minutes < 1) return "Just now";
  if (minutes < 60) return `${minutes} min ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours} h ago`;
  return `${Math.floor(hours / 24)} d ago`;
}

export function credentialsError(email, password) {
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim())) return "Enter a valid email address.";
  if (password.length < 8 || password.length > 72) return "Password must be 8–72 characters.";
  return "";
}

// stream: "02" = sub-stream (used for detection), "01" = main stream. Same format as backend/app/hikvision.py.
export const rtspPreview = ({ rtsp_username, ip, port, channel }, stream) =>
  `rtsp://${encodeURIComponent(rtsp_username)}:****@${ip}:${port}/Streaming/Channels/${channel}${stream}`;
