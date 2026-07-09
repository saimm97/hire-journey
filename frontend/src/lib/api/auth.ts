import { apiRequest } from './client'

/** Mirrors the backend `Token` schema. */
export type Token = {
  access_token: string
  token_type: string
}

/** Mirrors the backend `UserRead` schema. */
export type User = {
  user_id: string
  username: string
  email: string
}

/** Exchange a Google ID token (credential) for our own JWT. */
export function googleLogin(credential: string): Promise<Token> {
  return apiRequest<Token>('/auth/google', {
    method: 'POST',
    body: { credential },
  })
}

/** Resolve the current session cookie to the logged-in user. Throws ApiError(401) if no valid session. */
export function getMe(): Promise<User> {
  return apiRequest<User>('/auth/me')
}

/** Clear the session cookie on the backend. */
export function logoutUser(): Promise<void> {
  return apiRequest<void>('/auth/logout', { method: 'POST' })
}

/** Create an account. Returns the new user — does NOT log them in (no token). */
export function registerUser(data: {
  username: string
  email: string
  password: string
}): Promise<User> {
  return apiRequest<User>('/auth/register', { method: 'POST', body: data })
}

/**
 * Email/username + password login. The backend uses OAuth2PasswordRequestForm,
 * so this must be form-encoded with the identifier under the `username` field.
 */
export function loginWithPassword(identifier: string, password: string): Promise<Token> {
  return apiRequest<Token>('/auth/login', {
    method: 'POST',
    form: true,
    body: { username: identifier, password },
  })
}
