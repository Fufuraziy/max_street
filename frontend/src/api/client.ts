import { getInitData } from '../lib/max';
import type {
  BotInfo,
  Court,
  CourtDetail,
  CreateCourtPayload,
  CreateGamePayload,
  Defect,
  GameWithCourt,
  JoinResponse,
  LeaveResponse,
  PlayerPayload,
  ReportDefectPayload,
  SportType,
} from '../types';

const API_BASE = import.meta.env.VITE_API_BASE ?? '/api/v1';

type Query = Record<string, string | number | boolean | null | undefined>;

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
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

async function request<T>(path: string, options: { method?: string; body?: unknown; query?: Query } = {}): Promise<T> {
  const url = new URL(API_BASE + path, window.location.origin);
  Object.entries(options.query ?? {}).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') url.searchParams.set(key, String(value));
  });

  const headers: Record<string, string> = { Accept: 'application/json' };
  if (options.body !== undefined) headers['Content-Type'] = 'application/json';
  const initData = getInitData();
  if (initData) headers['X-Max-Init-Data'] = initData;

  let response: Response;
  try {
    response = await fetch(url.toString(), {
      method: options.method ?? 'GET',
      headers,
      body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
    });
  } catch {
    throw new ApiError('Нет связи с сервером. Проверьте интернет и попробуйте ещё раз', 0);
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
    const fallback = response.status >= 500 ? 'Сервер временно недоступен' : `Ошибка ${response.status}`;
    throw new ApiError(extractMessage(data) ?? fallback, response.status);
  }
  return data as T;
}

export function errorMessage(error: unknown): string {
  if (error instanceof ApiError) return error.message;
  if (error instanceof Error && error.message) return error.message;
  return 'Что-то пошло не так';
}

export const api = {
  listCourts: (params: { sport_type?: SportType } = {}) => request<Court[]>('/courts', { query: params }),
  getCourt: (id: number) => request<CourtDetail>(`/courts/${id}`),
  createCourt: (payload: CreateCourtPayload) => request<Court>('/courts', { method: 'POST', body: payload }),
  listGames: (params: { court_id?: number; user_max_id?: string; sport_type?: SportType } = {}) =>
    request<GameWithCourt[]>('/games', { query: params }),
  createGame: (payload: CreateGamePayload) => request<GameWithCourt>('/games', { method: 'POST', body: payload }),
  joinGame: (id: number, player: PlayerPayload) =>
    request<JoinResponse>(`/games/${id}/join`, { method: 'POST', body: player }),
  leaveGame: (id: number, player: PlayerPayload) =>
    request<LeaveResponse>(`/games/${id}/leave`, { method: 'POST', body: player }),
  reportDefect: (courtId: number, payload: ReportDefectPayload) =>
    request<Defect>(`/courts/${courtId}/defects`, { method: 'POST', body: payload }),
  botInfo: () => request<BotInfo>('/bot/info'),
};
