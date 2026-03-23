import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        ink: "#111827",
        mist: "#e5edf5",
        ember: "#ff7a18",
        tide: "#0f4c5c",
        shell: "#fffaf2",
      },
      boxShadow: {
        panel: "0 18px 60px rgba(15, 76, 92, 0.16)",
      },
      backgroundImage: {
        grid: "linear-gradient(rgba(15, 76, 92, 0.08) 1px, transparent 1px), linear-gradient(90deg, rgba(15, 76, 92, 0.08) 1px, transparent 1px)",
      },
    },
  },
  plugins: [],
};

export default config;
