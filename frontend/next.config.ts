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
};

export default nextConfig;
