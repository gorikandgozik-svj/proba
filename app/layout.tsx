import type { Metadata } from "next";
import './globals.css';

export const metadata: Metadata = { title: "NEXUS — Find your people", description: "A thoughtful space for people, ideas and conversations." };

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}
