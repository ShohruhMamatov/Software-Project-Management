import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  // The backend's CORS only allows :5173, so fail loudly instead of moving to another port.
  server: { port: 5173, strictPort: true },
});
