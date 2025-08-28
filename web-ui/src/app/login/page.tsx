'use client'

import React from 'react'
import { useRouter } from 'next/navigation'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import * as z from 'zod'
import Link from 'next/link'
import { Eye, EyeOff, Phone, Lock, Mail } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import { useAuthStore } from '@/store/auth'
import { useUIStore } from '@/store/ui'

const loginSchema = z.object({
  email: z.string().email('Please enter a valid email address'),
  password: z.string().min(6, 'Password must be at least 6 characters'),
  rememberMe: z.boolean().default(false),
})

type LoginFormData = z.infer<typeof loginSchema>

export default function LoginPage() {
  const router = useRouter()
  const { login, isLoading, error } = useAuthStore()
  const { showErrorToast, showSuccessToast } = useUIStore()
  const [showPassword, setShowPassword] = React.useState(false)

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
    setError,
  } = useForm<LoginFormData>({
    resolver: zodResolver(loginSchema),
    defaultValues: {
      email: '',
      password: '',
      rememberMe: false,
    },
  })

  const onSubmit = async (data: LoginFormData) => {
    try {
      await login(data)
      showSuccessToast('Successfully logged in')
      router.push('/dashboard')
    } catch (error: any) {
      const errorMessage = error.response?.data?.error?.message || error.message || 'Login failed'
      
      if (errorMessage.includes('email')) {
        setError('email', { message: errorMessage })
      } else if (errorMessage.includes('password')) {
        setError('password', { message: errorMessage })
      } else {
        showErrorToast(errorMessage, 'Login Failed')
      }
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-950 dark:to-slate-900 p-4">
      <div className="w-full max-w-md">
        {/* Brand Header */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-primary rounded-2xl mb-4">
            <Phone className="w-8 h-8 text-primary-foreground" />
          </div>
          <h1 className="text-3xl font-bold text-foreground">NeverMissCall</h1>
          <p className="text-muted-foreground mt-2">Welcome back to your dashboard</p>
        </div>

        <Card className="shadow-xl border-0">
          <CardHeader className="space-y-1 text-center">
            <CardTitle className="text-2xl font-bold">Sign In</CardTitle>
            <CardDescription>
              Enter your credentials to access your account
            </CardDescription>
          </CardHeader>
          
          <form onSubmit={handleSubmit(onSubmit)}>
            <CardContent className="space-y-4">
              {/* Email Field */}
              <div className="space-y-2">
                <label htmlFor="email" className="text-sm font-medium text-foreground">
                  Email Address
                </label>
                <div className="relative">
                  <Mail className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                  <Input
                    id="email"
                    type="email"
                    placeholder="your@email.com"
                    className={`pl-10 ${errors.email ? 'border-destructive focus-visible:ring-destructive' : ''}`}
                    {...register('email')}
                    disabled={isLoading || isSubmitting}
                  />
                </div>
                {errors.email && (
                  <p className="text-sm text-destructive">{errors.email.message}</p>
                )}
              </div>

              {/* Password Field */}
              <div className="space-y-2">
                <label htmlFor="password" className="text-sm font-medium text-foreground">
                  Password
                </label>
                <div className="relative">
                  <Lock className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                  <Input
                    id="password"
                    type={showPassword ? 'text' : 'password'}
                    placeholder="Enter your password"
                    className={`pl-10 pr-10 ${errors.password ? 'border-destructive focus-visible:ring-destructive' : ''}`}
                    {...register('password')}
                    disabled={isLoading || isSubmitting}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-3 text-muted-foreground hover:text-foreground"
                    disabled={isLoading || isSubmitting}
                  >
                    {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                </div>
                {errors.password && (
                  <p className="text-sm text-destructive">{errors.password.message}</p>
                )}
              </div>

              {/* Remember Me & Forgot Password */}
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <input
                    id="rememberMe"
                    type="checkbox"
                    className="h-4 w-4 rounded border border-input bg-background"
                    {...register('rememberMe')}
                    disabled={isLoading || isSubmitting}
                  />
                  <label
                    htmlFor="rememberMe"
                    className="text-sm font-medium text-muted-foreground hover:text-foreground cursor-pointer"
                  >
                    Remember me
                  </label>
                </div>
                <Link
                  href="/reset-password"
                  className="text-sm text-primary hover:text-primary/80 font-medium"
                >
                  Forgot password?
                </Link>
              </div>

              {/* Error Message */}
              {error && (
                <div className="p-3 text-sm text-destructive bg-destructive/10 border border-destructive/20 rounded-md">
                  {error}
                </div>
              )}
            </CardContent>

            <CardFooter className="flex flex-col space-y-4">
              <Button
                type="submit"
                className="w-full"
                loading={isLoading || isSubmitting}
                disabled={isLoading || isSubmitting}
              >
                {isLoading || isSubmitting ? 'Signing In...' : 'Sign In'}
              </Button>

              <div className="text-center text-sm text-muted-foreground">
                Don&apos;t have an account?{' '}
                <Link href="/signup" className="text-primary hover:text-primary/80 font-medium">
                  Contact support
                </Link>
              </div>
            </CardFooter>
          </form>
        </Card>

        {/* Demo Credentials */}
        <div className="mt-6 p-4 bg-muted/50 rounded-lg border border-dashed border-muted-foreground/20">
          <h3 className="text-sm font-medium text-foreground mb-2">Demo Credentials</h3>
          <div className="text-sm text-muted-foreground space-y-1">
            <p><strong>Email:</strong> demo@nevermisscall.com</p>
            <p><strong>Password:</strong> demo123</p>
          </div>
        </div>

        {/* Footer */}
        <div className="mt-8 text-center text-xs text-muted-foreground">
          <p>&copy; 2024 NeverMissCall. All rights reserved.</p>
          <div className="flex items-center justify-center space-x-4 mt-2">
            <Link href="/privacy" className="hover:text-foreground">Privacy Policy</Link>
            <span>•</span>
            <Link href="/terms" className="hover:text-foreground">Terms of Service</Link>
            <span>•</span>
            <Link href="/support" className="hover:text-foreground">Support</Link>
          </div>
        </div>
      </div>
    </div>
  )
}