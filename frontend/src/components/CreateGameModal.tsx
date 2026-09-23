import { useEffect, useMemo, useRef, useState } from 'react';
import { Minus, Plus, ShieldCheck, Users } from 'lucide-react';
import { api, errorMessage } from '../api/client';
import { SPORTS } from '../lib/constants';
import { dateKey, formatLabel, formatRub, formatTime, formatTimeRange, plural, shortDayLabel } from '../lib/format';
import { hapticImpact } from '../lib/max';
import type { Court, GameWithCourt, Identity, Slot, SportType } from '../types';
import { Modal, Spinner } from './ui';

interface CreateGameModalProps {
  court: Court;
  identity: Identity;
  onClose: () => void;
  onCreated: (game: GameWithCourt) => void;
}

const QUICK_TIMES = ['17:00', '18:00', '19:00', '20:00', '21:00'];
const MIN_PLAYERS = 2;
const MAX_PLAYERS = 30;
const FREE_DAYS = 7;
const RENT_DAYS = 5;

function buildDate(dayOffset: number, time: string): Date {
  const [hours, minutes] = time.split(':').map(Number);
  const date = new Date();
  date.setDate(date.getDate() + dayOffset);
  date.setHours(hours || 0, minutes || 0, 0, 0);
  return date;
}

/** Ближайший удобный слот: следующий полный час + 1; поздним вечером — завтра в 19:00. */
function defaultSlot(): { dayOffset: number; time: string } {
  const hour = new Date().getHours() + 2;
  if (hour > 22) return { dayOffset: 1, time: '19:00' };
  return { dayOffset: 0, time: `${String(Math.max(hour, 8)).padStart(2, '0')}:00` };
}

function DayPicker({ count, value, onChange }: { count: number; value: number; onChange: (offset: number) => void }) {
  const days = useMemo(() => Array.from({ length: count }, (_, offset) => buildDate(offset, '12:00')), [count]);
  return (
    <div className="no-scrollbar -mx-5 flex gap-2 overflow-x-auto px-5 pb-1">
      {days.map((day, offset) => {
        const label = shortDayLabel(day);
        const active = offset === value;
        return (
          <button
            key={offset}
            type="button"
            onClick={() => onChange(offset)}
            className={`flex min-w-[76px] shrink-0 flex-col items-center rounded-2xl px-3 py-2 transition active:scale-95 ${
              active ? 'bg-accent text-white shadow-sm' : 'bg-white text-slate-700 dark:bg-white/5 dark:text-slate-200'
            }`}
          >
            <span className="text-sm font-semibold capitalize">{label.top}</span>
            <span className={`text-xs ${active ? 'text-white/80' : 'text-slate-400'}`}>{label.bottom}</span>
          </button>
        );
      })}
    </div>
  );
}

function SlotGrid({
  slots,
  error,
  value,
  onChange,
}: {
  slots: Slot[] | null;
  error: string | null;
  value: number | null;
  onChange: (slotId: number) => void;
}) {
  if (error) return <p className="rounded-xl bg-rose-50 px-3 py-2 text-sm text-rose-700 dark:bg-rose-400/10 dark:text-rose-300">{error}</p>;
  if (slots === null) {
    return (
      <div className="flex items-center gap-2 py-3 text-sm text-slate-500">
        <Spinner className="h-4 w-4" /> Загружаем расписание арендодателя…
      </div>
    );
  }
  if (slots.length === 0) {
    return <p className="card text-sm text-slate-500 dark:text-slate-400">На этот день слотов нет, выберите другую дату.</p>;
  }
  return (
    <div className="grid grid-cols-2 gap-2">
      {slots.map((slot) => {
        const active = slot.id === value;
        const busyLabel = slot.status === 'reserved' ? 'Идёт сбор' : 'Занято';
        return (
          <button
            key={slot.id}
            type="button"
            disabled={!slot.is_available}
            aria-pressed={active}
            onClick={() => onChange(slot.id)}
            className={`flex flex-col items-start rounded-2xl border-2 px-3 py-2.5 text-left transition active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-45 ${
              active
                ? 'border-emerald-500 bg-emerald-50 dark:bg-emerald-400/10'
                : 'border-transparent bg-white dark:bg-white/5'
            }`}
          >
            <span className="font-semibold tabular-nums">{formatTimeRange(slot.start_time, slot.end_time)}</span>
            <span className={`text-sm ${slot.is_available ? 'text-emerald-700 dark:text-emerald-300' : 'text-slate-400 line-through'}`}>
              {slot.is_available ? formatRub(slot.price) : `${busyLabel} · ${formatRub(slot.price)}`}
            </span>
          </button>
        );
      })}
    </div>
  );
}

