import type { Metadata } from "next";
import "./globals.css";
import Providers from "@/components/providers/Providers";

const inter = { variable: "--font-inter" };

export const metadata: Metadata = {
  title: {
    default: "PAC — Police Analytics Core",
    template: "%s | PAC",
  },
  description:
    "AI-powered Crime Intelligence and Investigation Platform for Karnataka Law Enforcement",
  keywords: ["police", "crime analytics", "investigation", "intelligence", "CCTNS"],
  robots: "noindex, nofollow",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={`${inter.variable} font-sans bg-[#0d1117] text-[#e6edf3] antialiased`}>
        <Providers>
          {children}
        </Providers>
      </body>
    </html>
  );
}
