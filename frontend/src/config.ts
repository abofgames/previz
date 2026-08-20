// Where the frontend looks for the backend.
//
// Three cases, in order:
//  - VITE_API_URL set at build time  → use it (split frontend/backend deploys)
//  - dev server                      → the local uvicorn on :8000
//  - production build                → same origin, because the backend serves
//                                      this bundle itself
const explicit = import.meta.env.VITE_API_URL as string | undefined;

export const API = explicit ?? (import.meta.env.DEV ? "http://localhost:8000" : "");

export const WS =
  API === ""
    ? `${window.location.protocol === "https:" ? "wss" : "ws"}://${window.location.host}`
    : API.replace(/^http/, "ws");

export const PROJECT = "demo";
