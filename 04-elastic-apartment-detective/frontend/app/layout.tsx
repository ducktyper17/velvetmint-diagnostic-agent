import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Apartment Detective",
  description:
    "Paste a listing. Get the truth before you sign. An evidence-backed renter due-diligence agent powered by Gemini + Elastic.",
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
