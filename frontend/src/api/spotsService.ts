import { rawRequest, ApiError, buildUrl } from './client';
import {
  FALLBACK_COURTS,
  getFallbackCourts,
  getFallbackDetail,
  getFallbackSlots,
  joinFallbackGame,
  leaveFallbackGame,
  reportFallbackDefect,
  updateFallbackGameToBooked,
} from '../lib/mockData';
import type {
  BotInfo,
  CheckInPayload,
  CheckInResponse,
  Court,
  CourtDetail,
  CreateCourtPayload,
  CreateGamePayload,
  Defect,
  EscrowTransaction,
  GameWithCourt,
  JoinResponse,
  LeaveResponse,
  PayPayload,
  PayResponse,
  PlayerPayload,
  ReportDefectPayload,
  Slot,
  SportType,
} from '../types';

/**
 * Уходить в автономный режим можно только при отсутствии связи (сеть, CORS, таймаут, 5xx).
 * Ответ сервера 4xx («мест нет», «ваша доля: …») — это отказ, а не офлайн: его нужно показать
 * пользователю, иначе действие будет «выполнено» на моковых данных и молча потеряется.
 */
function isOfflineError(err: unknown): boolean {
  return !(err instanceof ApiError) || err.isNetworkOrTimeout;
}

type FallbackListener = (isFallback: boolean, message: string) => void;

class SpotsService {
  private isFallbackMode = false;
  private listeners: Set<FallbackListener> = new Set();
  private notifiedFallback = false;

