import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Agent Reliability Guard",
  description:
    "Catch and explain Gemini-agent regressions before they burn money and trust. Powered by Gemini + Dynatrace MCP.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-ink-950 text-zinc-200 font-sans antialiased">
        {children}
      </body>
    </html>
  );
}
