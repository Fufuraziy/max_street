import { useRef, useState, type ReactNode, type TouchEvent } from 'react';
import {
  CalendarDays,
  CircleCheck,
  Layers,
  Lightbulb,
  LightbulbOff,
  MapPin,
  Plus,
  Route,
  Share2,
  Star,
  Trees,
  Warehouse,
  Wrench,
  X,
} from 'lucide-react';
import { DEFECT_STATUS_STYLES, SPORTS, SURFACES } from '../lib/constants';
import { hexToRgba, timeAgo } from '../lib/format';
import type { Court, CourtDetail, Identity } from '../types';
import GameCard from './GameCard';
import { IconButton, SectionTitle } from './ui';

interface CourtDetailsSheetProps {
  court: Court;
  detail: CourtDetail | null;
  loading: boolean;
  identity: Identity;
  busyGameId: number | null;
  onClose: () => void;
  onCreateGame: () => void;
  onReportDefect: () => void;
  onJoin: (gameId: number) => void;
  onLeave: (gameId: number) => void;
  onRoute: () => void;
  onShare: () => void;
}

function InfoTile({ icon, label, value }: { icon: ReactNode; label: string; value: string }) {
  return (
    <div className="flex items-center gap-3 rounded-2xl bg-white px-3 py-2.5 dark:bg-[#1C1E24]">
      <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-slate-100 text-slate-600 dark:bg-white/10 dark:text-slate-300">
        {icon}
      </span>
      <span className="min-w-0">
        <span className="block text-xs text-slate-500 dark:text-slate-400">{label}</span>
        <span className="block truncate text-sm font-semibold">{value}</span>
      </span>
    </div>
  );
}

function GameSkeleton() {
  return (
    <div className="card mt-2 animate-pulse">
      <div className="flex gap-3">
        <div className="h-11 w-11 rounded-2xl bg-slate-200 dark:bg-white/10" />
        <div className="flex-1 space-y-2">
          <div className="h-4 w-2/3 rounded bg-slate-200 dark:bg-white/10" />
          <div className="h-3 w-1/3 rounded bg-slate-200 dark:bg-white/10" />
        </div>
      </div>
      <div className="mt-4 h-2 rounded bg-slate-200 dark:bg-white/10" />
      <div className="mt-4 h-12 rounded-2xl bg-slate-200 dark:bg-white/10" />
    </div>
  );
}

