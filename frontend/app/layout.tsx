import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Recruiting Agent",
  description: "Personal startup recruiting CRM + research agent",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
