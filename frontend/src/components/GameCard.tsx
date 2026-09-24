import { CircleCheck, Clock, Crown, LogOut, MapPin, ShieldCheck, UserPlus, Zap } from 'lucide-react';
import { GAME_STATUS_STYLES, PAYMENT_STATUS_STYLES, SPORTS } from '../lib/constants';
import {
  amountDue,
  avatarColor,
  formatGameWhen,
  formatLabel,
  formatRub,
  formatTime,
  dayLabel,
  hexToRgba,
  initials,
  percentOf,
  plural,
} from '../lib/format';
import type { Game, GameCourt, Identity, Participant } from '../types';
import { Spinner } from './ui';

interface GameCardProps {
  game: Game;
  identity: Identity;
  busy: boolean;
  onJoin: () => void;
  onLeave: () => void;
  onPay: () => void;
  onQuickSimulatePay?: () => void;
  court?: GameCourt;
  onOpenCourt?: () => void;
}

function Avatar({ participant }: { participant: Participant }) {
  return (
    <span
      title={participant.user_name}
      className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full border-2 border-white text-[11px] font-bold text-white dark:border-[#1C1E24]"
      style={{ background: avatarColor(participant.user_max_id) }}
    >
      {initials(participant.user_name)}
    </span>
  );
}

/** Виджет безопасного эскроу-счёта платного лобби. */
function EscrowPanel({ game }: { game: Game }) {
  const percent = percentOf(game.collected_amount, game.total_cost);
  const booked = game.payment_status === 'paid_to_court';
  const deadline = game.payment_deadline ? new Date(game.payment_deadline) : null;
  return (
    <div className="mt-3 rounded-2xl border border-emerald-200 bg-emerald-50/70 p-3 dark:border-emerald-400/20 dark:bg-emerald-400/5">
      <div className="flex items-start justify-between gap-2">
        <span className="flex min-w-0 items-center gap-1.5 text-sm font-semibold text-emerald-800 dark:text-emerald-300">
          <ShieldCheck className="h-4 w-4 shrink-0" />
          🛡️ Безопасный сбор MAX Escrow
        </span>
        <span className="shrink-0 whitespace-nowrap rounded-md bg-white/80 px-1.5 py-0.5 font-mono text-[11px] text-emerald-700 dark:bg-white/10 dark:text-emerald-300">
          #{game.escrow_account_id}
        </span>
      </div>
      <p className="mt-2 text-sm text-slate-700 dark:text-slate-200">
        Собрано: <b>{formatRub(game.collected_amount)}</b> из {formatRub(game.total_cost)} ({percent}%)
      </p>
      <div className="mt-1.5 h-2.5 overflow-hidden rounded-full bg-white dark:bg-white/10">
        <div className="h-full rounded-full bg-emerald-500 transition-all duration-700" style={{ width: `${percent}%` }} />
      </div>
      {!booked && (
        <p className="mt-2 text-xs leading-relaxed text-slate-600 dark:text-slate-400">
          Доля каждого: <b className="text-slate-800 dark:text-slate-100">{formatRub(game.share_amount)}</b>. Деньги заморожены
          на эскроу-счёте и уйдут арендодателю, только когда соберётся 100%.
          {deadline && ` Если не соберём до ${dayLabel(deadline).toLowerCase()} ${formatTime(deadline)}, всем вернётся оплата.`}
        </p>
      )}
    </div>
  );
}

export default function GameCard({
  game,
  identity,
  busy,
  onJoin,
  onLeave,
  onPay,
  onQuickSimulatePay,
  court,
  onOpenCourt,
}: GameCardProps) {
  const meta = SPORTS[game.sport_type] ?? SPORTS.basketball;
  const participants = Array.isArray(game.participants) ? game.participants : [];
  const me = participants.find((p) => p.user_max_id === identity.maxUserId);
  const isMember = Boolean(me);
  const isCreator = game.creator_max_id === identity.maxUserId;
  const isFull = game.current_players >= game.required_players;
  const progress = percentOf(game.current_players, game.required_players);
  const booked = game.status === 'booked';
  const collecting = game.is_paid && game.payment_status === 'pending';
  const due = amountDue(game.total_cost, game.collected_amount, game.share_amount, game.paid_count, game.required_players);
  const statusLabel = game.is_paid && !booked ? game.payment_status_label ?? game.status_label : game.status_label;
  const statusStyle = game.is_paid && !booked ? PAYMENT_STATUS_STYLES[game.payment_status] : GAME_STATUS_STYLES[game.status];
  const shown = participants.slice(0, 6);
  const hidden = participants.length - shown.length;

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
            <span className={`shrink-0 rounded-full px-2.5 py-1 text-xs font-semibold ${statusStyle}`}>{statusLabel}</span>
          </div>
          <p className="mt-0.5 flex items-center gap-1.5 text-sm text-slate-500 dark:text-slate-400">
            <Clock className="h-3.5 w-3.5" />
            {formatGameWhen(game.start_time, game.slot?.end_time)}
            {game.is_paid && <span className="text-slate-400">· аренда {formatRub(game.total_cost)}</span>}
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

      {game.is_paid && <EscrowPanel game={game} />}

      {collecting && game.spots_left === 1 && !booked && (
        <div className="mt-3 rounded-2xl border border-amber-300/60 bg-amber-50/80 p-3 text-xs text-amber-900 dark:border-amber-400/20 dark:bg-amber-400/10 dark:text-amber-200">
          <div className="flex items-center gap-1.5 font-semibold text-amber-800 dark:text-amber-300">
            <Zap className="h-4 w-4 shrink-0 text-amber-500 fill-amber-500" />
            Свободен слот 6/6 · Проверка Safe Split для жюри
          </div>
          <p className="mt-1 leading-relaxed">
            Нажмите кнопку ниже: внесите долю {formatRub(game.share_amount)} — лобби моментально соберет 100% и Safe Split переведет статус в «Забронировано».
          </p>
        </div>
      )}

      {game.is_paid ? (
        <ul className="mt-3 space-y-2">
          {participants.map((participant) => (
            <li key={participant.user_max_id} className="flex items-center justify-between gap-2 text-sm">
              <span className="flex min-w-0 items-center gap-2">
                <Avatar participant={participant} />
                <span className="truncate">
                  {participant.user_name}
                  {participant.user_max_id === game.creator_max_id && (
                    <span className="text-slate-400"> (Организатор)</span>
                  )}
                  {participant.user_max_id === identity.maxUserId && <span className="text-accent"> · вы</span>}
                </span>
              </span>
              {participant.has_paid ? (
                <span className="shrink-0 rounded-full bg-emerald-100 px-2 py-0.5 text-xs font-semibold text-emerald-700 dark:bg-emerald-400/15 dark:text-emerald-300">
                  ✅ Оплачено {formatRub(participant.paid_amount)}
                </span>
              ) : (
                <span className="shrink-0 rounded-full bg-amber-100 px-2 py-0.5 text-xs font-semibold text-amber-800 dark:bg-amber-400/15 dark:text-amber-300">
                  ⏳ Ожидание оплаты {formatRub(game.share_amount)}
                </span>
              )}
            </li>
          ))}
          {collecting && game.spots_left > 0 && (
            <li className="text-xs text-slate-400">
              + {game.spots_left} {plural(game.spots_left, ['свободное место', 'свободных места', 'свободных мест'])} ·{' '}
              {formatRub(game.share_amount)} с игрока
            </li>
          )}
        </ul>
      ) : (
        <div className="mt-3 flex items-center gap-2">
          <div className="flex -space-x-2">
            {shown.map((participant) => (
              <Avatar key={participant.user_max_id} participant={participant} />
            ))}
            {hidden > 0 && (
              <span className="flex h-8 w-8 items-center justify-center rounded-full border-2 border-white bg-slate-200 text-[11px] font-bold text-slate-600 dark:border-[#1C1E24] dark:bg-white/15 dark:text-slate-200">
                +{hidden}
              </span>
            )}
          </div>
          <p className="min-w-0 flex-1 truncate text-sm text-slate-500 dark:text-slate-400">
            {participants.map((p) => p.user_name).join(', ')}
          </p>
        </div>
      )}

      {game.comment && (
        <p className="mt-3 rounded-xl bg-slate-50 px-3 py-2 text-sm text-slate-600 dark:bg-white/5 dark:text-slate-300">
          💬 {game.comment}
        </p>
      )}

      <div className="mt-3">
        {booked ? (
          <div className="animate-pop-in rounded-2xl bg-emerald-600 px-4 py-3 text-white shadow-sm">
            <p className="font-semibold">🎉 Корт успешно забронирован!</p>
            <p className="mt-0.5 text-sm text-white/90">
              Номер брони: <b className="font-mono">#{game.booking_reference}</b>
            </p>
          </div>
        ) : isMember ? (
          <div className="flex flex-wrap gap-2">
            {collecting && me && !me.has_paid ? (
              <button
                type="button"
                className="btn-primary flex-1 bg-emerald-600 hover:bg-emerald-700"
                disabled={busy}
                onClick={onQuickSimulatePay || onPay}
              >
                {busy ? <Spinner /> : <Zap className="h-5 w-5 text-amber-300 fill-amber-300" />}
                Сымитировать оплату доли ({formatRub(due)})
              </button>
            ) : (
              <div className="flex min-h-[48px] flex-1 items-center gap-2 rounded-2xl bg-emerald-50 px-3 text-sm font-semibold text-emerald-700 dark:bg-emerald-400/10 dark:text-emerald-300">
                {isCreator ? <Crown className="h-5 w-5" /> : <CircleCheck className="h-5 w-5" />}
                {game.is_paid ? 'Ваша доля внесена' : isCreator ? 'Вы организатор' : 'Вы в составе'}
              </div>
            )}
            <button
              type="button"
              className="btn-secondary border border-slate-200 dark:border-white/10"
              disabled={busy}
              onClick={onLeave}
              title={me?.has_paid ? 'Взнос вернётся с эскроу-счёта' : undefined}
            >
              {busy ? <Spinner className="h-4 w-4" /> : <LogOut className="h-4 w-4" />}
              Выйти
            </button>
          </div>
        ) : isFull ? (
          <button type="button" className="btn-secondary w-full" disabled>
            Мест нет
          </button>
        ) : collecting && game.spots_left === 1 && onQuickSimulatePay ? (
          <div className="flex flex-col gap-2">
            <button
              type="button"
              className="btn-primary w-full bg-emerald-600 hover:bg-emerald-700 shadow-md font-semibold text-[15px]"
              disabled={busy}
              onClick={onQuickSimulatePay}
            >
              {busy ? <Spinner /> : <Zap className="h-5 w-5 text-amber-300 fill-amber-300" />}
              Сымитировать оплату доли (Слот 6/6 · {formatRub(game.share_amount)})
            </button>
            <button
              type="button"
              className="btn-secondary w-full text-xs text-slate-500 hover:text-slate-800 dark:text-slate-400 py-1.5"
              disabled={busy}
              onClick={onJoin}
            >
              Присоединиться через окно оплаты (+1)
            </button>
          </div>
        ) : (
          <button type="button" className="btn-primary w-full" disabled={busy} onClick={onJoin}>
            {busy ? <Spinner /> : <UserPlus className="h-5 w-5" />}
            Присоединиться (+1){game.is_paid && ` · ${formatRub(game.share_amount)}`}
          </button>
        )}
      </div>
    </article>
  );
}
