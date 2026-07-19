'use client'

import { GoogleLogin, type CredentialResponse } from '@react-oauth/google'
import { useRouter } from 'next/navigation'

import { googleLogin } from '@/lib/api/auth'
import { useAuth } from '@/lib/auth/AuthContext'
import { postAuthDestination } from '@/lib/onboarding/routing'

/**
 * Shared "Continue with Google" block (divider + button + legal), used by both
 * the sign-in and create-account screens. Uses Google's own widget because the
 * credential (ID-token) flow the backend verifies requires it.
 */
export function GoogleAuthButton() {
  const router = useRouter()
  const { login } = useAuth()

  async function handleSuccess(response: CredentialResponse) {
    const credential = response.credential
    if (!credential) return
    try {
      await googleLogin(credential)
      await login()
      router.push(await postAuthDestination())
    } catch (err) {
      console.error('Google login failed:', err)
    }
  }

  return (
    <div>
      <div className="my-6 flex items-center gap-4">
        <div className="h-px flex-1 bg-brand-border" />
        <span className="font-mono text-xs text-brand-muted">OR</span>
        <div className="h-px flex-1 bg-brand-border" />
      </div>

      <div className="flex justify-center">
        <GoogleLogin
          onSuccess={handleSuccess}
          onError={() => console.error('Google login failed')}
          theme="outline"
          size="large"
          shape="pill"
          text="continue_with"
          width="384"
        />
      </div>
    </div>
  )
}
