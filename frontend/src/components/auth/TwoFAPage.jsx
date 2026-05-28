/**
 * Two-factor authentication challenge page.
 * Shown after password login when the user has 2FA enabled.
 *
 * OWASP A07 – Identification and Authentication Failures
 *   - OTP field accepts 6 numeric digits only (no paste of sensitive data)
 *   - Auto-submit on 6th digit
 *   - Backup code fallback path
 *   - Generic error message (don't reveal remaining attempt count)
 *   - Clears code field on every failed attempt
 *
 * Place: frontend/src/pages/auth/TwoFAPage.jsx
 */

import { useState, useRef, useEffect } from 'react';
import { Link, Navigate } from 'react-router-dom';
import { ShieldCheck } from 'lucide-react';
import { useAuth } from '@/hooks/useAuth';
import { useAuthStore } from '@/store/authStore';

export default function TwoFAPage() {
  const { submit2FA, requires2FA } = useAuth();
  const [digits, setDigits]       = useState(Array(6).fill(''));
  const [useBackup, setUseBackup] = useState(false);
  const [backupCode, setBackupCode] = useState('');
  const [error, setError]         = useState('');
  const [loading, setLoading]     = useState(false);
  const inputsRef = useRef([]);

  // Guard: if no pending 2FA redirect to login
  if (!requires2FA) return <Navigate to="/login" replace />;

  // ── TOTP digit input ───────────────────────────────────────────────────────
  const handleDigitChange = async (idx, val) => {
    // Accept only single digit
    const digit = val.replace(/\D/g, '').slice(-1);
    const next  = [...digits];
    next[idx]   = digit;
    setDigits(next);

    if (digit && idx < 5) {
      inputsRef.current[idx + 1]?.focus();
    }

    // Auto-submit when all 6 filled
    if (next.every(Boolean) && next.join('').length === 6) {
      await submitCode(next.join(''));
    }
  };

  const handleDigitKeyDown = (idx, e) => {
    if (e.key === 'Backspace' && !digits[idx] && idx > 0) {
      inputsRef.current[idx - 1]?.focus();
    }
  };

  const handlePaste = (e) => {
    e.preventDefault();
    const pasted = e.clipboardData.getData('text').replace(/\D/g, '').slice(0, 6);
    if (pasted.length === 6) {
      setDigits(pasted.split(''));
      submitCode(pasted);
    }
  };

  // ── Submit ─────────────────────────────────────────────────────────────────
  const submitCode = async (code) => {
    setError('');
    setLoading(true);
    try {
      await submit2FA(code);
    } catch {
      // OWASP A07: generic — don't reveal attempts remaining
      setError('Invalid code. Please try again.');
      setDigits(Array(6).fill(''));
      inputsRef.current[0]?.focus();
    } finally {
      setLoading(false);
    }
  };

  const submitBackup = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await submit2FA(backupCode.trim().toUpperCase());
    } catch {
      setError('Invalid backup code.');
      setBackupCode('');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 px-4">
      <div className="w-full max-w-sm">

        <div className="mb-8 text-center">
          <ShieldCheck className="mx-auto h-12 w-12 text-indigo-600" />
          <h1 className="mt-3 text-xl font-bold text-gray-900">Two-factor authentication</h1>
          <p className="mt-1 text-sm text-gray-500">
            {useBackup
              ? 'Enter one of your 8-character backup codes.'
              : 'Open your authenticator app and enter the 6-digit code.'}
          </p>
        </div>

        <div className="card p-8">
          {error && (
            <div role="alert"
                 className="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
              {error}
            </div>
          )}

          {!useBackup ? (
            /* ── TOTP input ── */
            <div>
              <div className="flex justify-center gap-2" onPaste={handlePaste}
                   aria-label="Enter 6-digit authentication code">
                {digits.map((d, i) => (
                  <input
                    key={i}
                    ref={el => inputsRef.current[i] = el}
                    type="text"
                    inputMode="numeric"
                    pattern="\d*"
                    maxLength={1}
                    value={d}
                    autoFocus={i === 0}
                    disabled={loading}
                    aria-label={`Digit ${i + 1}`}
                    onChange={e => handleDigitChange(i, e.target.value)}
                    onKeyDown={e => handleDigitKeyDown(i, e)}
                    className="h-12 w-10 rounded-lg border border-gray-300 text-center text-lg
                               font-mono font-semibold tracking-widest shadow-sm
                               focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500
                               disabled:bg-gray-50 disabled:opacity-50"
                  />
                ))}
              </div>
              {loading && (
                <p className="mt-3 text-center text-sm text-gray-500">Verifying…</p>
              )}
            </div>
          ) : (
            /* ── Backup code ── */
            <form onSubmit={submitBackup} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1" htmlFor="backup">
                  Backup code
                </label>
                <input
                  id="backup" type="text" autoFocus
                  autoComplete="one-time-code"
                  placeholder="XXXXX-XXXXX"
                  value={backupCode}
                  onChange={e => setBackupCode(e.target.value)}
                  maxLength={11}
                  className="block w-full rounded-lg border border-gray-300 px-3 py-2 text-center
                             font-mono text-sm uppercase tracking-widest shadow-sm
                             focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                />
              </div>
              <button type="submit" disabled={loading || backupCode.length < 5}
                      className="inline-flex w-full items-center justify-center gap-2 rounded-lg bg-indigo-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50 transition-colors">
                {loading ? 'Verifying…' : 'Verify backup code'}
              </button>
            </form>
          )}

          <div className="mt-4 text-center">
            <button
              type="button"
              onClick={() => { setUseBackup(b => !b); setError(''); }}
              className="text-xs text-indigo-600 hover:text-indigo-700"
            >
              {useBackup ? '← Use authenticator app' : 'Use a backup code instead'}
            </button>
          </div>
        </div>

        <p className="mt-4 text-center text-sm text-gray-500">
          <Link to="/login" className="text-indigo-600 hover:text-indigo-700">
            ← Back to sign in
          </Link>
        </p>
      </div>
    </div>
  );
}