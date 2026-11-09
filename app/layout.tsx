import type { Metadata } from "next";
import './globals.css';
import './features.css';
import './theme.css';
import {ThemeProvider} from '@/components/theme-provider';
import {projectName} from '@/lib/project.mjs';

export const metadata: Metadata = { title: `${projectName} — Find your people`, description: "A thoughtful space for people, ideas and conversations." };

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body><ThemeProvider/>{children}</body></html>;
}
