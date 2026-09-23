import { Flame, ShieldCheck } from 'lucide-react';
import { SPORT_ORDER, SPORTS } from '../lib/constants';
import { hapticImpact } from '../lib/max';
import type { SportType } from '../types';

interface FiltersBarProps {
  sport: SportType | null;
  onSportChange: (sport: SportType | null) => void;
  onlyWithGames: boolean;
  onOnlyWithGamesChange: (value: boolean) => void;
  onlyRental: boolean;
  onOnlyRentalChange: (value: boolean) => void;
  className?: string;
}

export default function FiltersBar({
  sport,
  onSportChange,
  onlyWithGames,
  onOnlyWithGamesChange,
  onlyRental,
  onOnlyRentalChange,
  className = '',
}: FiltersBarProps) {
  const pick = (value: SportType | null) => {
    hapticImpact('light');
    onSportChange(value);
  };

  return (
    <div className={`no-scrollbar flex gap-2 overflow-x-auto px-3 pb-2 pt-1 ${className}`} role="toolbar" aria-label="Фильтры">
      <button
        type="button"
        onClick={() => pick(null)}
        aria-pressed={sport === null}
        className={sport === null ? 'chip bg-slate-900 text-white shadow-sm dark:bg-white dark:text-slate-900' : 'chip-idle'}
      >
        Все
      </button>
      <button
        type="button"
        onClick={() => {
          hapticImpact('light');
          onOnlyRentalChange(!onlyRental);
        }}
        aria-pressed={onlyRental}
        className={onlyRental ? 'chip bg-emerald-600 text-white shadow-sm' : 'chip-idle'}
      >
        <ShieldCheck className="h-4 w-4" />
        Аренда
      </button>
      {SPORT_ORDER.map((key) => {
        const meta = SPORTS[key];
        const active = sport === key;
        return (
          <button
            key={key}
            type="button"
            onClick={() => pick(active ? null : key)}
            aria-pressed={active}
            className={active ? 'chip text-white shadow-sm' : 'chip-idle'}
            style={active ? { background: meta.color } : undefined}
          >
            <span aria-hidden>{meta.emoji}</span>
            {meta.short}
          </button>
        );
      })}
      <button
        type="button"
        onClick={() => {
          hapticImpact('light');
          onOnlyWithGamesChange(!onlyWithGames);
        }}
        aria-pressed={onlyWithGames}
        className={onlyWithGames ? 'chip bg-rose-500 text-white shadow-sm' : 'chip-idle'}
      >
        <Flame className="h-4 w-4" />
        Сборы сегодня
      </button>
    </div>
  );
}
