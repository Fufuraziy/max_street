/**
 * Обёртка над MAX Bridge (window.WebApp из https://st.max.ru/js/max-web-app.js).
 * Вне мессенджера (обычный браузер) всё работает в «гостевом» режиме.
 */
import { useEffect, useRef } from 'react';
import type { Identity } from '../types';

interface MaxWebAppUser {
  id: number | string;
  first_name?: string;
  last_name?: string;
  username?: string;
  language_code?: string;
  photo_url?: string;
}

interface MaxWebApp {
  initData?: string;
  initDataUnsafe?: {
    user?: MaxWebAppUser;
    start_param?: unknown;
    query_id?: string;
    auth_date?: number;
    hash?: string;
  };
  platform?: string;
  version?: string;
  ready?: () => unknown;
  openLink?: (url: string) => unknown;
  openMaxLink?: (url: string) => unknown;
  shareMaxContent?: (params: { text?: string; link?: string }) => unknown;
  BackButton?: {
    show: () => unknown;
    hide: () => unknown;
    onClick: (callback: () => void) => unknown;
    offClick: (callback: () => void) => unknown;
  };
  HapticFeedback?: {
    impactOccurred?: (style: 'light' | 'medium' | 'heavy' | 'rigid' | 'soft') => unknown;
    notificationOccurred?: (type: 'error' | 'success' | 'warning') => unknown;
  };
}

declare global {
  interface Window {
    WebApp?: MaxWebApp;
  }
}

const GUEST_KEY = 'maxstreet.guest';

function webApp(): MaxWebApp | undefined {
  if (typeof window === 'undefined') return undefined;
  const win = window as any;
  return win.WebApp || win.Telegram?.WebApp || win.MaxWebApp;
}

/** Методы моста возвращают Promise и могут отсутствовать на части платформ: глушим ошибки. */
function safe(call: () => unknown): void {
  try {
    const result = call();
    if (result && typeof (result as Promise<unknown>).catch === 'function') {
      (result as Promise<unknown>).catch(() => undefined);
    }
  } catch {
    /* метод недоступен вне MAX */
  }
}

export function initMaxBridge(): void {
  safe(() => webApp()?.ready?.());
}

export function isInsideMax(): boolean {
  return Boolean(webApp()?.initData || (window as any).Telegram?.WebApp?.initData);
}

