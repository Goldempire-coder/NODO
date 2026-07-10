import type { Metadata } from "next";
import "@telegram-apps/telegram-ui/dist/styles.css";
import "./globals.css";

export const metadata: Metadata = {
  title: "NODO",
  description: "NODO Telegram Mini App auth foundation",
  icons: {
    icon: "/icon.svg",
    shortcut: "/icon.svg",
    apple: "/icon.svg"
  }
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="es">
      <body>{children}</body>
    </html>
  );
}
