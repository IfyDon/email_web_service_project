/**
 * Password strength meter.
 *
 * Gives real-time feedback on password quality based on:
 *   - Length (≥ 12 characters recommended by NIST SP 800-63B)
 *   - Character variety (upper, lower, digit, symbol)
 *   - Common pattern detection
 *
 * Place: frontend/src/components/auth/PasswordStrength.jsx
 */

import { useMemo } from 'react';
import { clsx } from 'clsx';

// Basic common-password snippet (extend with a full list in production)
const COMMON = new Set(['password', 'password1', '123456', 'qwerty', 'letmein', 'welcome']);

function evaluate(pwd = '') {
  if (!pwd) return { score: 0, label: '', colour: '' };

  let score = 0;
  const checks = {
    length12:   pwd.length >= 12,
    length8:    pwd.length >= 8,
    hasUpper:   /[A-Z]/.test(pwd),
    hasLower:   /[a-z]/.test(pwd),
    hasDigit:   /\d/.test(pwd),
    hasSymbol:  /[^A-Za-z0-9]/.test(pwd),
    notCommon:  !COMMON.has(pwd.toLowerCase()),
    noRepeats:  !/(.)\1{2,}/.test(pwd),   // e.g. 'aaa'
  };

  if (checks.length8)   score += 1;
  if (checks.length12)  score += 1;
  if (checks.hasUpper)  score += 1;
  if (checks.hasLower)  score += 1;
  if (checks.hasDigit)  score += 1;
  if (checks.hasSymbol) score += 1;
  if (checks.notCommon) score += 1;
  if (checks.noRepeats) score += 1;

  // Clamp to 0-4
  const level = score <= 2 ? 0 : score <= 4 ? 1 : score <= 6 ? 2 : score <= 7 ? 3 : 4;

  const LABELS  = ['Very weak', 'Weak', 'Fair', 'Strong', 'Very strong'];
  const COLOURS = ['bg-red-500', 'bg-orange-400', 'bg-amber-400', 'bg-lime-500', 'bg-green-500'];

  return { score: level, label: LABELS[level], colour: COLOURS[level], checks };
}

export default function PasswordStrength({ password }) {
  const { score, label, colour, checks } = useMemo(() => evaluate(password), [password]);

  if (!password) return null;

  return (
    <div className="mt-2 space-y-2" aria-live="polite">
      {/* Bar */}
      <div className="flex gap-1" role="img" aria-label={`Password strength: ${label}`}>
        {[0, 1, 2, 3].map(i => (
          <div
            key={i}
            className={clsx(
              'h-1.5 flex-1 rounded-full transition-all duration-300',
              i <= score - 1 ? colour : 'bg-gray-200',
            )}
          />
        ))}
      </div>

      {/* Label + tips */}
      <div className="flex items-start justify-between">
        <p className={clsx('text-xs font-medium',
          score <= 1 ? 'text-red-600'
          : score <= 2 ? 'text-amber-600'
          : 'text-green-700'
        )}>
          {label}
        </p>
        {score < 3 && (
          <ul className="text-xs text-gray-400 text-right space-y-0.5">
            {!checks?.length12  && <li>Use 12+ characters</li>}
            {!checks?.hasUpper  && <li>Add an uppercase letter</li>}
            {!checks?.hasSymbol && <li>Add a symbol (!@#…)</li>}
          </ul>
        )}
      </div>
    </div>
  );
}