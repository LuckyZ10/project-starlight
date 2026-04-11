import type { Metadata, Viewport } from "next";
import localFont from "next/font/local";
import "./globals.css";

const geistSans = localFont({
  src: "./fonts/GeistVF.woff",
  variable: "--font-geist-sans",
  weight: "100 900",
});
const geistMono = localFont({
  src: "./fonts/GeistMonoVF.woff",
  variable: "--font-geist-mono",
  weight: "100 900",
});

import ThemeToggle from "@/components/ThemeToggle";
import ToastContainer from "@/components/Toast";
import ErrorBoundary from "@/components/ErrorBoundary";

export const metadata: Metadata = {
  title: "Starlight",
  description: "Interactive AI-powered learning platform",
  manifest: "/manifest.json",
  appleWebApp: {
    capable: true,
    statusBarStyle: "default",
    title: "Starlight",
  },
};

export const viewport: Viewport = {
  themeColor: "#10b981",
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
  viewportFit: "cover",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        {/* KaTeX loaded async */}
        <link rel="preload" href="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.css" as="style" onLoad="this.onload=null;this.rel='stylesheet'" />
        <noscript><link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.css" /></noscript>
      </head>
      <body className={`${geistSans.variable} ${geistMono.variable} antialiased`}>
        <script dangerouslySetInnerHTML={{ __html: `(function(){try{var t=localStorage.getItem('theme');if(t==='dark'||(!t&&window.matchMedia('(prefers-color-scheme:dark)').matches)){document.documentElement.classList.add('dark')}}catch(e){}})()` }} />
        <ThemeToggle />
        <ToastContainer />
        <ErrorBoundary>{children}</ErrorBoundary>
      </body>
    </html>
  );
}
