import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: { 950: "#0a0a0f", 900: "#0f0f17", 800: "#16161f", 700: "#1f1f2b" },
        plum: { 500: "#a78bfa", 400: "#c4b5fd" },
        teal: { 500: "#2dd4bf", 400: "#5eead4" },
        rose: { 500: "#fb7185" },
      },
      fontFamily: {
        mono: ["ui-monospace", "SFMono-Regular", "Menlo", "monospace"],
      },
    },
  },
  plugins: [],
};
export default config;
