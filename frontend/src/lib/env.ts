/**
 * Frontend runtime configuration.
 *
 * The bearer token is read from the environment for now. `getAuthToken` is the
 * single seam to replace with the real session (the shared AuthContext) once it
 * lands — nothing else in the app reads the token directly.
 */

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1"

export function getAuthToken(): string | null {
  return process.env.NEXT_PUBLIC_API_TOKEN ?? null
}
