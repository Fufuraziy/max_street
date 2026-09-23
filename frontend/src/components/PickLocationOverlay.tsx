import { Check, MapPin, X } from 'lucide-react';

interface PickLocationOverlayProps {
  onCancel: () => void;
  onConfirm: () => void;
}

/** Режим выбора точки новой площадки: карта двигается под фиксированным пином в центре экрана. */
export default function PickLocationOverlay({ onCancel, onConfirm }: PickLocationOverlayProps) {
  return (
    <>
      <div className="pointer-events-none absolute inset-0 z-[1100]" aria-hidden>
        <MapPin
          className="absolute left-1/2 top-1/2 h-12 w-12 -translate-x-1/2 -translate-y-[92%] fill-accent text-white drop-shadow-lg"
          strokeWidth={1.5}
        />
        <span className="absolute left-1/2 top-1/2 h-2.5 w-2.5 -translate-x-1/2 -translate-y-1/2 rounded-full bg-black/40" />
      </div>
      <div className="pb-safe absolute inset-x-0 bottom-0 z-[1150] px-3 md:bottom-4 md:left-1/2 md:right-auto md:w-[420px] md:-translate-x-1/2">
        <div className="glass rounded-3xl p-4 shadow-sheet">
          <p className="font-semibold">Где находится площадка?</p>
          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">Двигайте карту, пока пин не окажется на площадке</p>
          <div className="mt-3 flex gap-2">
            <button type="button" className="btn-secondary flex-1 border border-slate-200 dark:border-white/10" onClick={onCancel}>
              <X className="h-5 w-5" />
              Отмена
            </button>
            <button type="button" className="btn-primary flex-[2]" onClick={onConfirm}>
              <Check className="h-5 w-5" />
              Площадка здесь
            </button>
          </div>
        </div>
      </div>
    </>
  );
}
