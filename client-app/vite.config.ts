import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// In development the browser talks only to Vite (port 5173) and Vite forwards
// /api to Django, so the app and the API share an origin and no CORS is needed.
// In Docker, nginx plays the same role.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": "http://127.0.0.1:8000",
    },
  },
});
