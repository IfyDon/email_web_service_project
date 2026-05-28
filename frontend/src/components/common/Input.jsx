/*
import { forwardRef } from 'react';
import { clsx } from 'clsx';

const Input = forwardRef(function Input({ label, error, hint, className, required, ...props }, ref) {
  const id = props.id || props.name;
  return (
    <div>
      {label && (
        <label htmlFor={id} className="block text-sm font-medium text-gray-700 mb-1">
          {label}{required && <span className="text-red-500 ml-0.5" aria-hidden>*</span>}
        </label>
      )}
      <input
        id={id}
        ref={ref}
        aria-invalid={!!error}
        aria-describedby={error ? `${id}-error` : hint ? `${id}-hint` : undefined}
        className={clsx(
          'block w-full rounded-lg border px-3 py-2 text-sm shadow-sm',
          'focus:outline-none focus:ring-1 placeholder-gray-400',
          error
            ? 'border-red-400 focus:border-red-400 focus:ring-red-400'
            : 'border-gray-300 focus:border-indigo-500 focus:ring-indigo-500',
          'disabled:bg-gray-50 disabled:cursor-not-allowed',
          className,
        )}
        {...props}
      />
      {error && <p id={`${id}-error`} role="alert" className="mt-1 text-xs text-red-600">{error}</p>}
      {hint && !error && <p id={`${id}-hint`} className="mt-1 text-xs text-gray-400">{hint}</p>}
    </div>
  );
});
export default Input;
*/