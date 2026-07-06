'use client'

import { GoogleLogin, type CredentialResponse } from '@react-oauth/google'
import { googleLogin } from '@/lib/api/auth'

export default function Login() {
  async function handleSuccess(response: CredentialResponse) {
    const credential = response.credential
    if (!credential) return

    try {
      const token = await googleLogin(credential)
      // TEMP: next step stores this JWT and redirects into the app.
      console.log('Our JWT:', token.access_token)
    } catch (err) {
      console.error('Login failed:', err)
    }
  }

  return (
    <GoogleLogin
      onSuccess={handleSuccess}
      onError={() => console.error('Google login failed')}
    />
  )
}
