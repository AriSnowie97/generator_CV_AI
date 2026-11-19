import type { Metadata } from "next";
import "./globals.css";
import { Navbar } from "@/components/Navbar";

export const metadata: Metadata = {
  title: "ResumeCraft — Сервіс-генератор резюме з AI-підказками",
  description:
    "Один профіль — якісне резюме у PDF та DOCX за 15 хвилин. Прості ATS-шаблони та чесні AI-підказки без вигадування фактів.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="uk">
      <body className="min-h-screen antialiased">
        <Navbar />
        <main>{children}</main>
      </body>
    </html>
  );
}
