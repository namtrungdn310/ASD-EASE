import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import { fileURLToPath } from "node:url";
import { resolve } from "node:path";
import { localSessionPlugin } from "./dev/local-session.mjs";

export default defineConfig(({ mode }) => {
  const root = fileURLToPath(new URL("../", import.meta.url));
  const environment = loadEnv(mode, root, "MQTT_");
  const directory = process.env.ASD_DEV_CREDENTIALS_DIR
    ?? resolve(root, environment.MQTT_LOCAL_DIR ?? "infra/mosquitto/local/dev");
  return {
    plugins: [react(), tailwindcss(), localSessionPlugin({ credentialsFile: resolve(directory, "backend.env") })],
    server: {
      host: "localhost", port: 5173, strictPort: true, allowedHosts: ["localhost"],
      fs: {
        allow: [fileURLToPath(new URL("./", import.meta.url))],
        deny: [".env", ".env.*", "**/*.{crt,pem}", "**/.git/**", "**/network_config.h", "**/infra/mosquitto/local/**"],
      },
    },
  };
});
