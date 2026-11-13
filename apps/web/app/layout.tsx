import type { Metadata } from "next";
import type { ReactNode } from "react";
import { Navigation } from "./navigation";
import "./globals.css";

export const metadata: Metadata = {
  title: "Industrial B2B AI Copilot",
  description: "Source-backed product knowledge for industrial sales and sourcing.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return <html lang="en"><body><Navigation />{children}</body></html>;
}
