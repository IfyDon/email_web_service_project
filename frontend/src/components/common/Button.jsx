/*
import { clsx } from 'clsx';
import Spinner from './Spinner';

const V = {
  primary:   'inline-flex items-center justify-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors',
  secondary: 'inline-flex items-center justify-center gap-2 rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors',
  danger:    'inline-flex items-center justify-center gap-2 rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors',
  ghost:     'inline-flex items-center gap-2 text-sm font-medium text-gray-600 hover:text-gray-900 disabled:opacity-50',
};

export default function Button({ children, variant='primary', loading=false, disabled, className, ...props }) {
  return (
    <button disabled={disabled || loading} className={clsx(V[variant], className)} {...props}>
      {loading && <Spinner size="sm" />}
      {children}
    </button>
  );
}
*/