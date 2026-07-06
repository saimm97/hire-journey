'use client'

import { GoogleOAuthProvider } from '@react-oauth/google'

export default function AuthLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <GoogleOAuthProvider clientId={process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID!}>
      <main className="flex min-h-screen items-center justify-center p-4">
        <div className="w-full max-w-sm rounded-xl border border-black/10 p-8 shadow-sm">
          {children}
        </div>
      </main>
    </GoogleOAuthProvider>
  )
}
