import { getInitData } from '../lib/max';

export type Query = Record<string, string | number | boolean | null | undefined>;

const RAW_API_BASE = (import.meta.env.VITE_API_BASE_URL || import.meta.env.VITE_API_BASE || '/api/v1').trim();

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly isNetworkOrTimeout: boolean = false,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

function extractMessage(data: unknown): string | null {
  if (!data || typeof data !== 'object') return null;
  const detail = (data as { detail?: unknown }).detail;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    const messages = detail
      .map((item) => (item && typeof item === 'object' ? String((item as { msg?: unknown }).msg ?? '') : ''))
      .filter(Boolean);
    return messages.length ? messages.join('; ') : null;
  }
  return null;
}

function normalizeBaseUrl(raw: string): string {
  const trimmed = raw.trim().replace(/\/+$/, '');
  if (!trimmed) {
    return '/api/v1';
  }
  try {
    if (/^https?:\/\//i.test(trimmed)) {
      const parsed = new URL(trimmed);
      const path = parsed.pathname.replace(/\/+$/, '');
      if (!path || path === '') {
        parsed.pathname = '/api/v1';
        return parsed.toString().replace(/\/+$/, '');
      }
      if (path === '/api') {
        parsed.pathname = '/api/v1';
        return parsed.toString().replace(/\/+$/, '');
      }
      return trimmed;
    }
  } catch {
    // fallback if URL constructor fails
  }

  if (trimmed === '/' || trimmed === '') return '/api/v1';
  if (trimmed === '/api') return '/api/v1';
  return trimmed;
}

function buildUrl(path: string, query?: Query): string {
  const normalizedPath = path.startsWith('/') ? path : `/${path}`;
  const base = normalizeBaseUrl(RAW_API_BASE);
  const baseIsAbsolute = /^https?:\/\//i.test(base);

  // Предотвращаем дублирование префиксов /api или /api/v1
  let cleanPath = normalizedPath;
  if (base.endsWith('/api/v1') && cleanPath.startsWith('/api/v1/')) {
    cleanPath = cleanPath.slice('/api/v1'.length);
  } else if (base.endsWith('/api') && cleanPath.startsWith('/api/')) {
    cleanPath = cleanPath.slice('/api'.length);
  }

  const url = baseIsAbsolute
    ? new URL(base.replace(/\/+$/, '') + cleanPath)
    : new URL(base.replace(/\/+$/, '') + cleanPath, window.location.origin);

  Object.entries(query ?? {}).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') {
      url.searchParams.set(key, String(value));
    }
  });
  return url.toString();
}

async function request<T>(path: string, options: { method?: string; body?: unknown; query?: Query; timeoutMs?: number } = {}): Promise<T> {
  const targetUrl = buildUrl(path, options.query);
  const headers: Record<string, string> = { Accept: 'application/json' };
  if (options.body !== undefined) headers['Content-Type'] = 'application/json';
  const initData = getInitData();
  if (initData) headers['X-Max-Init-Data'] = initData;

  const controller = new AbortController();
  const timeoutMs = options.timeoutMs ?? 4000;
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  let response: Response;
  try {
    response = await fetch(targetUrl, {
      method: options.method ?? 'GET',
      headers,
      body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
      signal: controller.signal,
    });
  } catch (err: unknown) {
    const isTimeout = (err as Error)?.name === 'AbortError';
    throw new ApiError(
      isTimeout
        ? 'Превышено время ожидания ответа сервера (таймаут)'
        : 'Нет связи с сервером (ошибка сети или CORS)',
      0,
      true,
    );
  } finally {
    clearTimeout(timeoutId);
  }

  const text = await response.text();
  let data: unknown = null;
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = null;
    }
  }
  if (!response.ok) {
    const isServerError = response.status >= 500;
    const fallback = isServerError ? 'Сервер временно недоступен' : `Ошибка ${response.status}`;
    throw new ApiError(extractMessage(data) ?? fallback, response.status, isServerError);
  }
  return data as T;
}

export function errorMessage(error: unknown): string {
  if (error instanceof ApiError) return error.message;
  if (error instanceof Error && error.message) return error.message;
  return 'Что-то пошло не так';
}

export const rawRequest = request;

import { spotsService } from './spotsService';
export { spotsService };
export const api = spotsService;

