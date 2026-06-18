import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import fs from "node:fs";
import path from "node:path";

const certDir = path.resolve(__dirname, "..", ".certs");
const https =
  process.env.HTTPS === "true"
    ? {
        key: fs.readFileSync(path.join(certDir, "localhost-key.pem")),
        cert: fs.readFileSync(path.join(certDir, "localhost-cert.pem")),
      }
    : undefined;

export default defineConfig({
  plugins: [react()],
  server: {
    https,
  },
  preview: {
    https,
  },
});
