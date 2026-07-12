import type { Metadata, Viewport } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Kisan Sahayak - AI Agricultural Advisor",
  description: "Multilingual AI Agricultural Advisor for Farmers",
  manifest: "/manifest.json",
  appleWebApp: {
    capable: true,
    statusBarStyle: "default",
    title: "Kisan Sahayak",
  },
};

export const viewport: Viewport = {
  themeColor: "#1b5e20",
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
  userScalable: false,
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="h-full bg-background text-foreground transition-colors duration-200">
        {children}
      </body>
    </html>
  );
}
