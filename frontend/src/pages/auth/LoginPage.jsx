/**
 * Login page — email + password with error handling.
 * Redirects to the `?next=` path after successful login.
 *
 * Place: frontend/src/pages/auth/LoginPage.jsx
 */

import { useState } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { z } from 'zod';
import { zodResolver } from '@hookform/resolvers/zod';
import { Eye, EyeOff, Mail, Lock } from 'lucide-react';
import { useAuth } from '@/hooks/useAuth';

// ── Validation schema ─────────────────────────────────────────────────────────
const schema = z.object({
    email:    z.string().min(1, 'Email or username is required'),
  password: z.string().min(1, 'Password is required'),
});

export default function LoginPage() {
  const navigate  = useNavigate();
  const location  = useLocation();
  const { login } = useAuth();

  const [showPwd, setShowPwd] = useState(false);
  const [apiError, setApiError] = useState('');

  const { register, handleSubmit, formState: { errors, isSubmitting } } =
    useForm({ resolver: zodResolver(schema) });

  const onSubmit = async (data) => {
    setApiError('');
    try {
      // login() handles navigation (to /dashboard or /login/2fa)
      await login(data);
    } catch (err) {
      setApiError(err?.message || 'Invalid email or password.');
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 px-4">
      <div className="w-full max-w-sm">

        {/* Logo */}
        <div className="mb-8 text-center">
          <span className="text-4xl">✉</span>
          <h1 className="mt-2 text-2xl font-bold text-gray-900">MailFlow</h1>
          <p className="mt-1 text-sm text-gray-500">Sign in to your account</p>
        </div>

        {/* Card */}
        <div className="card p-8">

          {/* API error banner */}
          {apiError && (
            <div className="mb-4 rounded-lg border border-red-200 bg-red-50
                            px-4 py-3 text-sm text-red-700 animate-fade-in">
              {apiError}
            </div>
          )}

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-5" noValidate>

            {/* Email */}
            <div>
              <label className="label" htmlFor="email">Email or username</label>
              <div className="relative">
                <Mail className="pointer-events-none absolute left-3 top-1/2
                                 -translate-y-1/2 h-4 w-4 text-gray-400" />
                <input
                  id="email"
                  type="text"
                  autoComplete="username email"
                  autoFocus
                  placeholder="you@example.com or jane_smith"
                  className={`input pl-9 ${errors.email ? 'border-red-400 focus:ring-red-400' : ''}`}
                  {...register('email')}
                />
              </div>
              {errors.email && (
                <p className="mt-1 text-xs text-red-600">{errors.email.message}</p>
              )}
            </div>

            {/* Password */}
            <div>
              <div className="flex items-center justify-between mb-1">
                <label className="label mb-0" htmlFor="password">Password</label>
                <Link
                  to="/forgot-password"
                  className="text-xs text-brand-600 hover:text-brand-700"
                >
                  Forgot password?
                </Link>
              </div>
              <div className="relative">
                <Lock className="pointer-events-none absolute left-3 top-1/2
                                 -translate-y-1/2 h-4 w-4 text-gray-400" />
                <input
                  id="password"
                  type={showPwd ? 'text' : 'password'}
                  autoComplete="current-password"
                  placeholder="••••••••"
                  className={`input pl-9 pr-10 ${errors.password ? 'border-red-400 focus:ring-red-400' : ''}`}
                  {...register('password')}
                />
                <button
                  type="button"
                  onClick={() => setShowPwd(v => !v)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                  tabIndex={-1}
                >
                  {showPwd ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
              {errors.password && (
                <p className="mt-1 text-xs text-red-600">{errors.password.message}</p>
              )}
            </div>

            {/* Submit */}
            <button
              type="submit"
              disabled={isSubmitting}
              className="btn-primary w-full justify-center py-2.5"
            >
              {isSubmitting ? (
                <>
                  <svg className="animate-spin h-4 w-4 mr-2" viewBox="0 0 24 24" fill="none">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
                  </svg>
                  Signing in…
                </>
              ) : 'Sign in'}
            </button>
          </form>
        </div>

        {/* Sign up link */}
        <p className="mt-6 text-center text-sm text-gray-500">
          Don't have an account?{' '}
          <Link to="/signup" className="font-medium text-brand-600 hover:text-brand-700">
            Create one free
          </Link>
        </p>
      </div>
    </div>
  );
}