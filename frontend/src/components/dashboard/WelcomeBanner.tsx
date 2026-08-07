"use client"

import { useAuth } from "@/lib/auth/AuthContext"

const QUOTES = [
  "Every application is a rep. Reps compound.",
  "The right role is looking for you too — help it find you.",
  "Rejection is redirection with worse branding.",
  "You only need one yes.",
  "Consistency beats intensity. Show up today.",
  "Your next interview is practice for the one that matters.",
  "Strong profiles aren't written once — they're sharpened.",
  "Luck is what happens when preparation meets opportunity.",
]

/** Day-of-year index: stable across server and client renders (no hydration mismatch). */
function quoteOfTheDay(): string {
  const now = new Date()
  const start = Date.UTC(now.getUTCFullYear(), 0, 0)
  const day = Math.floor((now.getTime() - start) / 86_400_000)
  return QUOTES[day % QUOTES.length]
}

/** Greeting + a bit of encouragement, rotating daily. */
export function WelcomeBanner() {
  const { user } = useAuth()

  return (
    <div className="space-y-3">
      <h1 className="text-[32px] font-semibold leading-10 tracking-tight text-brand-ink">
        Welcome back{user ? `, ${user.username}` : ""}.
      </h1>
      <p className="max-w-xl text-lg text-brand-muted">{quoteOfTheDay()}</p>
    </div>
  )
}