export default function CourtDetailsSheet({
  court,
  detail,
  loading,
  identity,
  busyGameId,
  onClose,
  onCreateGame,
  onReportDefect,
  onJoin,
  onLeave,
  onRoute,
  onShare,
}: CourtDetailsSheetProps) {
  const [expanded, setExpanded] = useState(false);
  const touchStartY = useRef<number | null>(null);
  const info = detail ?? court;
  const games = detail?.games ?? [];
  const defects = detail?.defects ?? [];
  const openDefects = defects.filter((d) => d.status !== 'resolved');
  const resolvedDefects = defects.filter((d) => d.status === 'resolved');

  const onTouchStart = (event: TouchEvent) => {
    touchStartY.current = event.touches[0]?.clientY ?? null;
  };
  const onTouchEnd = (event: TouchEvent) => {
    if (touchStartY.current === null) return;
    const delta = (event.changedTouches[0]?.clientY ?? touchStartY.current) - touchStartY.current;
    touchStartY.current = null;
    if (delta > 60) {
      if (expanded) setExpanded(false);
      else onClose();
    } else if (delta < -40) {
      setExpanded(true);
    }
  };

  return (
    <section
      aria-label={`Площадка ${info.title}`}
      className={`fixed inset-x-0 bottom-0 z-[1200] flex animate-slide-up flex-col rounded-t-3xl bg-[#F2F3F7] shadow-sheet transition-[max-height] duration-300 dark:bg-[#15171C] md:bottom-4 md:left-4 md:right-auto md:top-[136px] md:max-h-none md:w-[420px] md:rounded-3xl ${
        expanded ? 'max-h-[92dvh]' : 'max-h-[64dvh]'
      }`}
    >
      <div
        className="flex cursor-grab justify-center pb-1 pt-2 md:hidden"
        onClick={() => setExpanded((value) => !value)}
        onTouchStart={onTouchStart}
        onTouchEnd={onTouchEnd}
        role="button"
        aria-label={expanded ? 'Свернуть' : 'Развернуть'}
      >
        <span className="h-1.5 w-10 rounded-full bg-slate-300 dark:bg-white/20" />
      </div>

      <header className="flex items-start gap-3 px-5 pb-3 pt-2 md:pt-5" onTouchStart={onTouchStart} onTouchEnd={onTouchEnd}>
        <div className="min-w-0 flex-1">
          <div className="mb-1.5 flex flex-wrap gap-1.5">
            {info.sport_types.map((sport) => (
              <span
                key={sport}
                className="rounded-full px-2.5 py-1 text-xs font-semibold"
                style={{ background: hexToRgba(SPORTS[sport].color, 0.14), color: SPORTS[sport].color }}
              >
                {SPORTS[sport].emoji} {SPORTS[sport].label}
              </span>
            ))}
          </div>
          <h2 className="text-xl font-bold leading-tight">{info.title}</h2>
          <p className="mt-1 flex items-start gap-1.5 text-sm text-slate-500 dark:text-slate-400">
            <MapPin className="mt-0.5 h-4 w-4 shrink-0" />
            {info.address}
          </p>
        </div>
        <IconButton label="Закрыть" onClick={onClose}>
          <X className="h-5 w-5" />
        </IconButton>
      </header>

      <div className="scroll-area pb-safe flex-1 overflow-y-auto px-4">
        <div className="grid grid-cols-2 gap-2">
          <InfoTile icon={<Layers className="h-5 w-5" />} label="Покрытие" value={SURFACES[info.surface_type] ?? info.surface_type} />
          <InfoTile
            icon={info.has_lighting ? <Lightbulb className="h-5 w-5 text-amber-500" /> : <LightbulbOff className="h-5 w-5" />}
            label="Освещение"
            value={info.has_lighting ? 'Есть' : 'Нет'}
          />
          <InfoTile
            icon={<Star className="h-5 w-5 text-amber-500" />}
            label="Рейтинг"
            value={info.rating > 0 ? info.rating.toFixed(1) : 'Новая'}
          />
          <InfoTile
            icon={info.is_indoor ? <Warehouse className="h-5 w-5" /> : <Trees className="h-5 w-5 text-emerald-600" />}
            label="Тип"
            value={info.is_indoor ? 'Крытая' : 'Открытая'}
          />
        </div>

        {info.description && (
          <p className="mt-3 px-1 text-[15px] leading-relaxed text-slate-700 dark:text-slate-300">{info.description}</p>
        )}

        <div className="mt-4 flex gap-2">
          <button type="button" className="btn-primary flex-1" onClick={onCreateGame}>
            <Plus className="h-5 w-5" />
            Создать сбор
          </button>
          <button type="button" className="btn-secondary w-12 px-0" onClick={onRoute} aria-label="Маршрут" title="Маршрут">
            <Route className="h-5 w-5" />
          </button>
          <button type="button" className="btn-secondary w-12 px-0" onClick={onShare} aria-label="Поделиться" title="Поделиться">
            <Share2 className="h-5 w-5" />
          </button>
        </div>

        <SectionTitle title="Сборы" count={games.length} />
        {loading && !detail ? (
          <GameSkeleton />
        ) : games.length === 0 ? (
          <div className="card mt-2 flex flex-col items-center py-6 text-center">
            <CalendarDays className="h-9 w-9 text-slate-300 dark:text-slate-600" />
            <p className="mt-2 font-semibold">Пока никто не собирается</p>
            <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
              Создайте сбор: бот позовёт игроков и сообщит, когда команда будет в сборе
            </p>
          </div>
        ) : (
          games.map((game) => (
            <GameCard
              key={game.id}
              game={game}
              identity={identity}
              busy={busyGameId === game.id}
              onJoin={() => onJoin(game.id)}
              onLeave={() => onLeave(game.id)}
            />
          ))
        )}

        <SectionTitle title="Состояние площадки" />
        {detail && openDefects.length === 0 && (
          <div className="card mt-2 flex items-center gap-3">
            <CircleCheck className="h-6 w-6 shrink-0 text-emerald-500" />
            <p className="text-sm text-slate-600 dark:text-slate-300">
              Открытых заявок о неисправностях нет
              {resolvedDefects.length > 0 && ` · устранено: ${resolvedDefects.length}`}
            </p>
          </div>
        )}
        {openDefects.map((defect) => (
          <div key={defect.id} className="card mt-2">
            <div className="flex items-start justify-between gap-2">
              <p className="font-semibold">{defect.defect_label}</p>
              <span className={`shrink-0 rounded-full px-2.5 py-1 text-xs font-semibold ${DEFECT_STATUS_STYLES[defect.status]}`}>
                {defect.status_label}
              </span>
            </div>
            {defect.description && <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">{defect.description}</p>}
            <p className="mt-1 text-xs text-slate-400">
              Заявка №{defect.id} · {timeAgo(defect.created_at)}
            </p>
          </div>
        ))}
        <button type="button" className="btn-secondary mb-2 mt-2 w-full" onClick={onReportDefect}>
          <Wrench className="h-5 w-5" />
          Сообщить о поломке
        </button>
      </div>
    </section>
  );
}
