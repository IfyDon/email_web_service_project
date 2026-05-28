/**
 * Signup page.
 *
 *   - Real-time password strength indicator (PasswordStrength component)
 *   - Password confirmation matching
 *   - Rate-limit feedback (429 Retry-After)
 *   - Generic error messages — never leak "email already registered" to prevent
 *     account enumeration (mirrors Django's allauth behaviour)
 *
 * Place: frontend/src/pages/auth/SignupPage.jsx
 */

import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { z } from 'zod';
import { zodResolver } from '@hookform/resolvers/zod';
import { Eye, EyeOff, Mail, Lock, User } from 'lucide-react';
import { useAuth } from '@/hooks/useAuth';
import PasswordStrength from '@/components/auth/PasswordStrength';

// ── Schema (OWASP A07 — NIST 800-63B minimum 8 chars; we recommend 12) ────────
const schema = z
  .object({
    full_name:  z.string().trim().min(1, 'Name is required').max(255),
    email:      z.string().email('Enter a valid email address'),
    password:   z.string()
      .min(8, 'Password must be at least 8 characters')
      .max(128, 'Password is too long'),
    password2:  z.string(),
  })
  .refine(d => d.password === d.password2, {
    message: 'Passwords do not match',
    path:    ['password2'],
  });

export default function SignupPage() {
  const { signup }              = useAuth();
  const [showPwd, setShowPwd]   = useState(false);
  const [apiError, setApiError] = useState('');
  const [success, setSuccess]   = useState(false);

  const {
    register,
    handleSubmit,
    watch,
    formState: { errors, isSubmitting },
  } = useForm({ resolver: zodResolver(schema) });

  const watchedPwd = watch('password', '');

  const onSubmit = async (data) => {
    setApiError('');
    try {
      await signup({ email: data.email, full_name: data.full_name, password: data.password, password2: data.password2 });
      setSuccess(true);
    } catch (err) {
      if (err.status === 429) {
        const wait = err.retryAfter ?? 60;
        setApiError(`Too many attempts. Please wait ${wait} seconds and try again.`);
      } else {
        // OWASP A07: generic message — don't reveal if email already exists
        setApiError('Could not create your account. Please check your details and try again.');
      }
    }
  };

  if (success) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-50 px-4">
        <div className="w-full max-w-sm text-center card p-8">
          <span className="text-4xl">📬</span>
          <h2 className="mt-3 text-xl font-bold text-gray-900">Check your inbox</h2>
          <p className="mt-2 text-sm text-gray-500">
            We've sent a verification link to your email address.
            Click it to activate your account.
          </p>
          <Link to="/login" className="mt-6 inline-block text-sm font-medium text-indigo-600 hover:text-indigo-700">
            Back to sign in →
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 px-4 py-10">
      <div className="w-full max-w-sm">

        <div className="mb-8 text-center">
          <span className="text-4xl">✉</span>
          <h1 className="mt-2 text-2xl font-bold text-gray-900">Create your account</h1>
          <p className="mt-1 text-sm text-gray-500">Free to get started</p>
        </div>

        <div className="card p-8">
          {apiError && (
            <div role="alert"
                 className="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 animate-fade-in">
              {apiError}
            </div>
          )}

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-5" noValidate>

            {/* Full name */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1" htmlFor="full_name">
                Full name <span className="text-red-500" aria-hidden>*</span>
              </label>
              <div className="relative">
                <User className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
                <input id="full_name" type="text" autoComplete="name" autoFocus
                       placeholder="Alice Smith"
                       aria-invalid={!!errors.full_name}
                       className={`block w-full rounded-lg border px-3 py-2 pl-9 text-sm shadow-sm focus:outline-none focus:ring-1 ${errors.full_name ? 'border-red-400 focus:ring-red-400' : 'border-gray-300 focus:border-indigo-500 focus:ring-indigo-500'}`}
                       {...register('full_name')} />
              </div>
              {errors.full_name && <p role="alert" className="mt-1 text-xs text-red-600">{errors.full_name.message}</p>}
            </div>

            {/* Email */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1" htmlFor="email">
                Email address <span className="text-red-500" aria-hidden>*</span>
              </label>
              <div className="relative">
                <Mail className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
                <input id="email" type="email" autoComplete="email"
                       placeholder="you@example.com"
                       aria-invalid={!!errors.email}
                       className={`block w-full rounded-lg border px-3 py-2 pl-9 text-sm shadow-sm focus:outline-none focus:ring-1 ${errors.email ? 'border-red-400 focus:ring-red-400' : 'border-gray-300 focus:border-indigo-500 focus:ring-indigo-500'}`}
                       {...register('email')} />
              </div>
              {errors.email && <p role="alert" className="mt-1 text-xs text-red-600">{errors.email.message}</p>}
            </div>

            {/* Password */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1" htmlFor="password">
                Password <span className="text-red-500" aria-hidden>*</span>
              </label>
              <div className="relative">
                <Lock className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
                <input id="password" type={showPwd ? 'text' : 'password'}
                       autoComplete="new-password"
                       placeholder="Min. 8 characters"
                       aria-invalid={!!errors.password}
                       aria-describedby="pwd-strength"
                       className={`block w-full rounded-lg border px-3 py-2 pl-9 pr-10 text-sm shadow-sm focus:outline-none focus:ring-1 ${errors.password ? 'border-red-400 focus:ring-red-400' : 'border-gray-300 focus:border-indigo-500 focus:ring-indigo-500'}`}
                       {...register('password')} />
                <button type="button" tabIndex={-1} onClick={() => setShowPwd(v => !v)}
                        className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600">
                  {showPwd ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
              {errors.password && <p role="alert" className="mt-1 text-xs text-red-600">{errors.password.message}</p>}
              {/* OWASP A07 — live password strength */}
              <div id="pwd-strength">
                <PasswordStrength password={watchedPwd} />
              </div>
            </div>

            {/* Confirm password */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1" htmlFor="password2">
                Confirm password <span className="text-red-500" aria-hidden>*</span>
              </label>
              <div className="relative">
                <Lock className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
                <input id="password2" type={showPwd ? 'text' : 'password'}
                       autoComplete="new-password"
                       placeholder="Re-enter password"
                       aria-invalid={!!errors.password2}
                       className={`block w-full rounded-lg border px-3 py-2 pl-9 text-sm shadow-sm focus:outline-none focus:ring-1 ${errors.password2 ? 'border-red-400 focus:ring-red-400' : 'border-gray-300 focus:border-indigo-500 focus:ring-indigo-500'}`}
                       {...register('password2')} />
              </div>
              {errors.password2 && <p role="alert" className="mt-1 text-xs text-red-600">{errors.password2.message}</p>}
            </div>

            <button type="submit" disabled={isSubmitting}
                    className="mt-1 inline-flex w-full items-center justify-center gap-2 rounded-lg bg-indigo-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors">
              {isSubmitting ? 'Creating account…' : 'Create account'}
            </button>
          </form>
        </div>

        <p className="mt-6 text-center text-sm text-gray-500">
          Already have an account?{' '}
          <Link to="/login" className="font-medium text-indigo-600 hover:text-indigo-700">Sign in</Link>
        </p>
      </div>
    </div>
  );
}