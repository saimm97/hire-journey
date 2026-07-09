import type { Metadata } from "next"
import { Bricolage_Grotesque, Geist, Geist_Mono, Inter } from "next/font/google"

import "./globals.css"
import { cn } from "@/lib/utils"

const inter = Inter({ subsets: ["latin"], variable: "--font-sans" })
const bricolage = Bricolage_Grotesque({ subsets: ["latin"], variable: "--font-bricolage" })
const geistSans = Geist({ subsets: ["latin"], variable: "--font-geist-sans" })
const geistMono = Geist_Mono({ subsets: ["latin"], variable: "--font-geist-mono" })

export const metadata: Metadata = {
  title: "Hire Journey",
  description: "Your job-search partner",
}

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html
      lang="en"
      className={cn(
        "h-full antialiased font-sans",
        inter.variable,
        bricolage.variable,
        geistSans.variable,
        geistMono.variable,
      )}
    >
      <body className="min-h-full flex flex-col bg-brand-paper text-brand-ink">{children}</body>
    </html>
  )
}
