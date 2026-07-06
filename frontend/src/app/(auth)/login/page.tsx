'use client'

import { GoogleLogin, type CredentialResponse } from '@react-oauth/google'

export default function Login() {
  function handleSuccess(response: CredentialResponse) {
    const credential = response.credential
    if (!credential) return

    
    console.log('Google ID token (credential):', credential)
  }

  return (
    <GoogleLogin
      onSuccess={handleSuccess}
      onError={() => console.error('Google login failed')}
    />
  )
}