  public subscribeFallback(listener: FallbackListener): () => void {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  private triggerFallback(reason: string) {
    this.isFallbackMode = true;
    if (!this.notifiedFallback) {
      this.notifiedFallback = true;
      if (import.meta.env.DEV) {
        console.warn('[SpotsService Fallback activated]', reason);
      }
      const msg = 'Сервер недоступен (ошибка сети/CORS/таймаут). Включен автономный режим с проверенными данными СПб.';
      this.listeners.forEach((cb) => cb(true, msg));
    }
  }

  public get isOffline(): boolean {
    return this.isFallbackMode;
  }

  async listCourts(params: { sport_type?: SportType } = {}): Promise<Court[]> {
    try {
      const data = await rawRequest<Court[]>('/courts', { query: params });
      if (Array.isArray(data) && data.length > 0) {
        return data;
      }
      this.triggerFallback('Пустой список площадок от API');
      return getFallbackCourts(params.sport_type);
    } catch (err) {
      this.triggerFallback((err as Error)?.message || 'Ошибка сети');
      return getFallbackCourts(params.sport_type);
    }
  }

  async getCourt(id: number): Promise<CourtDetail> {
    try {
      const data = await rawRequest<CourtDetail>(`/courts/${id}`);
      if (data && data.id) {
        return data;
      }
      this.triggerFallback('Не найден корт в API');
      const fallback = getFallbackDetail(id);
      if (!fallback) throw new ApiError(`Площадка #${id} не найдена`, 404);
      return fallback;
    } catch (err) {
      this.triggerFallback((err as Error)?.message || 'Ошибка сети');
      const fallback = getFallbackDetail(id);
      if (!fallback) throw new ApiError(`Площадка #${id} не найдена`, 404);
      return fallback;
    }
  }

  async listSpots(params: { sport_type?: SportType } = {}): Promise<Court[]> {
    return this.listCourts(params);
  }

  async getSpot(id: number): Promise<CourtDetail> {
    return this.getCourt(id);
  }

  async getSlots(courtId: number, date: string): Promise<Slot[]> {
    try {
      return await rawRequest<Slot[]>(`/courts/${courtId}/slots`, { query: { date } });
    } catch (err) {
      this.triggerFallback((err as Error)?.message || 'Ошибка сети');
      return getFallbackSlots(courtId, date);
    }
  }

  async payShare(gameId: number, payload: PayPayload): Promise<PayResponse> {
    try {
      return await rawRequest<PayResponse>(`/games/${gameId}/pay`, { method: 'POST', body: payload });
    } catch (err) {
      if (!isOfflineError(err)) throw err;
      this.triggerFallback((err as Error)?.message || 'Ошибка сети');
      // Отрабатываем локальный Safe Split на моковых данных
      const updatedGame = updateFallbackGameToBooked(gameId, {
        user_max_id: payload.user_max_id || 'guest_jury',
        user_name: payload.user_name || 'Гость (Жюри)',
      });
      if (updatedGame) {
        const court = FALLBACK_COURTS.find((c) => c.id === updatedGame.court_id);
        const gameWithCourt: GameWithCourt = {
          ...updatedGame,
          court: {
            id: updatedGame.court_id,
            title: court?.title || 'Спортивный центр «Локомотив» (Мини-футбол)',
            address: court?.address || 'ул. Константина Заслонова, 23/4, Санкт-Петербург',
            latitude: court?.latitude || 59.9176,
            longitude: court?.longitude || 30.3491,
          },
        };
        const transaction: EscrowTransaction = {
          reference: 'TX-SAFE-SPLIT-701',
          kind: 'deposit',
          amount: payload.amount ?? 500,
          method: 'sbp_mock',
          user_max_id: payload.user_max_id,
          created_at: new Date().toISOString(),
        };
        return {
          game: gameWithCourt,
          booked: true,
          booking_reference: 'BOOK-LOKO-701',
          transaction,
          message: '🎉 Корт забронирован! Safe Split сработал, бронь #BOOK-LOKO-701',
        };
      }
      throw err;
    }
  }

  async checkinGame(gameId: number, payload: CheckInPayload): Promise<CheckInResponse> {
    try {
      return await rawRequest<CheckInResponse>(`/games/${gameId}/checkin`, { method: 'POST', body: payload });
    } catch (err) {
      if (!isOfflineError(err)) throw err;
      this.triggerFallback((err as Error)?.message || 'Ошибка сети');
      throw err;
    }
  }

  async createCourt(payload: CreateCourtPayload): Promise<Court> {
    try {
      return await rawRequest<Court>('/courts', { method: 'POST', body: payload });
    } catch (err) {
      if (!isOfflineError(err)) throw err;
      this.triggerFallback((err as Error)?.message || 'Ошибка сети');
      const newCourt: Court = {
        id: Date.now(),
        title: payload.title,
        sport_types: payload.sport_types,
        address: payload.address,
        latitude: payload.latitude,
        longitude: payload.longitude,
        surface_type: payload.surface_type,
        has_lighting: payload.has_lighting,
        is_indoor: false,
        is_commercial: false,
        rating: 5.0,
        description: payload.description || 'Новая площадка',
        website: payload.website ?? null,
        active_games_today: 0,
        price_from: null,
      };
      FALLBACK_COURTS.unshift(newCourt);
      return newCourt;
    }
  }

  async listGames(params: { court_id?: number; user_max_id?: string; sport_type?: SportType } = {}): Promise<GameWithCourt[]> {
    try {
      return await rawRequest<GameWithCourt[]>('/games', { query: params });
    } catch (err) {
      this.triggerFallback((err as Error)?.message || 'Ошибка сети');
      // Собираем игры со всех фолбэк-площадок
      const games: GameWithCourt[] = [];
      for (const court of FALLBACK_COURTS) {
        if (params.court_id && court.id !== params.court_id) continue;
        if (params.sport_type && !court.sport_types.includes(params.sport_type)) continue;

        const detail = getFallbackDetail(court.id);
        if (detail && detail.games) {
          for (const g of detail.games) {
            if (params.user_max_id && !g.participants.some((p) => p.user_max_id === params.user_max_id)) {
              continue;
            }
            games.push({
              ...g,
              court: {
                id: court.id,
                title: court.title,
                address: court.address,
                latitude: court.latitude,
                longitude: court.longitude,
              },
            });
          }
        }
      }
      return games;
    }
  }

  async createGame(payload: CreateGamePayload): Promise<GameWithCourt> {
    try {
      return await rawRequest<GameWithCourt>('/games', { method: 'POST', body: payload });
    } catch (err) {
      if (!isOfflineError(err)) throw err;
      this.triggerFallback((err as Error)?.message || 'Ошибка сети');
      const court = FALLBACK_COURTS.find((c) => c.id === payload.court_id);
      const detail = getFallbackDetail(payload.court_id);
      const newGame: GameWithCourt = {
        id: Date.now(),
        court_id: payload.court_id,
        creator_max_id: payload.creator_max_id,
        sport_type: payload.sport_type,
        start_time: payload.start_time || new Date().toISOString(),
        required_players: payload.required_players,
        current_players: 1,
        status: 'recruiting',
        status_label: 'Идёт набор',
        comment: payload.comment || '',
        created_at: new Date().toISOString(),
        participants: [
          {
            user_max_id: payload.creator_max_id,
            user_name: payload.creator_name || 'Организатор',
            joined_at: new Date().toISOString(),
            has_paid: false,
            paid_amount: 0,
            paid_at: null,
          },
        ],
        spots_left: payload.required_players - 1,
        slot_id: payload.slot_id ?? null,
        slot: null,
        escrow_account_id: null,
        total_cost: 0,
        collected_amount: 0,
        payment_status: 'funded',
        payment_status_label: null,
        payment_deadline: null,
        booking_reference: null,
        is_paid: false,
        share_amount: 0,
        paid_count: 0,
        court: {
          id: payload.court_id,
          title: court?.title || 'Спортивная площадка',
          address: court?.address || '',
          latitude: court?.latitude || 59.9343,
          longitude: court?.longitude || 30.3351,
        },
      };
      if (detail) {
        detail.games.unshift(newGame);
      }
      return newGame;
    }
  }

  async joinGame(id: number, player: PlayerPayload): Promise<JoinResponse> {
    try {
      return await rawRequest<JoinResponse>(`/games/${id}/join`, { method: 'POST', body: player });
    } catch (err) {
      if (!isOfflineError(err)) throw err;
      this.triggerFallback((err as Error)?.message || 'Ошибка сети');
      const res = joinFallbackGame(id, player);
      if (res) {
        const court = FALLBACK_COURTS.find((c) => c.id === res.game.court_id);
        const gameWithCourt: GameWithCourt = {
          ...res.game,
          court: {
            id: res.game.court_id,
            title: court?.title || 'Спортивная площадка',
            address: court?.address || '',
            latitude: court?.latitude || 59.9343,
            longitude: court?.longitude || 30.3351,
          },
        };
        return {
          game: gameWithCourt,
          joined: res.joined,
          confirmed: res.confirmed,
          message: res.confirmed ? '🎉 Состав собран! Бот MAX уведомит всех участников' : 'Вы присоединились к сбору',
        };
      }
      throw err;
    }
  }

  async leaveGame(id: number, player: PlayerPayload): Promise<LeaveResponse> {
    try {
      return await rawRequest<LeaveResponse>(`/games/${id}/leave`, { method: 'POST', body: player });
    } catch (err) {
      if (!isOfflineError(err)) throw err;
      this.triggerFallback((err as Error)?.message || 'Ошибка сети');
      const res = leaveFallbackGame(id, player);
      if (res) {
        const court = FALLBACK_COURTS.find((c) => c.id === res.game.court_id);
        const gameWithCourt: GameWithCourt = {
          ...res.game,
          court: {
            id: res.game.court_id,
            title: court?.title || 'Спортивная площадка',
            address: court?.address || '',
            latitude: court?.latitude || 59.9343,
            longitude: court?.longitude || 30.3351,
          },
        };
        return {
          game: gameWithCourt,
          message: 'Вы покинули сбор',
        };
      }
      throw err;
    }
  }

  async reportDefect(courtId: number, payload: ReportDefectPayload): Promise<Defect> {
    try {
      return await rawRequest<Defect>(`/courts/${courtId}/defects`, { method: 'POST', body: payload });
    } catch (err) {
      if (!isOfflineError(err)) throw err;
      this.triggerFallback((err as Error)?.message || 'Ошибка сети');
      return reportFallbackDefect(courtId, payload);
    }
  }

  async botInfo(): Promise<BotInfo> {
    try {
      return await rawRequest<BotInfo>('/bot/info');
    } catch {
      return {
        enabled: true,
        connected: false,
        mode: 'polling',
        name: 'Хакатон МАХ 69',
        username: 't69_hakaton_max_bot',
        deep_link: 'https://max.ru/t69_hakaton_max_bot?startapp',
        miniapp_url: 'https://max-street.pages.dev',
      };
    }
  }

  subscribeGameEvents(gameId: number, onUpdate: (game: GameWithCourt) => void): () => void {
    if (this.isFallbackMode || typeof EventSource === 'undefined') {
      return () => {};
    }
    try {
      const url = buildUrl(`/games/${gameId}/events`);
      const es = new EventSource(url);
      const listener = (event: MessageEvent) => {
        try {
          const data = JSON.parse(event.data);
          if (data && data.id) {
            onUpdate(data);
          }
        } catch {
          // ignore parsing error
        }
      };
      es.addEventListener('game_updated', listener);
      es.addEventListener('game_created', listener);
      return () => {
        es.removeEventListener('game_updated', listener);
        es.removeEventListener('game_created', listener);
        es.close();
      };
    } catch {
      return () => {};
    }
  }
}

export const spotsService = new SpotsService();
