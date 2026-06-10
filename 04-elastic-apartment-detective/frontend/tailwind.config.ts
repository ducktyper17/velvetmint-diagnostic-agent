import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: { 950: "#06070d", 900: "#0d0f17", 800: "#15171f", 700: "#1c1f29" },
        bondi: { 500: "#22d3ee", 400: "#67e8f9" },
        warn: { 500: "#fb923c", 400: "#fdba74" },
        rose: { 500: "#fb7185", 400: "#fda4af" },
        teal: { 500: "#2dd4bf", 400: "#5eead4" },
        amber: { 500: "#f59e0b", 400: "#fbbf24", 300: "#fcd34d" },
      },
      fontFamily: {
        mono: ["ui-monospace", "SFMono-Regular", "Menlo", "monospace"],
      },
    },
  },
  plugins: [],
};
export default config;
