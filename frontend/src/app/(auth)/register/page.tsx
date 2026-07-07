'use client'

import { zodResolver } from '@hookform/resolvers/zod'
import { ArrowRight, Eye, EyeOff, Loader2 } from 'lucide-react'
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
import { loginWithPassword, registerUser } from '@/lib/api/auth'
import { ApiError } from '@/lib/api/client'
import { useAuth } from '@/lib/auth/AuthContext'
import { cn } from '@/lib/utils'

// match with backend UserCreate constraints
const schema = z.object({
  username: z
    .string()
    .min(3, 'At least 3 characters')
    .max(50, 'At most 50 characters')
    .regex(/^[A-Za-z0-9_]+$/, 'Letters, numbers, and underscores only'),
  email: z.email('Enter a valid email'),
  password: z.string().min(8, 'At least 8 characters').max(128, 'At most 128 characters'),
})

type FormValues = z.infer<typeof schema>

const LABEL = 'font-mono text-[11px] uppercase tracking-wide text-brand-muted'
const FIELD =
  'h-11 rounded-lg border-brand-border bg-white shadow-sm placeholder:text-brand-muted/60 focus-visible:border-brand-violet focus-visible:ring-2 focus-visible:ring-brand-violet/25'

function strengthOf(pw: string): number {
  if (!pw) return 0;
  let s = 0
  if (pw.length >= 8) s++
  if (/[A-Z]/.test(pw) && /[a-z]/.test(pw)) s++
  if (/[0-9]/.test(pw) || /[^A-Za-z0-9]/.test(pw)) s++
  return s
}

export default function Register() {
  const router = useRouter()
  const { login } = useAuth()
  const [showPassword, setShowPassword] = useState(false)

  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { username: '', email: '', password: '' },
  })

  const strength = strengthOf(form.watch('password'))
  const strengthColor = ['bg-brand-border', 'bg-red-500', 'bg-amber-500', 'bg-brand-emerald'][
    strength
  ]
  const strengthLabel = ['', 'Weak', 'Fair', 'Good'][strength]

  async function onSubmit(values: FormValues) {
    try {
      await registerUser(values) // 1. create account
      const token = await loginWithPassword(values.email, values.password) // 2. auto-login
      await login(token.access_token) // 3. store + hydrate session
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
            name="username"
            render={({ field }) => (
              <FormItem>
                <FormLabel className={LABEL}>Username</FormLabel>
                <FormControl>
                  <Input placeholder="e.g. design_sarah" className={FIELD} {...field} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
          <FormField
            control={form.control}
            name="email"
            render={({ field }) => (
              <FormItem>
                <FormLabel className={LABEL}>Email address</FormLabel>
                <FormControl>
                  <Input type="email" placeholder="you@example.com" className={FIELD} {...field} />
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
                <FormLabel className={LABEL}>Password</FormLabel>
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
                {/* strength meter */}
                <div className="mt-2 flex items-center gap-2">
                  <div className="flex flex-1 gap-1">
                    {[0, 1, 2].map((i) => (
                      <div
                        key={i}
                        className={cn(
                          'h-1 flex-1 rounded-full',
                          i < strength ? strengthColor : 'bg-brand-border',
                        )}
                      />
                    ))}
                  </div>
                  <span className="w-8 font-mono text-[11px] text-brand-muted">
                    {strengthLabel}
                  </span>
                </div>
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
            className="mt-1 h-12 w-full rounded-full bg-brand-coral font-semibold text-white shadow-md hover:bg-brand-coral-dark"
          >
            {form.formState.isSubmitting ? (
              <>
                <Loader2 className="h-5 w-5 animate-spin" />
                Creating account…
              </>
            ) : (
              <>
                Start Your Journey
                <ArrowRight className="h-5 w-5" />
              </>
            )}
          </Button>
        </form>
      </Form>

      <GoogleAuthButton />
    </div>
  )
}
