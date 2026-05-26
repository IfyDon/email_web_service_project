/*
import { forwardRef } from 'react';
import { clsx } from 'clsx';

const Input = forwardRef(function Input(
  { label, error, hint, className, ...props }, ref
) {
  return (
    <div>
      {label && <label className="label">{label}</label>}
      <input
        ref={ref}
        className={clsx('input', error && 'border-red-500 focus:ring-red-400', className)}
        {...props}
      />
      {error && <p className="mt-1 text-xs text-red-600">{error}</p>}
      {hint  && <p className="mt-1 text-xs text-gray-400">{hint}</p>}
    </div>
  );
});
export default Input;
*/
