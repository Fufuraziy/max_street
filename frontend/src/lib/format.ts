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
