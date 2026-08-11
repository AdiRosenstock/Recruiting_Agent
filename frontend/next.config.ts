import path from "node:path";
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Pins Turbopack's workspace root to this project explicitly -- without it, Turbopack walks
  // up looking for a lockfile and can land on an unrelated one elsewhere in the user's home
  // directory (nothing to do with this project), which produces a spurious root-detection
  // warning.
  turbopack: {
    root: path.resolve(__dirname),
  },
  // Minimal, self-contained `.next/standalone` build (only the files actually needed at
  // runtime, own `node_modules` copied in) -- what Dockerfile's runtime stage runs. Doesn't
  // affect `next dev`/`next start` outside Docker.
  output: "standalone",
};

export default nextConfig;
