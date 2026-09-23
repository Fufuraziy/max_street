import { useState } from 'react';
import { CircleCheckBig, Send } from 'lucide-react';
import { api, errorMessage } from '../api/client';
import { DEFECTS } from '../lib/constants';
import { hapticImpact } from '../lib/max';
import type { Court, Defect, DefectType, Identity } from '../types';
import { Modal, Spinner } from './ui';

interface ReportDefectModalProps {
  court: Court;
  identity: Identity;
  onClose: () => void;
  onReported: (defect: Defect) => void;
}

export default function ReportDefectModal({ court, identity, onClose, onReported }: ReportDefectModalProps) {
  const [type, setType] = useState<DefectType | null>(null);
  const [description, setDescription] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [created, setCreated] = useState<Defect | null>(null);

  const submit = async () => {
    if (!type) return;
    setSubmitting(true);
    setError(null);
    try {
      const defect = await api.reportDefect(court.id, {
        user_max_id: identity.maxUserId,
        user_name: identity.name || null,
        defect_type: type,
        description: description.trim(),
      });
      setCreated(defect);
      onReported(defect);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setSubmitting(false);
    }
  };

  if (created) {
    return (
      <Modal
        title="Спасибо!"
        onClose={onClose}
        footer={
          <button type="button" className="btn-primary w-full" onClick={onClose}>
            Готово
          </button>
        }
      >
        <div className="flex flex-col items-center py-4 text-center">
          <span className="flex h-20 w-20 animate-pop-in items-center justify-center rounded-full bg-emerald-100 dark:bg-emerald-400/15">
            <CircleCheckBig className="h-11 w-11 text-emerald-600 dark:text-emerald-400" />
          </span>
          <h3 className="mt-4 text-xl font-bold">Заявка зарегистрирована</h3>
          <p className="mt-1 text-sm font-semibold text-slate-500">
            №{created.id} · {created.status_label}
          </p>
          <p className="mt-4 max-w-sm text-[15px] leading-relaxed text-slate-600 dark:text-slate-300">
            Проблема «{created.defect_label}» на площадке «{court.title}» зафиксирована. Статус заявки виден в карточке
            площадки.
          </p>
        </div>
      </Modal>
    );
  }

  return (
    <Modal
      title="Сообщить о поломке"
      subtitle={court.title}
      onClose={onClose}
      footer={
        <div>
          {error && <p className="mb-2 rounded-xl bg-rose-50 px-3 py-2 text-sm text-rose-700 dark:bg-rose-400/10 dark:text-rose-300">{error}</p>}
          <button type="button" className="btn-primary w-full" disabled={!type || submitting} onClick={submit}>
            {submitting ? <Spinner /> : <Send className="h-5 w-5" />}
            Отправить заявку
          </button>
        </div>
      }
    >
      <span className="field-label">Что случилось?</span>
      <div className="grid grid-cols-2 gap-2">
        {DEFECTS.map((item) => {
          const active = type === item.type;
          return (
            <button
              key={item.type}
              type="button"
              aria-pressed={active}
              onClick={() => {
                hapticImpact('light');
                setType(item.type);
              }}
              className={`flex flex-col items-start gap-1 rounded-2xl border-2 p-3 text-left transition active:scale-[0.98] ${
                active
                  ? 'border-accent bg-accent-soft dark:bg-accent/15'
                  : 'border-transparent bg-white dark:bg-white/5'
              }`}
            >
              <span className="text-2xl" aria-hidden>
                {item.emoji}
              </span>
              <span className="font-semibold leading-tight">{item.label}</span>
              <span className="text-xs text-slate-500 dark:text-slate-400">{item.hint}</span>
            </button>
          );
        })}
      </div>

      <label className="field-label mt-5" htmlFor="defect-description">
        Подробности <span className="font-normal text-slate-400">(необязательно)</span>
      </label>
      <textarea
        id="defect-description"
        rows={3}
        maxLength={1000}
        value={description}
        onChange={(event) => setDescription(event.target.value)}
        placeholder="Где именно и насколько серьёзно? Например: погнуто кольцо на южном щите"
        className="input resize-none"
      />
      <p className="mt-3 text-sm text-slate-500 dark:text-slate-400">
        Заявка сразу получит статус «Передано в районные службы», а игроки увидят предупреждение в карточке площадки.
      </p>
    </Modal>
  );
}
