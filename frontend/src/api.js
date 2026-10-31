// All calls to the LUMI backend. See docs/frontend-spec.md §7-8.
const BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(status, message) {
    super(message);
    this.status = status;
  }
}

async function send(path, { headers, ...options } = {}) {
  const token = localStorage.getItem("token");
  let res;
  try {
    res = await fetch(BASE + path, {
      ...options,
      headers: { ...headers, ...(token && { Authorization: `Bearer ${token}` }) },
    });
  } catch {
    throw new ApiError(0, "Can't reach the server. Check your connection and try again.");
  }
  // Expired/invalid token -> log out. A 401 from /auth/login only means a wrong password.
  if (res.status === 401 && token && path !== "/auth/login") {
    localStorage.removeItem("token");
    window.location.href = "/login";
  }
  return res;
}

async function request(path, { method = "GET", body } = {}) {
  const res = await send(path, {
    method,
    headers: body !== undefined ? { "Content-Type": "application/json" } : undefined,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) throw new ApiError(res.status, await errorMessage(res));
  return res.status === 204 ? null : res.json();
}

async function errorMessage(res) {
  try {
    const { detail } = await res.json();
    if (typeof detail === "string") return detail; // e.g. "Wrong email or password"
    if (Array.isArray(detail)) return detail.map((d) => `${d.loc.at(-1)}: ${d.msg}`).join(", "); // 422
  } catch {
    // Not JSON: fall through to the generic message.
  }
  return `Request failed (${res.status})`;
}

export async function apiBlob(path) {
  const res = await send(path);
  if (!res.ok) throw new ApiError(res.status, "File not found");
  return res.blob();
}

export const api = {
  register: (data) => request("/auth/register", { method: "POST", body: data }),
  login: (data) => request("/auth/login", { method: "POST", body: data }),
  me: () => request("/auth/me"),

  createStore: (data) => request("/stores", { method: "POST", body: data }),
  myStore: () => request("/stores/me"),
  updateStore: (data) => request("/stores/me", { method: "PATCH", body: data }),
  rotateApiKey: () => request("/stores/me/api-key", { method: "POST" }),

  cameras: () => request("/cameras"),
  camera: (id) => request(`/cameras/${id}`),
  createCamera: (data) => request("/cameras", { method: "POST", body: data }),
  updateCamera: (id, data) => request(`/cameras/${id}`, { method: "PATCH", body: data }),
  deleteCamera: (id) => request(`/cameras/${id}`, { method: "DELETE" }),
  zones: (id) => request(`/cameras/${id}/zones`),
  saveZones: (id, zones) => request(`/cameras/${id}/zones`, { method: "PUT", body: zones }),

  events: (params = {}) =>
    request(
      "/events?" +
        new URLSearchParams(Object.entries(params).filter(([, v]) => v !== undefined && v !== null && v !== "")),
    ),
  event: (id) => request(`/events/${id}`),
  review: (id, status) => request(`/events/${id}/review`, { method: "POST", body: { status } }),
};
