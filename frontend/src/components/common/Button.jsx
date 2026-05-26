/*
import { clsx } from 'clsx';
import Spinner from './Spinner';

const variants = {
  primary:   'btn-primary',
  secondary: 'btn-secondary',
  danger:    'btn-danger',
  ghost:     'text-gray-600 hover:text-gray-900 text-sm font-medium',
};

export default function Button({
  children, variant = 'primary', loading = false,
  disabled, className, ...props
}) {
  return (
    <button
      disabled={disabled || loading}
      className={clsx(variants[variant], className)}
      {...props}
    >
      {loading && <Spinner size="sm" className="mr-1.5" />}
      {children}
    </button>
  );
}
*/
