import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Isometric to MTO Generator",
  description: "Upload a piping isometric drawing to generate a Material Take-Off",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
