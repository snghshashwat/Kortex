import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Kortex - Context Graph Dashboard",
  description: "Visualize your second brain's semantic knowledge graph",
  icons: {
    icon: "/favicon.svg",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
