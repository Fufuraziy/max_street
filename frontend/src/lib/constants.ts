import type { DefectStatus, DefectType, GameStatus, PaymentStatus, SportType, SurfaceType } from '../types';

export interface SportFormat {
  label: string;
  players: number;
}

export interface SportMeta {
  label: string;
  short: string;
  emoji: string;
  color: string;
  formats: SportFormat[];
  defaultPlayers: number;
}

export const SPORTS: Record<SportType, SportMeta> = {
  basketball: {
    label: 'Баскетбол',
    short: 'Баскетбол',
    emoji: '🏀',
    color: '#F97316',
    formats: [
      { label: '1×1', players: 2 },
      { label: '2×2', players: 4 },
      { label: '3×3', players: 6 },
      { label: '5×5', players: 10 },
    ],
    defaultPlayers: 6,
  },
  football: {
    label: 'Футбол',
    short: 'Футбол',
    emoji: '⚽',
    color: '#16A34A',
    formats: [
      { label: '4×4', players: 8 },
      { label: '5×5', players: 10 },
      { label: '7×7', players: 14 },
      { label: '11×11', players: 22 },
    ],
    defaultPlayers: 10,
  },
  volleyball: {
    label: 'Волейбол',
    short: 'Волейбол',
    emoji: '🏐',
    color: '#0EA5E9',
    formats: [
      { label: '2×2', players: 4 },
      { label: '4×4', players: 8 },
      { label: '6×6', players: 12 },
    ],
    defaultPlayers: 8,
  },
  tennis: {
    label: 'Теннис',
    short: 'Теннис',
    emoji: '🎾',
    color: '#65A30D',
    formats: [
      { label: '1×1', players: 2 },
      { label: '2×2', players: 4 },
    ],
    defaultPlayers: 4,
  },
  padel: {
    label: 'Падел',
    short: 'Падел',
    emoji: '🥎',
    color: '#0D9488',
    formats: [
      { label: '2×2', players: 4 },
      { label: '1×1', players: 2 },
    ],
    defaultPlayers: 4,
  },
  table_tennis: {
    label: 'Настольный теннис',
    short: 'Пинг-понг',
    emoji: '🏓',
    color: '#E11D48',
    formats: [
      { label: '1×1', players: 2 },
      { label: '2×2', players: 4 },
      { label: 'Турнир на 8', players: 8 },
    ],
    defaultPlayers: 2,
  },
  workout: {
    label: 'Воркаут',
    short: 'Воркаут',
    emoji: '💪',
    color: '#8B5CF6',
    formats: [
      { label: 'Вдвоём', players: 2 },
      { label: 'Группа 4', players: 4 },
      { label: 'Группа 6', players: 6 },
      { label: 'Группа 10', players: 10 },
    ],
    defaultPlayers: 4,
  },
  multisport: {
    label: 'Мультиспорт',
    short: 'Мультиспорт',
    emoji: '🏅',
    color: '#8B5CF6',
    formats: [
      { label: 'Вдвоём', players: 2 },
      { label: 'Группа 4', players: 4 },
      { label: 'Группа 6', players: 6 },
    ],
    defaultPlayers: 4,
  },
} as Record<string, SportMeta>;

export const SPORT_ORDER: SportType[] = [
  'basketball',
  'football',
  'volleyball',
  'tennis',
  'padel',
  'table_tennis',
  'workout',
];

export const SURFACES: Record<string, string> = {
  rubber: 'Резиновое',
  asphalt: 'Асфальт',
  artificial_turf: 'Искусственный газон',
  artificial_grass: 'Искусственный газон',
  hard: 'Хард',
  parquet: 'Паркет',
  acrylic: 'Акрил',
  panoramic_glass_turf: 'Панорамное стекло / газон',
  padel_turf: 'Падел-газон',
  clay: 'Грунт',
  tera_flex: 'Терафлекс',
};

// Покрытия, которые можно выбрать при добавлении дворовой площадки.
export const SURFACE_ORDER: SurfaceType[] = ['rubber', 'asphalt', 'artificial_turf'];

export const DEFECTS: { type: DefectType; label: string; hint: string; emoji: string }[] = [
  { type: 'broken_ring', label: 'Сломано кольцо', hint: 'Кольцо, щит или ворота', emoji: '🏀' },
  { type: 'surface_damage', label: 'Яма в покрытии', hint: 'Трещины, отслоение, лужи', emoji: '🕳️' },
  { type: 'lighting_broken', label: 'Нет света', hint: 'Не работают фонари', emoji: '💡' },
  { type: 'net_missing', label: 'Нет сетки', hint: 'Порвана или снята', emoji: '🥅' },
  { type: 'trash', label: 'Мусор', hint: 'Стекло, мусор, вандализм', emoji: '🗑️' },
];

export const DEFECT_STATUS_STYLES: Record<DefectStatus, string> = {
  reported: 'bg-amber-100 text-amber-800 dark:bg-amber-400/15 dark:text-amber-300',
  sent_to_city: 'bg-sky-100 text-sky-800 dark:bg-sky-400/15 dark:text-sky-300',
  resolved: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-400/15 dark:text-emerald-300',
};

export const GAME_STATUS_STYLES: Record<GameStatus, string> = {
  recruiting: 'bg-accent-soft text-accent dark:bg-accent/20 dark:text-blue-300',
  confirmed: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-400/15 dark:text-emerald-300',
  booked: 'bg-emerald-600 text-white dark:bg-emerald-500 dark:text-white',
  finished: 'bg-slate-100 text-slate-600 dark:bg-white/10 dark:text-slate-300',
  cancelled: 'bg-rose-100 text-rose-700 dark:bg-rose-400/15 dark:text-rose-300',
};

export const PAYMENT_STATUS_STYLES: Record<PaymentStatus, string> = {
  pending: 'bg-amber-100 text-amber-800 dark:bg-amber-400/15 dark:text-amber-300',
  funded: 'bg-sky-100 text-sky-800 dark:bg-sky-400/15 dark:text-sky-300',
  paid_to_court: 'bg-emerald-600 text-white dark:bg-emerald-500',
  refunded: 'bg-slate-100 text-slate-600 dark:bg-white/10 dark:text-slate-300',
};

export const SPB_CENTER: [number, number] = [59.9386, 30.3141];
export const TILE_URL = 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png';
