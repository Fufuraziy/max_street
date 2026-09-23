import { CircleCheck, Clock, Crown, LogOut, MapPin, UserPlus } from 'lucide-react';
import { GAME_STATUS_STYLES, SPORTS } from '../lib/constants';
import { avatarColor, formatGameDate, formatLabel, hexToRgba, initials, plural } from '../lib/format';
import type { Game, GameCourt, Identity } from '../types';
import { Spinner } from './ui';

interface GameCardProps {
  game: Game;
  identity: Identity;
  busy: boolean;
  onJoin: () => void;
  onLeave: () => void;
  court?: GameCourt;
  onOpenCourt?: () => void;
}

export default function GameCard({ game, identity, busy, onJoin, onLeave, court, onOpenCourt }: GameCardProps) {
  const meta = SPORTS[game.sport_type] ?? SPORTS.basketball;
  const isMember = game.participants.some((p) => p.user_max_id === identity.maxUserId);
  const isCreator = game.creator_max_id === identity.maxUserId;
  const isFull = game.current_players >= game.required_players;
  const progress = Math.min(100, Math.round((game.current_players / game.required_players) * 100));
  const shown = game.participants.slice(0, 6);
  const hidden = game.participants.length - shown.length;

  return (
    <article className="card mt-2">
      <div className="flex items-start gap-3">
        <div
          className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl text-xl"
          style={{ background: hexToRgba(meta.color, 0.15) }}
          aria-hidden
        >
          {meta.emoji}
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-start justify-between gap-2">
            <h4 className="truncate font-semibold">
              {meta.label} · {formatLabel(game.sport_type, game.required_players)}
            </h4>
            <span className={`shrink-0 rounded-full px-2.5 py-1 text-xs font-semibold ${GAME_STATUS_STYLES[game.status]}`}>
              {game.status_label}
            </span>
          </div>
          <p className="mt-0.5 flex items-center gap-1.5 text-sm text-slate-500 dark:text-slate-400">
            <Clock className="h-3.5 w-3.5" />
            {formatGameDate(game.start_time)}
          </p>
          {court && (
            <button
              type="button"
              onClick={onOpenCourt}
              className="mt-0.5 flex max-w-full items-center gap-1.5 text-left text-sm font-medium text-accent"
            >
              <MapPin className="h-3.5 w-3.5 shrink-0" />
              <span className="truncate">{court.title}</span>
            </button>
          )}
        </div>
      </div>

      <div className="mt-3">
        <div className="flex items-center justify-between text-sm">
          <span className="font-semibold">
            {game.current_players}/{game.required_players} {plural(game.required_players, ['игрок', 'игрока', 'игроков'])}
          </span>
          <span className="text-slate-500 dark:text-slate-400">
            {isFull ? 'Команда в сборе' : `Свободно ${game.spots_left} ${plural(game.spots_left, ['место', 'места', 'мест'])}`}
          </span>
        </div>
        <div className="mt-1.5 h-2 overflow-hidden rounded-full bg-slate-100 dark:bg-white/10">
          <div
            className="h-full rounded-full transition-all duration-500"
            style={{ width: `${progress}%`, background: isFull ? '#10B981' : meta.color }}
          />
        </div>
      </div>

      <div className="mt-3 flex items-center gap-2">
        <div className="flex -space-x-2">
          {shown.map((participant) => (
            <span
              key={participant.user_max_id}
              title={participant.user_name}
              className="flex h-8 w-8 items-center justify-center rounded-full border-2 border-white text-[11px] font-bold text-white dark:border-[#1C1E24]"
              style={{ background: avatarColor(participant.user_max_id) }}
            >
              {initials(participant.user_name)}
            </span>
          ))}
          {hidden > 0 && (
            <span className="flex h-8 w-8 items-center justify-center rounded-full border-2 border-white bg-slate-200 text-[11px] font-bold text-slate-600 dark:border-[#1C1E24] dark:bg-white/15 dark:text-slate-200">
              +{hidden}
            </span>
          )}
        </div>
        <p className="min-w-0 flex-1 truncate text-sm text-slate-500 dark:text-slate-400">
          {game.participants.map((p) => p.user_name).join(', ')}
        </p>
      </div>

      {game.comment && (
        <p className="mt-3 rounded-xl bg-slate-50 px-3 py-2 text-sm text-slate-600 dark:bg-white/5 dark:text-slate-300">
          💬 {game.comment}
        </p>
      )}

      <div className="mt-3">
        {isMember ? (
          <div className="flex gap-2">
            <div className="flex min-h-[48px] flex-1 items-center gap-2 rounded-2xl bg-emerald-50 px-3 text-sm font-semibold text-emerald-700 dark:bg-emerald-400/10 dark:text-emerald-300">
              {isCreator ? <Crown className="h-5 w-5" /> : <CircleCheck className="h-5 w-5" />}
              {isCreator ? 'Вы организатор' : 'Вы в составе'}
            </div>
            <button type="button" className="btn-secondary border border-slate-200 dark:border-white/10" disabled={busy} onClick={onLeave}>
              {busy ? <Spinner className="h-4 w-4" /> : <LogOut className="h-4 w-4" />}
              Выйти
            </button>
          </div>
        ) : isFull ? (
          <button type="button" className="btn-secondary w-full" disabled>
            Мест нет
          </button>
        ) : (
          <button type="button" className="btn-primary w-full" disabled={busy} onClick={onJoin}>
            {busy ? <Spinner /> : <UserPlus className="h-5 w-5" />}
            Присоединиться (+1)
          </button>
        )}
      </div>
    </article>
  );
}
