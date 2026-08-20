// Single place the frontend learns where the backend lives, so a deployed
// build can point at a Cloud Run URL without touching component code.
export const API = import.meta.env.VITE_API_URL ?? "http://localhost:8000";
export const WS = API.replace(/^http/, "ws");
export const PROJECT = "demo";
