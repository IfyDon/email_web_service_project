/*
import { clsx } from 'clsx';
const S = {
  error:   'bg-red-50   border-red-200   text-red-700',
  success: 'bg-green-50 border-green-200 text-green-700',
  warning: 'bg-amber-50 border-amber-200 text-amber-700',
  info:    'bg-blue-50  border-blue-200  text-blue-700',
};
export default function Alert({ type='info', title, children, className }) {
  return (
    <div role={type === 'error' ? 'alert' : 'status'}
         className={clsx('rounded-lg border px-4 py-3 text-sm animate-fade-in', S[type], className)}>
      {title && <p className="font-semibold mb-0.5">{title}</p>}
      <div>{children}</div>
    </div>
  );
}
*/