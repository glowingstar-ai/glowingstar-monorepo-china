import localFont from "next/font/local";

const systemFont = localFont({
  src: [
    {
      path: "../public/fonts/inter-var.woff2",
      style: "normal",
    },
  ],
  display: "swap",
  fallback: [
    "-apple-system",
    "BlinkMacSystemFont",
    "Segoe UI",
    "PingFang SC",
    "Microsoft YaHei",
    "sans-serif",
  ],
  variable: "--font-inter",
});

export const inter = systemFont;

export const manrope = localFont({
  src: [{ path: "../public/fonts/inter-var.woff2", style: "normal" }],
  display: "swap",
  fallback: ["sans-serif"],
  variable: "--font-manrope",
});

export const plexSans = localFont({
  src: [{ path: "../public/fonts/inter-var.woff2", style: "normal" }],
  display: "swap",
  fallback: ["sans-serif"],
  variable: "--font-plex",
});

export const dmSans = localFont({
  src: [{ path: "../public/fonts/inter-var.woff2", style: "normal" }],
  display: "swap",
  fallback: ["sans-serif"],
  variable: "--font-dm-sans",
});

export const plusJakartaSans = localFont({
  src: [{ path: "../public/fonts/inter-var.woff2", style: "normal" }],
  display: "swap",
  fallback: ["sans-serif"],
  variable: "--font-plus-jakarta",
});

export const outfit = localFont({
  src: [{ path: "../public/fonts/inter-var.woff2", style: "normal" }],
  display: "swap",
  fallback: ["sans-serif"],
  variable: "--font-outfit",
});

export const playfairDisplay = localFont({
  src: [{ path: "../public/fonts/inter-var.woff2", style: "normal" }],
  display: "swap",
  fallback: ["serif"],
  variable: "--font-playfair",
});
