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
  return typeof window === 'undefined' ? undefined : window.WebApp;
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
  return Boolean(webApp()?.initData);
}

export function getInitData(): string {
  return webApp()?.initData ?? '';
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
  const court = params.get('court');
  return params.get('startapp') ?? (court ? `court_${court}` : null);
}

export function getStartCourtId(): number | null {
  const match = getStartParam()?.match(/^court_(\d+)$/);
  return match ? Number(match[1]) : null;
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
  if (existing) return existing;
  const profile = { id: `guest_${Math.random().toString(36).slice(2, 10)}`, name: '' };
  writeGuest(profile);
  return profile;
}

export function getIdentity(): Identity {
  const user = webApp()?.initDataUnsafe?.user;
  if (user?.id) {
    const name = [user.first_name, user.last_name].filter(Boolean).join(' ') || user.username || 'Игрок MAX';
    return { maxUserId: String(user.id), name, username: user.username ?? null, isGuest: false };
  }
  const guest = ensureGuest();
  return { maxUserId: guest.id, name: guest.name, username: null, isGuest: true };
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
