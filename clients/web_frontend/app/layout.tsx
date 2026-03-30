import './globals.css'
import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Project Mata-Mata | Threat Intelligence',
  description: 'AI-Native Phishing Detection Dashboard',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className="bg-[#fffbf0] text-gray-900 min-h-screen antialiased">
        {children}
      </body>
    </html>
  )
}
