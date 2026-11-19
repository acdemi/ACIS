import vue from "@vitejs/plugin-vue";
import { defineConfig } from "vitest/config";
import { loadEnv } from "vite";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, ".", "ACIS_");
  const apiTarget = env.ACIS_API_PROXY_TARGET || "http://127.0.0.1:8000";

  return {
    plugins: [vue()],
    server: {
      host: "127.0.0.1",
      fs: { allow: [".."] },
      proxy: {
        "/health": apiTarget,
        "/diagnose": apiTarget,
        "/decisions": apiTarget,
      },
    },
    test: {
      environment: "jsdom",
      restoreMocks: true,
    },
  };
});
