/**
 * Account settings page — profile, password change, 2FA management.
 *
 * Security notes:
 *  - Password change requires current password verification (OWASP A07)
 *  - 2FA disable requires password confirmation
 *  - QR code rendered via data URL (no external image requests)
 *  - Backup codes auto-cleared from state after 3 minutes
 *  - Session re-validated after password change (Django handles cookie rotation)
 *
 * Place: frontend/src/pages/settings/AccountPage.jsx
 */

import { useState, useEffect, useCallback } from 'react';
import { useForm } from 'react-hook-form';
import { z } from 'zod';
import { zodResolver } from '@hookform/resolvers/zod';
import { Eye, EyeOff, ShieldCheck, ShieldOff, RefreshCw, Download } from 'lucide-react';
import { authApi } from '@/api/auth';
import { useAuth } from '@/hooks/useAuth';
import PasswordStrength from '@/components/auth/PasswordStrength';

const BACKUP_CLEAR_MS = 180_000;  // 3 minutes

// ── Schemas ───────────────────────────────────────────────────────────────────
const profileSchema = z.object({
  full_name: z.string().trim().min(1, 'Name is required').max(255),
});

const passwordSchema = z.object({
  current_password: z.string().min(1, 'Current password is required'),
  new_password:     z.string().min(8, 'Must be at least 8 characters').max(128),
  new_password2:    z.string(),
}).refine(d => d.new_password === d.new_password2, {
  message: 'Passwords do not match', path: ['new_password2'],
});

const disable2faSchema = z.object({
  password: z.string().min(1, 'Password is required'),
});

// ── Profile section ───────────────────────────────────────────────────────────
function ProfileSection({ user, onUpdate }) {
  const [success, setSuccess]   = useState('');
  const [apiError, setApiError] = useState('');
  const { register, handleSubmit, formState: { errors, isSubmitting } } =
    useForm({ resolver: zodResolver(profileSchema), defaultValues: { full_name: user?.full_name ?? '' } });

  const onSubmit = async (data) => {
    setApiError(''); setSuccess('');
    try {
      const updated = await authApi.updateMe(data);
      onUpdate(updated);
      setSuccess('Profile updated.');
    } catch (err) {
      setApiError(err?.message ?? 'Update failed.');
    }
  };

  return (
    <section className="bg-white rounded-xl border border-gray-200 shadow-sm p-6">
      <h2 className="text-sm font-semibold text-gray-800 mb-4">Profile</h2>
      {success  && <div role="status" className="mb-3 rounded-lg bg-green-50 border border-green-200 px-4 py-2 text-sm text-green-700">{success}</div>}
      {apiError && <div role="alert"  className="mb-3 rounded-lg bg-red-50 border border-red-200 px-4 py-2 text-sm text-red-700">{apiError}</div>}
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1" htmlFor="full_name">Full name</label>
          <input id="full_name" type="text" autoComplete="name"
                 aria-invalid={!!errors.full_name}
                 className={`block w-full rounded-lg border px-3 py-2 text-sm shadow-sm focus:outline-none focus:ring-1 ${errors.full_name ? 'border-red-400 focus:ring-red-400' : 'border-gray-300 focus:border-indigo-500 focus:ring-indigo-500'}`}
                 {...register('full_name')} />
          {errors.full_name && <p role="alert" className="mt-1 text-xs text-red-600">{errors.full_name.message}</p>}
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
          <input type="email" disabled value={user?.email ?? ''} aria-readonly="true"
                 className="block w-full rounded-lg border border-gray-200 px-3 py-2 text-sm bg-gray-50 text-gray-500 cursor-not-allowed" />
          <p className="mt-1 text-xs text-gray-400">Email cannot be changed. Contact support if needed.</p>
        </div>
        <button type="submit" disabled={isSubmitting}
                className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50 transition-colors">
          {isSubmitting ? 'Saving…' : 'Save profile'}
        </button>
      </form>
    </section>
  );
}

