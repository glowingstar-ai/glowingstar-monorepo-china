import "./globals.css";
import "katex/dist/katex.min.css";

import type { Metadata } from "next";
import type { ReactNode } from "react";
import { ThemeProvider } from "@/components/theme-provider";
import {
  dmSans,
  inter,
  manrope,
  outfit,
  playfairDisplay,
  plexSans,
  plusJakartaSans,
} from "@/lib/fonts";

export const metadata: Metadata = {
  title: {
    default: "GlowingStar Experience Studio",
    template: "%s | GlowingStar Studio",
  },
  description:
    "Command center for emotionally intelligent customer experiences—monitor sessions, review insights, and launch guided playbooks.",
  icons: {
    icon: "/logo.png",
    shortcut: "/logo.png",
  },
};

export default function RootLayout({
  children,
}: Readonly<{ children: ReactNode }>) {
  return (
    <html
      lang="en"
      className={`antialiased ${inter.variable} ${manrope.variable} ${plexSans.variable} ${dmSans.variable} ${plusJakartaSans.variable} ${outfit.variable} ${playfairDisplay.variable}`}
      suppressHydrationWarning
    >
      <body>
        <ThemeProvider attribute="class" defaultTheme="system" enableSystem>
          {children}
          <footer className="w-full py-3 text-center text-xs text-muted-foreground/50">
            v0.0.1
          </footer>
        </ThemeProvider>
      </body>
    </html>
  );
}
