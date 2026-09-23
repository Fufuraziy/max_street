import { useState } from 'react';
import { CircleCheckBig, Lock, ShieldCheck, Zap } from 'lucide-react';
import { api, errorMessage } from '../api/client';
import { SPORTS } from '../lib/constants';
import { amountDue, formatGameWhen, formatLabel, formatRub, percentOf, playersText } from '../lib/format';
import { hapticImpact } from '../lib/max';
import type { Game, Identity, PayResponse } from '../types';
import { Modal, Spinner } from './ui';

interface PayModalProps {
  game: Game;
  courtTitle: string;
  identity: Identity;
  onClose: () => void;
  onPaid: (result: PayResponse) => void;
}

type Stage = 'form' | 'processing' | 'done';

const MIN_PROCESSING_MS = 900;

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-start justify-between gap-3 py-2 text-sm">
      <span className="text-slate-500 dark:text-slate-400">{label}</span>
      <span className="text-right font-medium">{value}</span>
    </div>
  );
}

/** Безопасная mock-оплата доли на эскроу-счёт (тестовый СБП, деньги не списываются). */
export default function PayModal({ game, courtTitle, identity, onClose, onPaid }: PayModalProps) {
  const [stage, setStage] = useState<Stage>('form');
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<PayResponse | null>(null);
  const meta = SPORTS[game.sport_type] ?? SPORTS.basketball;
  const due = amountDue(game.total_cost, game.collected_amount, game.share_amount, game.paid_count, game.required_players);

  const pay = async () => {
    hapticImpact('medium');
    setStage('processing');
    setError(null);
    const startedAt = Date.now();
    try {
      const response = await api.payShare(game.id, {
        user_max_id: identity.maxUserId,
        user_name: identity.name || null,
        amount: due,
        payment_method: 'sbp_mock',
      });
      const wait = MIN_PROCESSING_MS - (Date.now() - startedAt);
      if (wait > 0) await new Promise((resolve) => window.setTimeout(resolve, wait));
      setResult(response);
      setStage('done');
      onPaid(response);
    } catch (err) {
      setError(errorMessage(err));
      setStage('form');
    }
  };

  if (stage === 'done' && result) {
    const paidGame = result.game;
    const percent = percentOf(paidGame.collected_amount, paidGame.total_cost);
    return (
      <Modal
        title="Оплата прошла"
        subtitle="MAX Escrow · тестовый режим"
        onClose={onClose}
        footer={
          <button type="button" className="btn-primary w-full" onClick={onClose}>
            Готово
          </button>
        }
      >
        <div className="flex flex-col items-center py-2 text-center">
          <span className="flex h-20 w-20 animate-pop-in items-center justify-center rounded-full bg-emerald-100 dark:bg-emerald-400/15">
            <CircleCheckBig className="h-11 w-11 text-emerald-600 dark:text-emerald-400" />
          </span>
          <h3 className="mt-4 text-xl font-bold">{formatRub(result.transaction.amount)} на эскроу-счёте</h3>
          <p className="mt-1 text-sm text-slate-500">
            Счёт #{paidGame.escrow_account_id} · чек {result.transaction.reference}
          </p>
        </div>

        {result.booked ? (
          <div className="mt-3 animate-pop-in rounded-2xl bg-emerald-600 p-4 text-white">
            <p className="text-lg font-bold">🎉 Корт успешно забронирован!</p>
            <p className="mt-1 text-sm text-white/90">
              Номер брони: <b className="font-mono">#{result.booking_reference}</b>
            </p>
            <p className="mt-2 text-sm text-white/90">
              Собрано 100% ({formatRub(paidGame.total_cost)}). Сумма переведена арендодателю, электронный ваучер придёт
              участникам в MAX.
            </p>
          </div>
        ) : (
          <div className="card mt-3">
            <p className="text-sm">
              Собрано: <b>{formatRub(paidGame.collected_amount)}</b> из {formatRub(paidGame.total_cost)} ({percent}%)
            </p>
            <div className="mt-2 h-2.5 overflow-hidden rounded-full bg-slate-100 dark:bg-white/10">
              <div className="h-full rounded-full bg-emerald-500 transition-all duration-700" style={{ width: `${percent}%` }} />
            </div>
            <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">
              Корт выкупится автоматически, когда оплатят все участники. Бот MAX сообщит о брони.
            </p>
          </div>
        )}
      </Modal>
    );
  }

  return (
    <Modal
      title="Безопасная оплата"
      subtitle="MAX Escrow · тестовый режим"
      onClose={stage === 'processing' ? () => undefined : onClose}
      footer={
        <div>
          {error && (
            <p className="mb-2 rounded-xl bg-rose-50 px-3 py-2 text-sm text-rose-700 dark:bg-rose-400/10 dark:text-rose-300">{error}</p>
          )}
          <button
            type="button"
            className="btn-primary w-full bg-slate-900 hover:bg-slate-800 dark:bg-white dark:text-slate-900 dark:hover:bg-slate-100"
            disabled={stage === 'processing' || due <= 0}
            onClick={pay}
          >
            {stage === 'processing' ? <Spinner /> : <Zap className="h-5 w-5 text-amber-400" />}
            {stage === 'processing' ? 'Проводим платёж…' : 'Оплатить через СБП (Тест)'}
          </button>
          <p className="mt-2 flex items-center justify-center gap-1.5 text-xs text-slate-500 dark:text-slate-400">
            <Lock className="h-3.5 w-3.5" />
            Демонстрационный платёж: реальные деньги не списываются
          </p>
        </div>
      }
    >
      <div className="card text-center">
        <p className="text-sm text-slate-500 dark:text-slate-400">Ваша доля</p>
        <p className="mt-1 text-4xl font-bold tracking-tight">{formatRub(due)}</p>
        <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
          из {formatRub(game.total_cost)} за корт · {playersText(game.required_players)}
        </p>
      </div>

      <div className="card mt-3 divide-y divide-slate-100 py-1 dark:divide-white/5">
        <Row label="Получатель" value={`Эскроу-счёт #${game.escrow_account_id}`} />
        <Row
          label="Назначение"
          value={`${meta.label} ${formatLabel(game.sport_type, game.required_players)}, ${formatGameWhen(game.start_time, game.slot?.end_time).toLowerCase()}`}
        />
        <Row label="Корт" value={courtTitle} />
        <Row label="Плательщик" value={identity.name || 'Гость'} />
        <Row label="Способ" value="СБП · тестовый режим" />
      </div>

      <div className="mt-3 flex gap-3 rounded-2xl bg-emerald-50 p-4 text-sm text-emerald-900 dark:bg-emerald-400/10 dark:text-emerald-200">
        <ShieldCheck className="h-5 w-5 shrink-0" />
        <p>
          Деньги не уходят организатору: они замораживаются на защищённом счёте сбора и переводятся арендодателю, только когда
          соберётся 100%. Если сбор не наберётся к дедлайну, оплата вернётся автоматически.
        </p>
      </div>
    </Modal>
  );
}
