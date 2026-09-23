import { useState } from 'react';
import { MapPinPlus } from 'lucide-react';
import { api, errorMessage } from '../api/client';
import { SPORT_ORDER, SPORTS, SURFACE_ORDER, SURFACES } from '../lib/constants';
import type { Court, SportType, SurfaceType } from '../types';
import { Modal, Spinner, Toggle } from './ui';

interface AddCourtModalProps {
  point: { lat: number; lng: number };
  onClose: () => void;
  onCreated: (court: Court) => void;
}

export default function AddCourtModal({ point, onClose, onCreated }: AddCourtModalProps) {
  const [title, setTitle] = useState('');
  const [address, setAddress] = useState('');
  const [sports, setSports] = useState<SportType[]>([]);
  const [surface, setSurface] = useState<SurfaceType>('rubber');
  const [hasLighting, setHasLighting] = useState(false);
  const [isIndoor, setIsIndoor] = useState(false);
  const [description, setDescription] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const canSubmit = title.trim().length >= 3 && address.trim().length >= 3 && sports.length > 0;

  const toggleSport = (sport: SportType) =>
    setSports((current) => (current.includes(sport) ? current.filter((s) => s !== sport) : [...current, sport]));

  const submit = async () => {
    setSubmitting(true);
    setError(null);
    try {
      const court = await api.createCourt({
        title: title.trim(),
        address: address.trim(),
        sport_types: sports,
        latitude: point.lat,
        longitude: point.lng,
        surface_type: surface,
        has_lighting: hasLighting,
        is_indoor: isIndoor,
        description: description.trim(),
      });
      onCreated(court);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Modal
      title="Новая площадка"
      subtitle={`Точка на карте: ${point.lat.toFixed(5)}, ${point.lng.toFixed(5)}`}
      onClose={onClose}
      footer={
        <div>
          {error && <p className="mb-2 rounded-xl bg-rose-50 px-3 py-2 text-sm text-rose-700 dark:bg-rose-400/10 dark:text-rose-300">{error}</p>}
          <button type="button" className="btn-primary w-full" disabled={!canSubmit || submitting} onClick={submit}>
            {submitting ? <Spinner /> : <MapPinPlus className="h-5 w-5" />}
            Добавить на карту
          </button>
        </div>
      }
    >
      <label className="field-label" htmlFor="court-title">
        Название
      </label>
      <input
        id="court-title"
        className="input"
        maxLength={200}
        value={title}
        onChange={(event) => setTitle(event.target.value)}
        placeholder="Например: коробка во дворе на Лиговском"
      />

      <label className="field-label mt-4" htmlFor="court-address">
        Адрес или ориентир
      </label>
      <input
        id="court-address"
        className="input"
        maxLength={300}
        value={address}
        onChange={(event) => setAddress(event.target.value)}
        placeholder="Улица, дом, как найти"
      />

      <span className="field-label mt-4">Виды спорта</span>
      <div className="flex flex-wrap gap-2">
        {SPORT_ORDER.map((sport) => {
          const active = sports.includes(sport);
          return (
            <button
              key={sport}
              type="button"
              aria-pressed={active}
              onClick={() => toggleSport(sport)}
              className={active ? 'chip text-white shadow-sm' : 'chip-idle'}
              style={active ? { background: SPORTS[sport].color } : undefined}
            >
              {SPORTS[sport].emoji} {SPORTS[sport].label}
            </button>
          );
        })}
      </div>

      <span className="field-label mt-4">Покрытие</span>
      <div className="flex flex-wrap gap-2">
        {SURFACE_ORDER.map((value) => (
          <button
            key={value}
            type="button"
            aria-pressed={surface === value}
            onClick={() => setSurface(value)}
            className={surface === value ? 'chip bg-slate-900 text-white dark:bg-white dark:text-slate-900' : 'chip-idle'}
          >
            {SURFACES[value]}
          </button>
        ))}
      </div>

      <div className="mt-4 space-y-2">
        <Toggle checked={hasLighting} onChange={setHasLighting} label="Есть освещение" description="Можно играть вечером" />
        <Toggle checked={isIndoor} onChange={setIsIndoor} label="Крытая площадка" description="Манеж, зал или навес" />
      </div>

      <label className="field-label mt-4" htmlFor="court-description">
        Описание <span className="font-normal text-slate-400">(необязательно)</span>
      </label>
      <textarea
        id="court-description"
        rows={3}
        maxLength={2000}
        value={description}
        onChange={(event) => setDescription(event.target.value)}
        placeholder="Сколько колец или ворот, есть ли сетки, когда обычно свободно"
        className="input resize-none"
      />
    </Modal>
  );
}
