import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import fs from "node:fs";
import path from "node:path";

const certDir = path.resolve(__dirname, "..", ".certs");
const backendPort = process.env.BACKEND_PORT || "8010";
const backendTarget = `${process.env.HTTPS === "true" ? "https" : "http"}://127.0.0.1:${backendPort}`;
const https =
  process.env.HTTPS === "true"
    ? {
        key: fs.readFileSync(path.join(certDir, "localhost-key.pem")),
        cert: fs.readFileSync(path.join(certDir, "localhost-cert.pem")),
      }
    : undefined;
const proxy = {
  "/api": {
    target: backendTarget,
    changeOrigin: true,
    secure: false,
  },
  "/help": {
    target: backendTarget,
    changeOrigin: true,
    secure: false,
  },
  "/health": {
    target: backendTarget,
    changeOrigin: true,
    secure: false,
  },
  "/setup": {
    target: backendTarget,
    changeOrigin: true,
    secure: false,
  },
};

export default defineConfig({
  plugins: [react()],
  server: {
    https,
    proxy,
  },
  preview: {
    https,
    proxy,
  },
});
