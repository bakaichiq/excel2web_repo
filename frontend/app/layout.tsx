import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Excel2Web Dashboard",
  description: "Production-ready replacement for heavy Excel construction accounting"
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ru">
      <body className="min-h-screen">{children}</body>
    </html>
  );
}
