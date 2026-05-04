import type { Metadata } from "next";

import { AuthProvider } from "@/components/AuthProvider";
import { MobileNav } from "@/components/MobileNav";
import "./globals.css";

export const metadata: Metadata = {
  title: "BIDALS",
  description: "Secure mobile-first digital auctions.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <AuthProvider>
          <MobileNav />
          {children}
        </AuthProvider>
      </body>
    </html>
  );
}

