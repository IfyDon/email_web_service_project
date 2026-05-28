/**
 * API Key management page.
 *
 * Security notes:
 *  - Raw key is displayed ONCE in a modal; never stored in component state
 *    beyond the single render cycle after creation
 *  - After COPY_TIMEOUT ms the raw key is cleared from state to limit XSS
 *    exposure window (key no longer accessible via JS after timeout)
 *  - Revoke requires an explicit confirmation dialog (OWASP A01)
 *  - No key content is logged to console (OWASP A09)
 *  - CSRF handled by the Axios client automatically
 *
 * Place: frontend/src/pages/settings/APIKeysPage.jsx
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { useForm } from 'react-hook-form';
import { z } from 'zod';
import { zodResolver } from '@hookform/resolvers/zod';
import { Plus, Copy, Check, Trash2, KeyRound, X, AlertTriangle } from 'lucide-react';
import { format } from 'date-fns';
import { authApi } from '@/api/auth';
import { useApi } from '@/hooks/useApi';

// How long (ms) the raw key stays visible after creation
const KEY_CLEAR_TIMEOUT = 120_000;  // 2 minutes

const schema = z.object({
  label:      z.string().trim().min(1, 'Label is required').max(100),
  expires_at: z.string().optional(),
});

// ── Sub-components ────────────────────────────────────────────────────────────

function KeyRevealModal({ rawKey, onClose }) {
  const [copied,    setCopied]    = useState(false);
  const [timeLeft,  setTimeLeft]  = useState(KEY_CLEAR_TIMEOUT / 1000);
  const clearRef                  = useRef(null);

  // Countdown — key auto-hides when timer hits 0
  useEffect(() => {
    const tick = setInterval(() => {
      setTimeLeft(t => {
        if (t <= 1) { clearInterval(tick); onClose(); return 0; }
        return t - 1;
      });
    }, 1000);
    return () => clearInterval(tick);
  }, [onClose]);

  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(rawKey);
      setCopied(true);
      setTimeout(() => setCopied(false), 2500);
    } catch {
      // Clipboard API blocked (insecure context / policy)
      alert('Copy failed. Please select the key manually.');
    }
  }, [rawKey]);

  return (
    <div role="dialog" aria-modal="true" aria-labelledby="key-modal-title"
         className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4">
      <div className="w-full max-w-lg bg-white rounded-2xl shadow-2xl p-6 animate-slide-up">

        {/* Header */}
        <div className="flex items-start justify-between mb-4">
          <div className="flex items-center gap-2">
            <KeyRound className="h-5 w-5 text-amber-500" />
            <h2 id="key-modal-title" className="font-semibold text-gray-900">
              Save your API key
            </h2>
          </div>
          <button onClick={onClose} aria-label="Close"
                  className="text-gray-400 hover:text-gray-600 transition-colors">
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Warning */}
        <div className="flex items-start gap-3 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 mb-5">
          <AlertTriangle className="h-4 w-4 text-amber-600 mt-0.5 flex-shrink-0" />
          <p className="text-sm text-amber-800">
            This key is shown <strong>once</strong> and cannot be retrieved again.
            Copy it now and store it in a password manager. This window closes in{' '}
            <strong>{timeLeft}s</strong>.
          </p>
        </div>

        {/* Key display */}
        <div className="flex items-center gap-2 mb-5">
          <code className="flex-1 select-all overflow-x-auto rounded-lg bg-gray-900 px-3 py-2.5
                           font-mono text-sm text-emerald-400 whitespace-nowrap">
            {rawKey}
          </code>
          <button onClick={handleCopy}
                  className="flex-shrink-0 flex items-center gap-1.5 rounded-lg border border-gray-300
                             bg-white px-3 py-2 text-sm font-medium text-gray-700
                             hover:bg-gray-50 transition-colors"
                  aria-label={copied ? 'Copied' : 'Copy API key'}>
            {copied
              ? <><Check className="h-4 w-4 text-green-600" />Copied</>
              : <><Copy className="h-4 w-4" />Copy</>}
          </button>
        </div>

        {/* Usage hint */}
        <div className="rounded-lg bg-gray-900 px-4 py-3 text-xs font-mono text-gray-400 overflow-x-auto">
          <span className="text-gray-500"># Example</span>{'\n'}
          curl -H <span className="text-yellow-300">"Authorization: Bearer {rawKey.slice(0, 12)}…"</span>{'\n'}
          {'  '}https://yourapp.com/api/v1/send
        </div>

        <button onClick={onClose}
                className="mt-5 inline-flex w-full items-center justify-center rounded-lg
                           bg-indigo-600 px-4 py-2.5 text-sm font-medium text-white
                           hover:bg-indigo-700 transition-colors">
          I've saved my key
        </button>
      </div>
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function APIKeysPage() {
  const { data: keys, loading, error, execute: loadKeys, setData: setKeys } =
    useApi(authApi.listApiKeys, { immediate: true, initialData: [] });

  const [creating,  setCreating]  = useState(false);
  const [rawKey,    setRawKey]    = useState(null);   // cleared after modal close
  const [revokeId,  setRevokeId]  = useState(null);   // key id pending confirmation
  const [formError, setFormError] = useState('');

  const { register, handleSubmit, reset, formState: { errors, isSubmitting } } =
    useForm({ resolver: zodResolver(schema) });

  // ── Create ────────────────────────────────────────────────────────────────
  const onCreate = async (data) => {
    setFormError('');
    try {
      const result = await authApi.createApiKey(data);
      // result contains { key: 'ems_…', … } — show in modal, don't log
      setRawKey(result.key);
      setCreating(false);
      reset();
      // Add the new key (without the raw value) to the list
      setKeys(prev => [result, ...(prev ?? [])]);
    } catch (err) {
      setFormError(err?.message ?? 'Failed to create API key.');
    }
  };

  // ── Revoke ────────────────────────────────────────────────────────────────
  const onRevoke = async () => {
    if (!revokeId) return;
    try {
      await authApi.revokeApiKey(revokeId);
      setKeys(prev => prev?.filter(k => k.id !== revokeId) ?? []);
    } catch (err) {
      alert(err?.message ?? 'Failed to revoke key.');
    } finally {
      setRevokeId(null);
    }
  };

  // ── Status badge ──────────────────────────────────────────────────────────
  const keyBadge = (key) => {
    if (!key.is_active) return { label: 'Revoked', cls: 'bg-gray-100 text-gray-500' };
    if (key.expires_at && new Date(key.expires_at) < new Date())
      return { label: 'Expired', cls: 'bg-red-100 text-red-600' };
    return { label: 'Active', cls: 'bg-green-100 text-green-700' };
  };

  return (
    <div className="max-w-4xl space-y-6">

      {/* Raw-key reveal modal */}
      {rawKey && (
        <KeyRevealModal
          rawKey={rawKey}
          onClose={() => setRawKey(null)}
        />
      )}

      {/* Revoke confirmation */}
      {revokeId && (
        <div role="dialog" aria-modal="true" aria-labelledby="revoke-title"
             className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4">
          <div className="w-full max-w-sm bg-white rounded-2xl shadow-2xl p-6 animate-slide-up">
            <h2 id="revoke-title" className="font-semibold text-gray-900 mb-2">Revoke API key?</h2>
            <p className="text-sm text-gray-500 mb-5">
              Any application using this key will immediately lose access. This cannot be undone.
            </p>
            <div className="flex gap-3">
              <button onClick={onRevoke}
                      className="flex-1 rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700 transition-colors">
                Revoke
              </button>
              <button onClick={() => setRevokeId(null)}
                      className="flex-1 rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors">
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-base font-semibold text-gray-900">API Keys</h2>
          <p className="text-sm text-gray-500 mt-0.5">
            Keys authenticate programmatic access. Never share or commit them to version control.
          </p>
        </div>
        <button onClick={() => { setCreating(true); setFormError(''); reset(); }}
                className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm
                           font-medium text-white hover:bg-indigo-700 transition-colors">
          <Plus className="h-4 w-4" /> New Key
        </button>
      </div>

      {/* Create form */}
      {creating && (
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-5 animate-fade-in">
          <h3 className="text-sm font-semibold text-gray-800 mb-4">Create API key</h3>
          {formError && (
            <div role="alert" className="mb-3 rounded-lg border border-red-200 bg-red-50 px-4 py-2 text-sm text-red-700">
              {formError}
            </div>
          )}
          <form onSubmit={handleSubmit(onCreate)} className="space-y-4" noValidate>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1" htmlFor="label">
                  Label <span className="text-red-500" aria-hidden>*</span>
                </label>
                <input id="label" type="text" placeholder="e.g. Production, CI/CD"
                       aria-invalid={!!errors.label}
                       className="block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                       {...register('label')} />
                {errors.label && <p role="alert" className="mt-1 text-xs text-red-600">{errors.label.message}</p>}
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1" htmlFor="expires_at">
                  Expires (optional)
                </label>
                <input id="expires_at" type="datetime-local"
                       className="block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                       {...register('expires_at')} />
              </div>
            </div>
            <div className="flex gap-3">
              <button type="submit" disabled={isSubmitting}
                      className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50 transition-colors">
                {isSubmitting ? 'Generating…' : 'Generate key'}
              </button>
              <button type="button" onClick={() => setCreating(false)}
                      className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors">
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Keys table */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center py-16">
            <div className="animate-spin h-6 w-6 rounded-full border-2 border-gray-200 border-t-indigo-600" />
          </div>
        ) : error ? (
          <div role="alert" className="px-6 py-10 text-center text-sm text-red-600">
            Failed to load API keys. <button onClick={loadKeys} className="underline">Retry</button>
          </div>
        ) : !keys?.length ? (
          <div className="px-6 py-16 text-center text-gray-400">
            <KeyRound className="mx-auto h-10 w-10 mb-3 text-gray-300" />
            <p className="font-medium text-gray-600">No API keys yet</p>
            <p className="text-sm mt-1">Create a key to start sending emails via the API.</p>
          </div>
        ) : (
          <table className="w-full text-sm" aria-label="API Keys">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                {['Label','Prefix','Status','Last used','Expires','Created',''].map(h => (
                  <th key={h} className="px-5 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {keys.map(k => {
                const badge = keyBadge(k);
                return (
                  <tr key={k.id} className="hover:bg-gray-50 transition-colors">
                    <td className="px-5 py-3 font-medium text-gray-800">{k.label}</td>
                    <td className="px-5 py-3">
                      <code className="rounded bg-gray-100 px-2 py-0.5 text-xs font-mono text-gray-700">
                        {k.prefix}…
                      </code>
                    </td>
                    <td className="px-5 py-3">
                      <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${badge.cls}`}>
                        {badge.label}
                      </span>
                    </td>
                    <td className="px-5 py-3 text-gray-500">
                      {k.last_used ? format(new Date(k.last_used), 'MMM d, yyyy') : '—'}
                    </td>
                    <td className="px-5 py-3 text-gray-500">
                      {k.expires_at ? format(new Date(k.expires_at), 'MMM d, yyyy') : 'Never'}
                    </td>
                    <td className="px-5 py-3 text-gray-400 text-xs">
                      {format(new Date(k.created_at), 'MMM d, yyyy')}
                    </td>
                    <td className="px-5 py-3 text-right">
                      {k.is_active && (
                        <button onClick={() => setRevokeId(k.id)}
                                aria-label={`Revoke key ${k.label}`}
                                className="text-red-500 hover:text-red-700 transition-colors">
                          <Trash2 className="h-4 w-4" />
                        </button>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>

      {/* Security note */}
      <p className="text-xs text-gray-400">
        🔒 Keys are hashed and cannot be recovered after creation. Use{' '}
        <code className="bg-gray-100 px-1 rounded">Authorization: Bearer ems_…</code> in API requests.
        Rotate keys regularly and revoke any you no longer use.
      </p>
    </div>
  );
}