// ── Password section ──────────────────────────────────────────────────────────
function PasswordSection() {
  const [showCurrent, setShowCurrent] = useState(false);
  const [showNew,     setShowNew]     = useState(false);
  const [success, setSuccess]         = useState('');
  const [apiError, setApiError]       = useState('');
  const { register, handleSubmit, watch, reset, formState: { errors, isSubmitting } } =
    useForm({ resolver: zodResolver(passwordSchema) });
  const newPwd = watch('new_password', '');

  const onSubmit = async (data) => {
    setApiError(''); setSuccess('');
    try {
      await authApi.changePassword(data);
      setSuccess('Password updated. You may need to log in again on other devices.');
      reset();
    } catch (err) {
      // OWASP A07: generic message — don't confirm whether current password was wrong
      setApiError(err?.message ?? 'Password change failed. Check your current password.');
    }
  };

  return (
    <section className="bg-white rounded-xl border border-gray-200 shadow-sm p-6">
      <h2 className="text-sm font-semibold text-gray-800 mb-4">Change Password</h2>
      {success  && <div role="status" className="mb-3 rounded-lg bg-green-50 border border-green-200 px-4 py-2 text-sm text-green-700">{success}</div>}
      {apiError && <div role="alert"  className="mb-3 rounded-lg bg-red-50 border border-red-200 px-4 py-2 text-sm text-red-700">{apiError}</div>}
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
        {/* Current password */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1" htmlFor="current_password">Current password</label>
          <div className="relative">
            <input id="current_password" type={showCurrent ? 'text' : 'password'}
                   autoComplete="current-password" aria-invalid={!!errors.current_password}
                   className={`block w-full rounded-lg border px-3 py-2 pr-10 text-sm shadow-sm focus:outline-none focus:ring-1 ${errors.current_password ? 'border-red-400 focus:ring-red-400' : 'border-gray-300 focus:border-indigo-500 focus:ring-indigo-500'}`}
                   {...register('current_password')} />
            <button type="button" tabIndex={-1} onClick={() => setShowCurrent(v => !v)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600">
              {showCurrent ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
            </button>
          </div>
          {errors.current_password && <p role="alert" className="mt-1 text-xs text-red-600">{errors.current_password.message}</p>}
        </div>

        {/* New password */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1" htmlFor="new_password">New password</label>
          <div className="relative">
            <input id="new_password" type={showNew ? 'text' : 'password'}
                   autoComplete="new-password" aria-invalid={!!errors.new_password}
                   className={`block w-full rounded-lg border px-3 py-2 pr-10 text-sm shadow-sm focus:outline-none focus:ring-1 ${errors.new_password ? 'border-red-400 focus:ring-red-400' : 'border-gray-300 focus:border-indigo-500 focus:ring-indigo-500'}`}
                   {...register('new_password')} />
            <button type="button" tabIndex={-1} onClick={() => setShowNew(v => !v)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600">
              {showNew ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
            </button>
          </div>
          {errors.new_password && <p role="alert" className="mt-1 text-xs text-red-600">{errors.new_password.message}</p>}
          <PasswordStrength password={newPwd} />
        </div>

        {/* Confirm new password */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1" htmlFor="new_password2">Confirm new password</label>
          <input id="new_password2" type={showNew ? 'text' : 'password'} autoComplete="new-password"
                 aria-invalid={!!errors.new_password2}
                 className={`block w-full rounded-lg border px-3 py-2 text-sm shadow-sm focus:outline-none focus:ring-1 ${errors.new_password2 ? 'border-red-400 focus:ring-red-400' : 'border-gray-300 focus:border-indigo-500 focus:ring-indigo-500'}`}
                 {...register('new_password2')} />
          {errors.new_password2 && <p role="alert" className="mt-1 text-xs text-red-600">{errors.new_password2.message}</p>}
        </div>

        <button type="submit" disabled={isSubmitting}
                className="inline-flex items-center gap-2 rounded-lg bg-gray-800 px-4 py-2 text-sm font-medium text-white hover:bg-gray-900 disabled:opacity-50 transition-colors">
          {isSubmitting ? 'Updating…' : 'Update password'}
        </button>
      </form>
    </section>
  );
}

// ── 2FA section ───────────────────────────────────────────────────────────────
function TwoFASection({ user, onUpdate }) {
  const [step,        setStep]        = useState('idle');   // idle|setup|backup|disable
  const [qrUrl,       setQrUrl]       = useState('');
  const [secret,      setSecret]      = useState('');
  const [codes,       setCodes]       = useState([]);
  const [otpCode,     setOtpCode]     = useState('');
  const [disablePwd,  setDisablePwd]  = useState('');
  const [error,       setError]       = useState('');
  const [loading,     setLoading]     = useState(false);

  // Auto-clear backup codes from state after timeout
  useEffect(() => {
    if (step !== 'backup') return;
    const t = setTimeout(() => { setCodes([]); setStep('idle'); }, BACKUP_CLEAR_MS);
    return () => clearTimeout(t);
  }, [step]);

  const startSetup = async () => {
    setError(''); setLoading(true);
    try {
      const data = await authApi.twoFaSetup();
      setQrUrl(data.qr_code_url);
      setSecret(data.secret);
      setStep('setup');
    } catch (err) { setError(err?.message ?? 'Failed to start 2FA setup.'); }
    finally { setLoading(false); }
  };

  const verifySetup = async () => {
    setError(''); setLoading(true);
    try {
      const result = await authApi.twoFaVerify({ code: otpCode.trim() });
      onUpdate({ otp_enabled: true });
      setCodes(result.backup_codes ?? []);
      setOtpCode('');
      setStep('backup');
    } catch {
      // OWASP A07: generic error
      setError('Invalid code. Check your authenticator app and try again.');
    } finally { setLoading(false); }
  };

  const disable2FA = async () => {
    setError(''); setLoading(true);
    try {
      await authApi.twoFaDisable({ password: disablePwd });
      onUpdate({ otp_enabled: false });
      setDisablePwd(''); setStep('idle');
    } catch { setError('Incorrect password.'); }
    finally { setLoading(false); }
  };

  const downloadCodes = () => {
    const txt  = `MailFlow 2FA Backup Codes\n\n${codes.join('\n')}`;
    const blob = new Blob([txt], { type: 'text/plain' });
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement('a');
    a.href = url; a.download = 'mailflow-backup-codes.txt';
    a.click(); URL.revokeObjectURL(url);
  };

  return (
    <section className="bg-white rounded-xl border border-gray-200 shadow-sm p-6">
      <div className="flex items-center gap-2 mb-1">
        <h2 className="text-sm font-semibold text-gray-800">Two-Factor Authentication</h2>
        {user?.otp_enabled
          ? <span className="inline-flex items-center gap-1 rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-700"><ShieldCheck className="h-3.5 w-3.5" />Enabled</span>
          : <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-500">Disabled</span>}
      </div>
      <p className="text-sm text-gray-500 mb-4">
        Protect your account with a TOTP authenticator app (e.g. Authy, Google Authenticator).
      </p>

      {error && <div role="alert" className="mb-3 rounded-lg border border-red-200 bg-red-50 px-4 py-2 text-sm text-red-700">{error}</div>}

      {/* ── Idle ── */}
      {step === 'idle' && !user?.otp_enabled && (
        <button onClick={startSetup} disabled={loading}
                className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50 transition-colors">
          <ShieldCheck className="h-4 w-4" />{loading ? 'Loading…' : 'Enable 2FA'}
        </button>
      )}

      {/* ── Setup: scan QR ── */}
      {step === 'setup' && (
        <div className="space-y-4 animate-fade-in">
          <p className="text-sm text-gray-600">Scan this QR code with your authenticator app, then enter the 6-digit code below to confirm.</p>
          {qrUrl && <img src={qrUrl} alt="2FA QR code" className="w-40 h-40 border border-gray-200 rounded-lg p-2" />}
          <p className="text-xs text-gray-400">Can't scan? Enter this secret manually: <code className="font-mono bg-gray-100 px-1 rounded">{secret}</code></p>
          <div className="flex items-center gap-3">
            <input type="text" inputMode="numeric" maxLength={6} placeholder="000000"
                   value={otpCode} onChange={e => setOtpCode(e.target.value.replace(/\D/g,''))}
                   aria-label="6-digit OTP code"
                   className="w-32 rounded-lg border border-gray-300 px-3 py-2 text-center font-mono text-sm tracking-widest shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500" />
            <button onClick={verifySetup} disabled={loading || otpCode.length < 6}
                    className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50 transition-colors">
              {loading ? 'Verifying…' : 'Verify & Enable'}
            </button>
            <button onClick={() => setStep('idle')} className="text-sm text-gray-500 hover:text-gray-700">Cancel</button>
          </div>
        </div>
      )}

      {/* ── Backup codes reveal ── */}
      {step === 'backup' && (
        <div className="space-y-4 animate-fade-in">
          <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
            ⚠ Save these backup codes. Each can be used <strong>once</strong>. This window clears in 3 minutes.
          </div>
          <div className="grid grid-cols-2 gap-2">
            {codes.map((c, i) => (
              <code key={i} className="rounded-lg bg-gray-900 px-3 py-2 text-center font-mono text-xs text-emerald-400">
                {c}
              </code>
            ))}
          </div>
          <div className="flex gap-3">
            <button onClick={downloadCodes}
                    className="inline-flex items-center gap-2 rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors">
              <Download className="h-4 w-4" />Download
            </button>
            <button onClick={() => { setCodes([]); setStep('idle'); }}
                    className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 transition-colors">
              I've saved them →
            </button>
          </div>
        </div>
      )}

      {/* ── Disable 2FA ── */}
      {step === 'idle' && user?.otp_enabled && (
        <div className="space-y-3 animate-fade-in">
          {step !== 'disable' && (
            <button onClick={() => setStep('disable')}
                    className="inline-flex items-center gap-2 rounded-lg border border-red-300 px-4 py-2 text-sm font-medium text-red-600 hover:bg-red-50 transition-colors">
              <ShieldOff className="h-4 w-4" />Disable 2FA
            </button>
          )}
        </div>
      )}
      {step === 'disable' && (
        <div className="space-y-3 animate-fade-in">
          <p className="text-sm text-gray-600">Enter your password to confirm disabling 2FA.</p>
          <div className="flex items-center gap-3">
            <input type="password" placeholder="Your password" autoComplete="current-password"
                   value={disablePwd} onChange={e => setDisablePwd(e.target.value)}
                   className="w-64 rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500" />
            <button onClick={disable2FA} disabled={loading || !disablePwd}
                    className="rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700 disabled:opacity-50 transition-colors">
              {loading ? 'Disabling…' : 'Disable'}
            </button>
            <button onClick={() => { setStep('idle'); setDisablePwd(''); setError(''); }}
                    className="text-sm text-gray-500 hover:text-gray-700">Cancel</button>
          </div>
        </div>
      )}
    </section>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────
export default function AccountPage() {
  const { user, updateUser } = useAuth();

  const handleUpdate = useCallback((partial) => {
    updateUser(partial);
  }, [updateUser]);

  return (
    <div className="max-w-2xl space-y-6">
      <ProfileSection  user={user} onUpdate={handleUpdate} />
      <PasswordSection />
      <TwoFASection    user={user} onUpdate={handleUpdate} />
    </div>
  );
}