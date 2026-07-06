'use client'

import { GoogleLogin, type CredentialResponse } from '@react-oauth/google'
import { useRouter } from 'next/navigation'

import { googleLogin } from '@/lib/api/auth'
import { useAuth } from '@/lib/auth/AuthContext'

export default function Login() {
  const router = useRouter()
  const { login } = useAuth()

  async function handleSuccess(response: CredentialResponse) {
    const credential = response.credential
    if (!credential) return

    try {
      const token = await googleLogin(credential)
      await login(token.access_token)
      router.push('/')
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
