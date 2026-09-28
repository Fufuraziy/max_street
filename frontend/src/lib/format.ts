import { SPORTS } from './constants';
import type { SportType } from '../types';

const WEEKDAYS = ['вс', 'пн', 'вт', 'ср', 'чт', 'пт', 'сб'];
const MONTHS = ['янв', 'фев', 'мар', 'апр', 'мая', 'июн', 'июл', 'авг', 'сен', 'окт', 'ноя', 'дек'];
const DAY_MS = 86_400_000;

export function plural(n: number, forms: [string, string, string]): string {
  const abs = Math.abs(n) % 100;
  if (abs > 10 && abs < 20) return forms[2];
  if (abs % 10 === 1) return forms[0];
  if (abs % 10 >= 2 && abs % 10 <= 4) return forms[1];
  return forms[2];
}

export function dayDiff(date: Date, now = new Date()): number {
  const a = new Date(date.getFullYear(), date.getMonth(), date.getDate()).getTime();
  const b = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
  return Math.round((a - b) / DAY_MS);
}

export function formatTime(date: Date): string {
  return `${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`;
}

export function dayLabel(date: Date): string {
  const diff = dayDiff(date);
  if (diff === 0) return 'Сегодня';
  if (diff === 1) return 'Завтра';
  if (diff === -1) return 'Вчера';
  return `${WEEKDAYS[date.getDay()]}, ${date.getDate()} ${MONTHS[date.getMonth()]}`;
}

export function formatGameDate(iso: string): string {
  const date = new Date(iso);
  return `${dayLabel(date)}, ${formatTime(date)}`;
}

export function shortDayLabel(date: Date): { top: string; bottom: string } {
  const diff = dayDiff(date);
  if (diff === 0) return { top: 'Сегодня', bottom: `${date.getDate()} ${MONTHS[date.getMonth()]}` };
  if (diff === 1) return { top: 'Завтра', bottom: `${date.getDate()} ${MONTHS[date.getMonth()]}` };
  return { top: WEEKDAYS[date.getDay()], bottom: `${date.getDate()} ${MONTHS[date.getMonth()]}` };
}

export function timeAgo(iso: string): string {
  const diff = dayDiff(new Date(iso));
  if (diff === 0) return 'сегодня';
  if (diff === -1) return 'вчера';
  const days = Math.abs(diff);
  return `${days} ${plural(days, ['день', 'дня', 'дней'])} назад`;
}

export function formatLabel(sport: SportType, players: number): string {
  const known = SPORTS[sport]?.formats.find((format) => format.players === players);
  if (known) return known.label;
  if (sport === 'workout' || players % 2) return `${players} ${plural(players, ['участник', 'участника', 'участников'])}`;
  return `${players / 2}×${players / 2}`;
}

export function playersText(n: number): string {
  return `${n} ${plural(n, ['игрок', 'игрока', 'игроков'])}`;
}

export function initials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (!parts.length) return '?';
  return (parts[0][0] + (parts[1]?.[0] ?? '')).toUpperCase();
}

export function avatarColor(seed: string): string {
  let hash = 0;
  for (let i = 0; i < seed.length; i += 1) hash = (hash * 31 + seed.charCodeAt(i)) | 0;
  return `hsl(${Math.abs(hash) % 360} 65% 52%)`;
}

export function hexToRgba(hex: string, alpha: number): string {
  const value = hex.replace('#', '');
  const r = parseInt(value.slice(0, 2), 16);
  const g = parseInt(value.slice(2, 4), 16);
  const b = parseInt(value.slice(4, 6), 16);
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

export function routeUrl(lat: number, lon: number): string {
  return `https://yandex.ru/maps/?rtext=~${lat.toFixed(6)},${lon.toFixed(6)}&rtt=pd`;
}

/** Расчёт расстояния между двумя координатами по формуле Haversine (в метрах). */
export function calculateDistanceMeters(lat1: number, lon1: number, lat2: number, lon2: number): number {
  const R = 6371e3;
  const rad = Math.PI / 180;
  const phi1 = lat1 * rad;
  const phi2 = lat2 * rad;
  const deltaPhi = (lat2 - lat1) * rad;
  const deltaLambda = (lon2 - lon1) * rad;
  const a =
    Math.sin(deltaPhi / 2) * Math.sin(deltaPhi / 2) +
    Math.cos(phi1) * Math.cos(phi2) * Math.sin(deltaLambda / 2) * Math.sin(deltaLambda / 2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return Math.round(R * c);
}

/** 350 → «350 м», 1400 → «1,4 км». */
export function formatDistance(meters: number): string {
  if (meters < 1000) return `${Math.round(meters / 10) * 10} м`;
  return `${(meters / 1000).toFixed(1).replace('.', ',')} км`;
}

/** Форматирование текста официального обращения для портала «Наш Санкт-Петербург» / Госуслуг. */
export function formatOfficialAppealText(courtTitle: string, address: string, defectLabel: string, description: string): string {
  const now = new Date();
  const dateStr = `${String(now.getDate()).padStart(2, '0')}.${String(now.getMonth() + 1).padStart(2, '0')}.${now.getFullYear()}`;
  return `В Администрацию района / Комитет по благоустройству Санкт-Петербурга
Портал «Наш Санкт-Петербург» / Сервис «Госуслуги. Решаем вместе»

ЗАЯВЛЕНИЕ О ДЕФЕКТЕ СПОРТИВНОЙ ИНФРАСТРУКТУРЫ
(Зафиксировано через сервис «MAX Спот»)

1. Объект: ${courtTitle}
2. Адрес расположения: ${address}
3. Обнаруженная неисправность: ${defectLabel}
${description ? `4. Подробное описание: ${description}\n` : ''}5. Дата фиксации: ${dateStr}

Прошу провести выездную инспекцию спортивного объекта и устранить выявленные дефекты в сроки, установленные регламентом содержания объектов физической культуры и спорта.`;
}

const rubFormatter = new Intl.NumberFormat('ru-RU', { maximumFractionDigits: 2 });

/** 1800 → «1 800 ₽», 583.33 → «583,33 ₽». */
export function formatRub(amount: number): string {
  return `${rubFormatter.format(amount)} ₽`;
}

/** «18:00–19:30» */
export function formatTimeRange(startIso: string, endIso: string): string {
  return `${formatTime(new Date(startIso))}–${formatTime(new Date(endIso))}`;
}

/** Дата сбора с диапазоном слота, если он есть: «Завтра, 18:00–19:30». */
export function formatGameWhen(startIso: string, endIso?: string | null): string {
  const start = new Date(startIso);
  return endIso ? `${dayLabel(start)}, ${formatTimeRange(startIso, endIso)}` : `${dayLabel(start)}, ${formatTime(start)}`;
}

/** Локальная дата в формате YYYY-MM-DD для запроса расписания. */
export function dateKey(date: Date): string {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
}

export function percentOf(part: number, total: number): number {
  return total > 0 ? Math.min(100, Math.floor((part / total) * 100)) : 0;
}

/** Сколько должен внести участник: доля, а последний плательщик — точный остаток (как на сервере). */
export function amountDue(total: number, collected: number, share: number, paidCount: number, required: number): number {
  const remaining = Math.round((total - collected) * 100) / 100;
  return paidCount >= required - 1 ? remaining : Math.min(share, remaining);
}
