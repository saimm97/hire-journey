'use client'

import { zodResolver } from '@hookform/resolvers/zod'
import { Eye, EyeOff, Loader2 } from 'lucide-react'
import { useRouter } from 'next/navigation'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { z } from 'zod'

import { GoogleAuthButton } from '@/components/auth/GoogleAuthButton'
import { Button } from '@/components/ui/button'
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form'
import { Input } from '@/components/ui/input'
import { passwordLogin } from '@/lib/api/auth'
import { ApiError } from '@/lib/api/client'
import { useAuth } from '@/lib/auth/AuthContext'
import { cn } from '@/lib/utils'

const schema = z.object({
  identifier: z.string().min(1, 'Enter your email or username'),
  password: z.string().min(1, 'Enter your password'),
})

type FormValues = z.infer<typeof schema>

const LABEL = 'font-mono text-[11px] uppercase tracking-wide text-brand-muted'
const FIELD =
  'h-11 rounded-lg border-brand-border bg-white shadow-sm placeholder:text-brand-muted/60 focus-visible:border-brand-violet focus-visible:ring-2 focus-visible:ring-brand-violet/25'

export default function Login() {
  const router = useRouter()
  const { login } = useAuth()
  const [showPassword, setShowPassword] = useState(false)

  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { identifier: '', password: '' },
  })

  async function onSubmit(values: FormValues) {
    try {
      const token = await passwordLogin(values.identifier, values.password)
      await login(token.access_token)
      router.push('/')
    } catch (err) {
      const message = err instanceof ApiError ? err.message : 'Something went wrong'
      form.setError('root', { message })
    }
  }

  return (
    <div>
      <Form {...form}>
        <form onSubmit={form.handleSubmit(onSubmit)} className="flex flex-col gap-5">
          <FormField
            control={form.control}
            name="identifier"
            render={({ field }) => (
              <FormItem>
                <FormLabel className={LABEL}>Email or username</FormLabel>
                <FormControl>
                  <Input placeholder="you@example.com" className={FIELD} {...field} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
          <FormField
            control={form.control}
            name="password"
            render={({ field }) => (
              <FormItem>
                <div className="flex items-center justify-between">
                  <FormLabel className={LABEL}>Password</FormLabel>
                  <a href="#" className="text-sm text-brand-violet hover:underline">
                    Forgot?
                  </a>
                </div>
                <FormControl>
                  <div className="relative">
                    <Input
                      type={showPassword ? 'text' : 'password'}
                      placeholder="••••••••"
                      className={cn(FIELD, 'pr-11')}
                      {...field}
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword((v) => !v)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-brand-muted hover:text-brand-ink"
                      aria-label={showPassword ? 'Hide password' : 'Show password'}
                    >
                      {showPassword ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}
                    </button>
                  </div>
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />

          {form.formState.errors.root && (
            <p className="text-sm text-red-600">{form.formState.errors.root.message}</p>
          )}

          <Button
            type="submit"
            disabled={form.formState.isSubmitting}
            className="mt-1 h-12 w-full rounded-full bg-brand-violet font-semibold text-white shadow-md hover:bg-brand-violet-dark"
          >
            {form.formState.isSubmitting ? (
              <>
                <Loader2 className="h-5 w-5 animate-spin" />
                Signing in…
              </>
            ) : (
              'Sign In'
            )}
          </Button>
        </form>
      </Form>

      <GoogleAuthButton />
    </div>
  )
}