export function getInitData(): string {
  const fromBridge = webApp()?.initData;
  if (fromBridge) return fromBridge;
  if (typeof window !== 'undefined') {
    const params = new URLSearchParams(window.location.search);
    const hashParams = new URLSearchParams(window.location.hash.replace(/^#/, ''));
    return params.get('initData') || params.get('tgWebAppData') || hashParams.get('tgWebAppData') || hashParams.get('initData') || '';
  }
  return '';
}

/** start_param из deep link https://max.ru/<bot>?startapp=court_12 или ?court=12 в браузере. */
export function getStartParam(): string | null {
  const raw = webApp()?.initDataUnsafe?.start_param;
  if (typeof raw === 'string' && raw) return raw;
  if (raw && typeof raw === 'object') {
    const record = raw as Record<string, unknown>;
    const value = record.value ?? record.payload ?? record.startapp;
    if (typeof value === 'string' && value) return value;
  }
  const params = new URLSearchParams(window.location.search);
  const hashParams = new URLSearchParams(window.location.hash.replace(/^#/, ''));
  const court = params.get('court') || hashParams.get('court');
  return params.get('startapp') ?? hashParams.get('startapp') ?? (court ? `court_${court}` : null);
}

export function getStartCourtId(): number | null {
  const match = getStartParam()?.match(/^court_(\d+)$/);
  return match ? Number(match[1]) : null;
}

export function getInitialLocationFromUrl(): [number, number] | null {
  if (typeof window === 'undefined') return null;
  try {
    const searchParams = new URLSearchParams(window.location.search);
    const hashParams = new URLSearchParams(window.location.hash.replace(/^#/, ''));
    const latStr = searchParams.get('lat') || hashParams.get('lat') || searchParams.get('latitude') || hashParams.get('latitude');
    const lonStr = searchParams.get('lon') || hashParams.get('lon') || searchParams.get('lng') || hashParams.get('longitude') || hashParams.get('lng');
    if (latStr && lonStr) {
      const lat = parseFloat(latStr);
      const lon = parseFloat(lonStr);
      if (!isNaN(lat) && !isNaN(lon) && lat >= -90 && lat <= 90 && lon >= -180 && lon <= 180) {
        return [lat, lon];
      }
    }
  } catch {
    /* ignore */
  }
  return null;
}

interface GuestProfile {
  id: string;
  name: string;
}

function readGuest(): GuestProfile | null {
  try {
    const parsed = JSON.parse(localStorage.getItem(GUEST_KEY) ?? 'null') as Partial<GuestProfile> | null;
    if (parsed && typeof parsed.id === 'string') {
      return { id: parsed.id, name: typeof parsed.name === 'string' ? parsed.name : '' };
    }
  } catch {
    /* localStorage недоступен */
  }
  return null;
}

function writeGuest(profile: GuestProfile): void {
  try {
    localStorage.setItem(GUEST_KEY, JSON.stringify(profile));
  } catch {
    /* приватный режим */
  }
}

function ensureGuest(): GuestProfile {
  const existing = readGuest();
  if (existing && existing.name.trim()) return existing;
  const profile = { id: existing?.id || `usr_${Math.random().toString(36).slice(2, 10)}`, name: 'Игрок MAX' };
  writeGuest(profile);
  return profile;
}

function parseUserFromUrl(): Identity | null {
  if (typeof window === 'undefined') return null;

  try {
    const searchParams = new URLSearchParams(window.location.search);
    const hashParams = new URLSearchParams(window.location.hash.replace(/^#/, ''));

    // 1. Проверяем initData / tgWebAppData в search и hash
    const rawInitData =
      searchParams.get('initData') ||
      searchParams.get('tgWebAppData') ||
      hashParams.get('tgWebAppData') ||
      hashParams.get('initData');
    if (rawInitData) {
      const initParsed = new URLSearchParams(rawInitData);
      const rawUser = initParsed.get('user');
      if (rawUser) {
        try {
          const userObj = JSON.parse(rawUser) as {
            id?: number | string;
            first_name?: string;
            last_name?: string;
            username?: string;
          };
          if (userObj && (userObj.id || userObj.first_name || userObj.username)) {
            const name =
              [userObj.first_name, userObj.last_name].filter(Boolean).join(' ') ||
              userObj.username ||
              (userObj.id ? `Пользователь #${userObj.id}` : 'Игрок MAX');
            const uid = String(userObj.id || ensureGuest().id);
            const identity: Identity = {
              maxUserId: uid,
              name,
              username: userObj.username ?? null,
              isGuest: false,
            };
            writeGuest({ id: identity.maxUserId, name: identity.name });
            return identity;
          }
        } catch {
          /* игнорируем повреждённый JSON */
        }
      }
    }

    // 2. Проверяем прямые URL-параметры (user_id, userId, id, name, user_name, username)
    const directId =
      searchParams.get('user_id') ||
      searchParams.get('userId') ||
      searchParams.get('id') ||
      hashParams.get('user_id') ||
      hashParams.get('userId') ||
      hashParams.get('id');

    const rawName =
      searchParams.get('user_name') ||
      searchParams.get('userName') ||
      searchParams.get('name') ||
      searchParams.get('first_name') ||
      hashParams.get('name') ||
      hashParams.get('user_name');

    const directUsername = searchParams.get('username') || hashParams.get('username') || null;

    if (directId || rawName || directUsername) {
      const cleanName = rawName
        ? decodeURIComponent(rawName).trim()
        : directUsername || (directId ? `Пользователь #${directId}` : 'Игрок MAX');
      const uid = String(directId || ensureGuest().id);
      const identity: Identity = {
        maxUserId: uid,
        name: cleanName,
        username: directUsername,
        isGuest: false,
      };
      writeGuest({ id: identity.maxUserId, name: identity.name });
      return identity;
    }
  } catch {
    /* безопасность при сбоях парсинга URL */
  }

  return null;
}

export function getIdentity(): Identity {
  const user = webApp()?.initDataUnsafe?.user;
  if (user?.id) {
    const name = [user.first_name, user.last_name].filter(Boolean).join(' ') || user.username || 'Игрок MAX';
    return { maxUserId: String(user.id), name, username: user.username ?? null, isGuest: false };
  }
  const fromUrl = parseUserFromUrl();
  if (fromUrl) {
    return fromUrl;
  }
  const guest = ensureGuest();
  return { maxUserId: guest.id, name: guest.name, username: null, isGuest: guest.name === 'Игрок MAX' };
}

export function saveGuestName(name: string): Identity {
  writeGuest({ ...ensureGuest(), name: name.trim() });
  return getIdentity();
}

export function hapticImpact(style: 'light' | 'medium' | 'heavy' = 'light'): void {
  safe(() => webApp()?.HapticFeedback?.impactOccurred?.(style));
}

export function hapticNotify(type: 'success' | 'error' | 'warning'): void {
  safe(() => webApp()?.HapticFeedback?.notificationOccurred?.(type));
}

export function openExternalLink(url: string): void {
  const app = webApp();
  if (isInsideMax() && app?.openLink) {
    safe(() => app.openLink?.(url));
    return;
  }
  window.open(url, '_blank', 'noopener,noreferrer');
}

/** Ссылка на max.ru (чат, канал, бот) открывается внутри MAX, остальные — во внешнем браузере. */
export function openMaxLink(url: string): void {
  const app = webApp();
  if (isInsideMax() && app?.openMaxLink) {
    safe(() => app.openMaxLink?.(url));
    return;
  }
  openExternalLink(url);
}

export async function shareLink(text: string, link: string): Promise<'shared' | 'copied' | 'failed'> {
  const app = webApp();
  if (isInsideMax() && app?.shareMaxContent) {
    safe(() => app.shareMaxContent?.({ text, link }));
    return 'shared';
  }
  if (typeof navigator.share === 'function') {
    try {
      await navigator.share({ title: 'MAX Стрит', text, url: link });
      return 'shared';
    } catch (error) {
      if ((error as DOMException)?.name === 'AbortError') return 'shared';
    }
  }
  try {
    await navigator.clipboard.writeText(`${text}\n${link}`);
    return 'copied';
  } catch {
    return 'failed';
  }
}

/** Системная кнопка «Назад» MAX + Escape на десктопе. */
export function useBackButton(visible: boolean, onBack: () => void): void {
  const handlerRef = useRef(onBack);
  handlerRef.current = onBack;

  useEffect(() => {
    // Вне MAX мост не может доставить событие кнопки, поэтому трогаем её только внутри мессенджера.
    const button = isInsideMax() ? webApp()?.BackButton : undefined;
    if (!visible) {
      if (button) safe(() => button.hide());
      return;
    }
    const handler = () => handlerRef.current();
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') handlerRef.current();
    };
    if (button) {
      safe(() => button.onClick(handler));
      safe(() => button.show());
    }
    window.addEventListener('keydown', onKey);
    return () => {
      window.removeEventListener('keydown', onKey);
      if (button) safe(() => button.offClick(handler));
    };
  }, [visible]);
}
