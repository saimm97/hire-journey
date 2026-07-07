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
  created_at: string
}

/** Exchange a Google ID token (credential) for our own JWT. */
export function googleLogin(credential: string): Promise<Token> {
  return apiRequest<Token>('/auth/google', {
    method: 'POST',
    body: { credential },
  })
}

/** Resolve a JWT to the current user. Throws ApiError(401) if the token is stale. */
export function getMe(token: string): Promise<User> {
  return apiRequest<User>('/auth/me', { token })
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
export function passwordLogin(identifier: string, password: string): Promise<Token> {
  return apiRequest<Token>('/auth/login', {
    method: 'POST',
    form: true,
    body: { username: identifier, password },
  })
}
