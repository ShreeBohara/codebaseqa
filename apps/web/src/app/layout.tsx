import type { Metadata } from "next";
import { Analytics } from "@vercel/analytics/next";
import "./globals.css";

export const metadata: Metadata = {
  title: "CodebaseQA - AI-Powered Codebase Understanding",
  description: "Understand any codebase in minutes with AI-powered Q&A",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark" suppressHydrationWarning>
      <body className="antialiased bg-zinc-950 text-white">
        {children}
        <Analytics />
      </body>
    </html>
  );
}
