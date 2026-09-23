import { useEffect, type ReactNode } from 'react';
import { CircleCheck, Info, LoaderCircle, TriangleAlert, X } from 'lucide-react';

export function Spinner({ className = 'h-5 w-5' }: { className?: string }) {
  return <LoaderCircle className={`animate-spin ${className}`} aria-hidden />;
}

export function IconButton({
  label,
  onClick,
  children,
  className = '',
}: {
  label: string;
  onClick: () => void;
  children: ReactNode;
  className?: string;
}) {
  return (
    <button
      type="button"
      aria-label={label}
      title={label}
      onClick={onClick}
      className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-black/5 text-slate-600 transition hover:bg-black/10 active:scale-95 dark:bg-white/10 dark:text-slate-300 dark:hover:bg-white/15 ${className}`}
    >
      {children}
    </button>
  );
}

/** Модальное окно: bottom sheet на телефоне и диалог по центру на десктопе. */
export function Modal({
  title,
  subtitle,
  onClose,
  children,
  footer,
}: {
  title: ReactNode;
  subtitle?: ReactNode;
  onClose: () => void;
  children: ReactNode;
  footer?: ReactNode;
}) {
  return (
    <div className="fixed inset-0 z-[1300] flex items-end justify-center md:items-center md:p-6">
      <div className="absolute inset-0 animate-fade-in bg-black/45" onClick={onClose} aria-hidden />
      <div
        role="dialog"
        aria-modal="true"
        className="relative flex max-h-[92dvh] w-full animate-slide-up flex-col rounded-t-3xl bg-[#F2F3F7] shadow-sheet dark:bg-[#15171C] md:max-w-lg md:animate-fade-in md:rounded-3xl"
      >
        <div className="flex justify-center pt-2 md:hidden">
          <span className="h-1.5 w-10 rounded-full bg-slate-300 dark:bg-white/20" />
        </div>
        <div className="flex items-start gap-3 px-5 pb-3 pt-3">
          <div className="min-w-0 flex-1">
            <h2 className="text-lg font-bold leading-tight">{title}</h2>
            {subtitle && <p className="mt-0.5 text-sm text-slate-500 dark:text-slate-400">{subtitle}</p>}
          </div>
          <IconButton label="Закрыть" onClick={onClose}>
            <X className="h-5 w-5" />
          </IconButton>
        </div>
        <div className="scroll-area flex-1 overflow-y-auto px-5 pb-4">{children}</div>
        {footer && <div className="pb-safe border-t border-black/5 px-5 pt-3 dark:border-white/5">{footer}</div>}
      </div>
    </div>
  );
}

export function Toggle({
  checked,
  onChange,
  label,
  description,
}: {
  checked: boolean;
  onChange: (value: boolean) => void;
  label: string;
  description?: string;
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      onClick={() => onChange(!checked)}
      className="flex w-full items-center gap-3 rounded-2xl bg-white px-4 py-3 text-left dark:bg-white/5"
    >
      <span className="min-w-0 flex-1">
        <span className="block font-medium">{label}</span>
        {description && <span className="block text-sm text-slate-500 dark:text-slate-400">{description}</span>}
      </span>
      <span
        className={`relative h-7 w-12 shrink-0 rounded-full transition ${checked ? 'bg-accent' : 'bg-slate-300 dark:bg-white/20'}`}
      >
        <span
          className={`absolute top-0.5 h-6 w-6 rounded-full bg-white shadow transition-all ${checked ? 'left-[22px]' : 'left-0.5'}`}
        />
      </span>
    </button>
  );
}

export interface ToastState {
  id: number;
  message: string;
  kind: 'success' | 'error' | 'info';
}

const TOAST_STYLES: Record<ToastState['kind'], string> = {
  success: 'bg-emerald-600',
  error: 'bg-rose-600',
  info: 'bg-slate-800 dark:bg-slate-700',
};

export function Toast({ toast, onHide }: { toast: ToastState | null; onHide: () => void }) {
  useEffect(() => {
    if (!toast) return undefined;
    const timer = window.setTimeout(onHide, toast.kind === 'error' ? 4500 : 3200);
    return () => window.clearTimeout(timer);
  }, [toast, onHide]);

  if (!toast) return null;
  const Icon = toast.kind === 'success' ? CircleCheck : toast.kind === 'error' ? TriangleAlert : Info;
  return (
    <div
      className="pointer-events-none fixed inset-x-0 z-[1500] flex justify-center px-4"
      style={{ top: 'calc(max(env(safe-area-inset-top), 12px) + 116px)' }}
    >
      <div
        key={toast.id}
        role="status"
        onClick={onHide}
        className={`pointer-events-auto flex max-w-md animate-pop-in items-center gap-2.5 rounded-2xl px-4 py-3 text-sm font-medium text-white shadow-float ${TOAST_STYLES[toast.kind]}`}
      >
        <Icon className="h-5 w-5 shrink-0" />
        <span>{toast.message}</span>
      </div>
    </div>
  );
}

export function SectionTitle({ title, count, action }: { title: string; count?: number; action?: ReactNode }) {
  return (
    <div className="mb-1 mt-6 flex items-center justify-between px-1">
      <h3 className="text-[15px] font-bold">
        {title}
        {count !== undefined && count > 0 && <span className="ml-1.5 text-slate-400">{count}</span>}
      </h3>
      {action}
    </div>
  );
}