export default function CreateGameModal({ court, identity, onClose, onCreated }: CreateGameModalProps) {
  const rental = court.is_commercial;
  const initialSlot = useMemo(defaultSlot, []);
  const [sport, setSport] = useState<SportType>(court.sport_types[0]);
  const [players, setPlayers] = useState(SPORTS[court.sport_types[0]].defaultPlayers);
  const [dayOffset, setDayOffset] = useState(rental ? 0 : initialSlot.dayOffset);
  const [time, setTime] = useState(initialSlot.time);
  const [comment, setComment] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [slots, setSlots] = useState<Slot[] | null>(null);
  const [slotsError, setSlotsError] = useState<string | null>(null);
  const [slotId, setSlotId] = useState<number | null>(null);
  const autoAdvanced = useRef(false);

  // Расписание аренды на выбранный день от провайдера арендодателя.
  useEffect(() => {
    if (!rental) return undefined;
    let cancelled = false;
    setSlots(null);
    setSlotsError(null);
    setSlotId(null);
    api
      .getSlots(court.id, dateKey(buildDate(dayOffset, '12:00')))
      .then((data) => {
        if (cancelled) return;
        const firstFree = data.find((slot) => slot.is_available);
        // Вечером свободных слотов на сегодня обычно нет — один раз сами переключаемся на завтра.
        if (!firstFree && dayOffset === 0 && !autoAdvanced.current) {
          autoAdvanced.current = true;
          setDayOffset(1);
          return;
        }
        autoAdvanced.current = true;
        setSlots(data);
        setSlotId(firstFree?.id ?? null);
      })
      .catch((err) => {
        if (!cancelled) setSlotsError(errorMessage(err));
      });
    return () => {
      cancelled = true;
    };
  }, [rental, court.id, dayOffset]);

  const meta = SPORTS[sport];
  const selectedSlot = slots?.find((slot) => slot.id === slotId) ?? null;
  const start = rental && selectedSlot ? new Date(selectedSlot.start_time) : buildDate(dayOffset, time || '00:00');
  const isPast = !rental && start.getTime() < Date.now() + 5 * 60_000;
  const share = selectedSlot ? Math.round((selectedSlot.price / players) * 100) / 100 : 0;
  const missing = players - 1;
  const canSubmit = rental ? selectedSlot !== null : Boolean(time) && !isPast;

  const changeSport = (value: SportType) => {
    hapticImpact('light');
    setSport(value);
    setPlayers(SPORTS[value].defaultPlayers);
  };

  const submit = async () => {
    if (!canSubmit) return;
    setSubmitting(true);
    setError(null);
    try {
      const game = await api.createGame({
        court_id: court.id,
        sport_type: sport,
        ...(rental && selectedSlot ? { slot_id: selectedSlot.id } : { start_time: start.toISOString() }),
        required_players: players,
        comment: comment.trim(),
        creator_max_id: identity.maxUserId,
        creator_name: identity.name || 'Игрок',
        creator_username: identity.username,
      });
      onCreated(game);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Modal
      title={rental ? 'Аренда корта и сбор' : 'Новый сбор'}
      subtitle={court.title}
      onClose={onClose}
      footer={
        <div>
          {error && <p className="mb-2 rounded-xl bg-rose-50 px-3 py-2 text-sm text-rose-700 dark:bg-rose-400/10 dark:text-rose-300">{error}</p>}
          <button
            type="button"
            className={`btn-primary w-full ${rental ? 'bg-emerald-600 hover:bg-emerald-700' : ''}`}
            disabled={submitting || !canSubmit}
            onClick={submit}
          >
            {submitting ? <Spinner /> : rental ? <ShieldCheck className="h-5 w-5" /> : <Users className="h-5 w-5" />}
            {rental
              ? `Создать сбор с эскроу${selectedSlot ? ` · ${formatRub(selectedSlot.price)}` : ''}`
              : `Создать сбор · ${meta.emoji} ${formatLabel(sport, players)}`}
          </button>
        </div>
      }
    >
      {court.sport_types.length > 1 && (
        <section className="mb-5">
          <span className="field-label">Вид спорта</span>
          <div className="flex flex-wrap gap-2">
            {court.sport_types.map((value) => {
              const active = value === sport;
              return (
                <button
                  key={value}
                  type="button"
                  onClick={() => changeSport(value)}
                  className={active ? 'chip text-white shadow-sm' : 'chip-idle'}
                  style={active ? { background: SPORTS[value].color } : undefined}
                >
                  {SPORTS[value].emoji} {SPORTS[value].label}
                </button>
              );
            })}
          </div>
        </section>
      )}

      <section className="mb-5">
        <span className="field-label">День</span>
        <DayPicker count={rental ? RENT_DAYS : FREE_DAYS} value={dayOffset} onChange={setDayOffset} />
      </section>

      {rental ? (
        <section className="mb-5">
          <span className="field-label">Свободные слоты арендодателя</span>
          <SlotGrid slots={slots} error={slotsError} value={slotId} onChange={setSlotId} />
        </section>
      ) : (
        <section className="mb-5">
          <label className="field-label" htmlFor="game-time">
            Время начала
          </label>
          <div className="flex flex-wrap gap-2">
            {QUICK_TIMES.map((value) => {
              const disabled = buildDate(dayOffset, value).getTime() < Date.now() + 5 * 60_000;
              return (
                <button
                  key={value}
                  type="button"
                  disabled={disabled}
                  onClick={() => setTime(value)}
                  className={`${time === value ? 'chip bg-accent text-white' : 'chip-idle'} disabled:opacity-40`}
                >
                  {value}
                </button>
              );
            })}
            <input
              id="game-time"
              type="time"
              step={900}
              value={time}
              onChange={(event) => setTime(event.target.value)}
              className="input w-auto min-w-[120px] py-2"
            />
          </div>
          {isPast && time && <p className="mt-2 text-sm text-rose-600 dark:text-rose-400">Это время уже прошло</p>}
        </section>
      )}

      <section className="mb-5">
        <span className="field-label">Формат и количество игроков</span>
        <div className="flex flex-wrap gap-2">
          {meta.formats.map((format) => (
            <button
              key={format.label}
              type="button"
              onClick={() => setPlayers(format.players)}
              className={players === format.players ? 'chip text-white shadow-sm' : 'chip-idle'}
              style={players === format.players ? { background: meta.color } : undefined}
            >
              {format.label}
              <span className={players === format.players ? 'text-white/80' : 'text-slate-400'}>· {format.players}</span>
            </button>
          ))}
        </div>
        <div className="mt-3 flex items-center justify-between rounded-2xl bg-white px-4 py-2 dark:bg-white/5">
          <span className="text-sm text-slate-600 dark:text-slate-300">Всего игроков, включая вас</span>
          <div className="flex items-center gap-3">
            <button
              type="button"
              aria-label="Меньше"
              className="flex h-9 w-9 items-center justify-center rounded-full bg-slate-100 active:scale-95 disabled:opacity-40 dark:bg-white/10"
              disabled={players <= MIN_PLAYERS}
              onClick={() => setPlayers((value) => Math.max(MIN_PLAYERS, value - 1))}
            >
              <Minus className="h-4 w-4" />
            </button>
            <span className="w-6 text-center text-lg font-bold tabular-nums">{players}</span>
            <button
              type="button"
              aria-label="Больше"
              className="flex h-9 w-9 items-center justify-center rounded-full bg-slate-100 active:scale-95 disabled:opacity-40 dark:bg-white/10"
              disabled={players >= MAX_PLAYERS}
              onClick={() => setPlayers((value) => Math.min(MAX_PLAYERS, value + 1))}
            >
              <Plus className="h-4 w-4" />
            </button>
          </div>
        </div>
      </section>

      <section className="mb-2">
        <label className="field-label" htmlFor="game-comment">
          Комментарий <span className="font-normal text-slate-400">(необязательно)</span>
        </label>
        <textarea
          id="game-comment"
          rows={3}
          maxLength={500}
          value={comment}
          onChange={(event) => setComment(event.target.value)}
          placeholder={rental ? 'Например: пары 2×2, уровень средний, мячи есть' : 'Например: играем до 21, мяч есть, уровень любительский'}
          className="input resize-none"
        />
      </section>

      {rental ? (
        <div className="flex gap-3 rounded-2xl bg-emerald-50 px-4 py-3 text-sm text-emerald-900 dark:bg-emerald-400/10 dark:text-emerald-200">
          <ShieldCheck className="mt-0.5 h-5 w-5 shrink-0" />
          <p>
            {selectedSlot ? (
              <>
                Корт {formatTime(start)}: <b>{formatRub(selectedSlot.price)}</b>, доля каждого{' '}
                <b>{formatRub(share)}</b> ({players} {plural(players, ['игрок', 'игрока', 'игроков'])}).{' '}
              </>
            ) : (
              'Выберите свободный слот. '
            )}
            Слот будет зарезервирован, а для сбора создастся эскроу-счёт MAX Escrow. Деньги не уходят организатору: корт
            выкупается автоматически, когда соберётся 100%, иначе все получат возврат.
          </p>
        </div>
      ) : (
        <p className="rounded-2xl bg-accent-soft px-4 py-3 text-sm text-slate-700 dark:bg-accent/15 dark:text-slate-200">
          {meta.emoji} {meta.label} · {shortDayLabel(start).top.toLowerCase()} в {formatTime(start)}. Вы уже в составе, нужно
          ещё {missing} {plural(missing, ['игрок', 'игрока', 'игроков'])}. Когда все соберутся, бот MAX пришлёт уведомление.
        </p>
      )}
    </Modal>
  );
}
