import type { Metadata } from "next";
import "./globals.css";

const title = "SF3D Web Tool";
const description = "Web-based SF3D demo and asset processing tool scaffold.";

export const metadata: Metadata = {
  title,
  description,
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
