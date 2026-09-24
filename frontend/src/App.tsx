import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import L from 'leaflet';
import { CalendarDays, LocateFixed, MapPinPlus, RefreshCw } from 'lucide-react';
import { api, errorMessage } from './api/client';
import AddCourtModal from './components/AddCourtModal';
import CourtDetailsSheet from './components/CourtDetailsSheet';
import CreateGameModal from './components/CreateGameModal';
import FiltersBar from './components/FiltersBar';
import MapView from './components/MapView';
import MyGamesSheet from './components/MyGamesSheet';
import NamePromptModal from './components/NamePromptModal';
import PayModal from './components/PayModal';
import PickLocationOverlay from './components/PickLocationOverlay';
import ReportDefectModal from './components/ReportDefectModal';
import { Spinner, Toast, type ToastState } from './components/ui';
import { plural, routeUrl } from './lib/format';
import {
  getIdentity,
  getStartCourtId,
  hapticNotify,
  openExternalLink,
  saveGuestName,
  shareLink,
  useBackButton,
} from './lib/max';
import type { BotInfo, Court, CourtDetail, Game, GameWithCourt, Identity, PayResponse, SportType } from './types';

type ModalKind = 'create-game' | 'report-defect' | 'add-court' | 'my-games' | null;
type IdentityAction = (identity: Identity) => void;

const COURTS_REFRESH_MS = 60_000;

/**
 * Перемещение карты без падений: Leaflet flyTo на контейнере нулевого размера
 * (скрытая вкладка, ещё не отрисованный WebView) вычисляет NaN, поэтому там — setView без анимации.
 */
function moveMap(map: L.Map, center: L.LatLngExpression, zoom: number): void {
  const size = map.getSize();
  try {
    if (size.x > 0 && size.y > 0) {
      map.flyTo(center, zoom, { duration: 0.6 });
      return;
    }
  } catch {
    /* падаем на setView ниже */
  }
  map.setView(center, zoom, { animate: false });
}

export default function App() {
  const [identity, setIdentity] = useState<Identity>(getIdentity);
  const [sport, setSport] = useState<SportType | null>(null);
  const [onlyWithGames, setOnlyWithGames] = useState(false);
  const [onlyRental, setOnlyRental] = useState(false);
  const [payTarget, setPayTarget] = useState<{ game: Game; courtTitle: string } | null>(null);
  const [courts, setCourts] = useState<Court[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [detail, setDetail] = useState<CourtDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [modal, setModal] = useState<ModalKind>(null);
  const [pickMode, setPickMode] = useState(false);
  const [pickedPoint, setPickedPoint] = useState<{ lat: number; lng: number } | null>(null);
  const [pendingAction, setPendingAction] = useState<IdentityAction | null>(null);
  const [busyGameId, setBusyGameId] = useState<number | null>(null);
  const [userLocation, setUserLocation] = useState<[number, number] | null>(null);
  const [locating, setLocating] = useState(false);
  const [toast, setToast] = useState<ToastState | null>(null);
  const [botInfo, setBotInfo] = useState<BotInfo | null>(null);
  const [myGamesCount, setMyGamesCount] = useState(0);
  const [refreshToken, setRefreshToken] = useState(0);
  const [map, setMap] = useState<L.Map | null>(null);

  const startCourtId = useRef<number | null>(getStartCourtId());
  const initialViewDone = useRef(false);
  const detailRequest = useRef(0);
  const courtsRef = useRef<Court[]>([]);
  courtsRef.current = courts;

  const notify = useCallback((message: string, kind: ToastState['kind'] = 'info') => {
    setToast({ id: Date.now(), message, kind });
    if (kind !== 'info') hapticNotify(kind === 'success' ? 'success' : 'error');
  }, []);
  const hideToast = useCallback(() => setToast(null), []);

  // --- Данные ---------------------------------------------------------------------

  const loadCourts = useCallback(async () => {
    try {
      const data = await api.listCourts(sport ? { sport_type: sport } : {});
      setCourts(Array.isArray(data) ? data : []);
      setLoadError(null);
    } catch (err) {
      setCourts([]);
      setLoadError(errorMessage(err));
    } finally {
      setLoading(false);
    }
  }, [sport]);

  useEffect(() => {
    void loadCourts();
    const timer = window.setInterval(() => void loadCourts(), COURTS_REFRESH_MS);
    return () => window.clearInterval(timer);
  }, [loadCourts]);

  const loadDetail = useCallback(
    async (courtId: number) => {
      const requestId = ++detailRequest.current;
      setDetailLoading(true);
      try {
        const data = await api.getCourt(courtId);
        if (requestId === detailRequest.current) setDetail(data);
      } catch (err) {
        if (requestId === detailRequest.current) {
          notify(errorMessage(err), 'error');
          setSelectedId(null);
        }
      } finally {
        if (requestId === detailRequest.current) setDetailLoading(false);
      }
    },
    [notify],
  );

  useEffect(() => {
    if (selectedId === null) {
      detailRequest.current += 1;
      setDetail(null);
      setDetailLoading(false);
      return;
    }
    setDetail((current) => (current?.id === selectedId ? current : null));
    void loadDetail(selectedId);
  }, [selectedId, loadDetail]);

  const loadMyGamesCount = useCallback(async () => {
    try {
      const games = await api.listGames({ user_max_id: identity.maxUserId });
      setMyGamesCount(games.length);
    } catch {
      /* счётчик не критичен */
    }
  }, [identity.maxUserId]);

  useEffect(() => {
    void loadMyGamesCount();
  }, [loadMyGamesCount, refreshToken]);

  useEffect(() => {
    api.botInfo().then(setBotInfo).catch(() => undefined);
  }, []);

  // Если доступ к геопозиции уже выдан — тихо показываем точку пользователя.
  useEffect(() => {
    if (!navigator.geolocation || !navigator.permissions?.query) return;
    navigator.permissions
      .query({ name: 'geolocation' as PermissionName })
      .then((status) => {
        if (status.state !== 'granted') return;
        navigator.geolocation.getCurrentPosition(
          (position) => setUserLocation([position.coords.latitude, position.coords.longitude]),
          () => undefined,
          { maximumAge: 300_000 },
        );
      })
      .catch(() => undefined);
  }, []);

  const refreshAll = useCallback(async () => {
    setRefreshToken((value) => value + 1);
    await Promise.all([loadCourts(), selectedId !== null ? loadDetail(selectedId) : Promise.resolve()]);
  }, [loadCourts, loadDetail, selectedId]);

  // --- Карта ----------------------------------------------------------------------

  /** Центрирует карту так, чтобы маркер не прятался под шторкой (телефон) или панелью (десктоп). */
  const focusPoint = useCallback(
    (lat: number, lng: number) => {
      if (!map) return;
      const zoom = Math.max(map.getZoom() || 12, 15);
      const size = map.getSize();
      if (size.x === 0 || size.y === 0) {
        moveMap(map, [lat, lng], zoom);
        return;
      }
      const desktop = window.matchMedia('(min-width: 768px)').matches;
      const offset = desktop ? L.point(-218, 0) : L.point(0, size.y * 0.26);
      const center = map.unproject(map.project([lat, lng], zoom).add(offset), zoom);
      moveMap(map, center, zoom);
    },
    [map],
  );

  const selectCourt = useCallback(
    (courtId: number, point?: { lat: number; lng: number }) => {
      setModal(null);
      setPickMode(false);
      setSelectedId(courtId);
      const court = courtsRef.current.find((item) => item.id === courtId);
      const target = point ?? (court ? { lat: court.latitude, lng: court.longitude } : null);
      if (target) focusPoint(target.lat, target.lng);
    },
    [focusPoint],
  );

  // Первый показ: площадка из deep link (startapp=court_<id>) или все площадки в кадре.
  useEffect(() => {
    const list = courts || [];
    if (!map || initialViewDone.current || list.length === 0) return;
    initialViewDone.current = true;
    if (startCourtId.current !== null) {
      selectCourt(startCourtId.current);
      return;
    }
    const bounds = L.latLngBounds(list.map((court) => [court.latitude, court.longitude] as [number, number]));
    const size = map.getSize();
    if (size.x > 0 && size.y > 0) {
      map.fitBounds(bounds, { paddingTopLeft: [24, 140], paddingBottomRight: [24, 32], maxZoom: 14 });
    } else {
      map.setView(bounds.getCenter(), 11, { animate: false });
    }
  }, [map, courts, selectCourt]);

  const handleMapClick = useCallback(() => {
    if (!pickMode) setSelectedId(null);
  }, [pickMode]);

  const locate = useCallback(() => {
    if (!navigator.geolocation) {
      notify('Геолокация недоступна на этом устройстве', 'error');
      return;
    }
    setLocating(true);
    navigator.geolocation.getCurrentPosition(
      (position) => {
        const point: [number, number] = [position.coords.latitude, position.coords.longitude];
        setUserLocation(point);
        if (map) moveMap(map, point, Math.max(map.getZoom() || 12, 14));
        setLocating(false);
      },
      () => {
        setLocating(false);
        notify('Не удалось определить местоположение. Разрешите доступ к геопозиции', 'error');
      },
      { enableHighAccuracy: true, timeout: 10_000, maximumAge: 60_000 },
    );
  }, [map, notify]);

  const startPick = () => {
    setSelectedId(null);
    setModal(null);
    setPickMode(true);
  };

  const confirmPick = () => {
    if (!map) return;
    const center = map.getCenter();
    setPickedPoint({ lat: center.lat, lng: center.lng });
    setPickMode(false);
    setModal('add-court');
  };

  // --- Действия пользователя -----------------------------------------------------------

  /** В гостевом режиме сначала спрашиваем имя, затем выполняем действие. */
  const withIdentity = useCallback(
    (action: IdentityAction) => {
      if (identity.name.trim()) action(identity);
      else setPendingAction(() => action);
    },
    [identity],
  );

  const submitName = (name: string) => {
    const updated = saveGuestName(name);
    setIdentity(updated);
    const action = pendingAction;
    setPendingAction(null);
    action?.(updated);
  };

  const joinGame = useCallback(
    (gameId: number) => {
      withIdentity(async (me) => {
        setBusyGameId(gameId);
        try {
          const result = await api.joinGame(gameId, {
            user_max_id: me.maxUserId,
            user_name: me.name,
            username: me.username,
          });
          notify(
            result.confirmed ? '🎉 Состав собран! Бот MAX уведомит всех участников' : result.message,
            result.joined ? 'success' : 'info',
          );
          if (result.joined && result.game.is_paid && result.game.payment_status === 'pending') {
            const court = courtsRef.current.find((c) => c.id === result.game.court_id);
            setPayTarget({ game: result.game, courtTitle: court?.title || '' });
          }
        } catch (err) {
          notify(errorMessage(err), 'error');
        } finally {
          setBusyGameId(null);
          void refreshAll();
        }
      });
    },
    [withIdentity, notify, refreshAll],
  );

  const simulateQuickPay = useCallback(
    (game: Game) => {
      withIdentity(async (me) => {
        setBusyGameId(game.id);
        try {
          const isMember = game.participants?.some((p) => p.user_max_id === me.maxUserId);
          let targetGame = game;
          if (!isMember) {
            const joinResult = await api.joinGame(game.id, {
              user_max_id: me.maxUserId,
              user_name: me.name || 'Гость (Жюри)',
              username: me.username,
            });
            targetGame = joinResult.game;
          }
          const due = targetGame.total_cost - targetGame.collected_amount;
          const payResult = await api.payShare(game.id, {
            user_max_id: me.maxUserId,
            user_name: me.name || 'Гость (Жюри)',
            amount: due,
            payment_method: 'sbp_mock',
          });
          if (payResult.booked) {
            notify(`🎉 Корт забронирован! Safe Split сработал, бронь #${payResult.booking_reference}`, 'success');
          } else {
            notify(payResult.message, 'success');
          }
        } catch (err) {
          notify(errorMessage(err), 'error');
        } finally {
          setBusyGameId(null);
          void refreshAll();
        }
      });
    },
    [withIdentity, notify, refreshAll],
  );

  const leaveGame = useCallback(
    async (gameId: number) => {
      setBusyGameId(gameId);
      try {
        const result = await api.leaveGame(gameId, {
          user_max_id: identity.maxUserId,
          user_name: identity.name || 'Игрок',
          username: identity.username,
        });
        notify(result.message, 'info');
      } catch (err) {
        notify(errorMessage(err), 'error');
      } finally {
        setBusyGameId(null);
        void refreshAll();
      }
    },
    [identity, notify, refreshAll],
  );

  const handleGameCreated = useCallback(
    (game: GameWithCourt) => {
      setModal(null);
      if (game.is_paid) {
        // Платный сбор: организатор сразу вносит свою долю на эскроу-счёт.
        notify(`Сбор создан, слот зарезервирован. Эскроу-счёт #${game.escrow_account_id}`, 'success');
        setPayTarget({ game, courtTitle: game.court.title });
      } else {
        notify('Сбор создан! Бот сообщит, когда команда соберётся', 'success');
      }
      void refreshAll();
    },
    [notify, refreshAll],
  );

  const openPay = useCallback(
    (game: Game, courtTitle: string) => withIdentity(() => setPayTarget({ game, courtTitle })),
    [withIdentity],
  );

  const handlePaid = useCallback(
    (result: PayResponse) => {
      if (result.booked) {
        notify(`🎉 Корт забронирован! Номер брони #${result.booking_reference}`, 'success');
      } else {
        notify(result.message, 'success');
      }
      void refreshAll();
    },
    [notify, refreshAll],
  );

  const handleDefectReported = useCallback(() => {
    void refreshAll();
  }, [refreshAll]);

  const handleCourtCreated = useCallback(
    (court: Court) => {
      setPickedPoint(null);
      setCourts((current) => [...(current || []).filter((item) => item.id !== court.id), court]);
      courtsRef.current = [...(courtsRef.current || []), court];
      notify('Площадка добавлена на карту. Спасибо!', 'success');
      selectCourt(court.id, { lat: court.latitude, lng: court.longitude });
    },
    [notify, selectCourt],
  );

  const openCourtFromGame = useCallback(
    (game: GameWithCourt) => selectCourt(game.court_id, { lat: game.court.latitude, lng: game.court.longitude }),
    [selectCourt],
  );

  const shareCourt = useCallback(
    async (court: Court) => {
      const link = botInfo?.username
        ? `https://max.ru/${botInfo.username}?startapp=court_${court.id}`
        : `${window.location.origin}/?court=${court.id}`;
      const result = await shareLink(`${court.title}: площадка в MAX Стрит`, link);
      if (result === 'copied') notify('Ссылка скопирована', 'success');
      else if (result === 'failed') notify('Не удалось поделиться ссылкой', 'error');
    },
    [botInfo, notify],
  );

  // --- «Назад» (кнопка MAX и Escape) -----------------------------------------------------

  const backVisible = modal !== null || pendingAction !== null || payTarget !== null || pickMode || selectedId !== null;
  const handleBack = useCallback(() => {
    if (pendingAction) setPendingAction(null);
    else if (payTarget) setPayTarget(null);
    else if (modal) setModal(null);
    else if (pickMode) setPickMode(false);
    else setSelectedId(null);
  }, [pendingAction, payTarget, modal, pickMode]);
  useBackButton(backVisible, handleBack);

  // --- Отрисовка -----------------------------------------------------------------------

  const visibleCourts = useMemo(
    () =>
      (courts || []).filter(
        (court) => (!onlyWithGames || court.active_games_today > 0) && (!onlyRental || court.is_commercial),
      ),
    [courts, onlyWithGames, onlyRental],
  );
  const gamesToday = useMemo(() => (courts || []).reduce((sum, court) => sum + court.active_games_today, 0), [courts]);
  const selectedCourt: Court | null =
    detail && detail.id === selectedId ? detail : ((courts || []).find((court) => court.id === selectedId) ?? null);

  const courtsCount = courts?.length ?? 0;
  const subtitle = loading
    ? 'Загружаем площадки…'
    : `${courtsCount} ${plural(courtsCount, ['площадка', 'площадки', 'площадок'])} · ${gamesToday} ${plural(gamesToday, [
        'сбор',
        'сбора',
        'сборов',
      ])} сегодня`;

  return (
    <div className="relative h-full w-full overflow-hidden">
      <MapView
        courts={visibleCourts}
        selectedId={selectedId}
        activeSport={sport}
        userLocation={userLocation}
        onSelect={selectCourt}
        onMapReady={setMap}
        onMapClick={handleMapClick}
      />

      <div className="pt-safe pointer-events-none absolute inset-x-0 top-0 z-[1100]">
        <div className="pointer-events-auto mx-3 flex items-center gap-2 md:max-w-[420px]">
          <div className="glass flex min-w-0 flex-1 items-center gap-3 rounded-2xl px-3 py-2 shadow-float">
            <img src="/favicon.svg" alt="" className="h-9 w-9 shrink-0 rounded-xl" />
            <div className="min-w-0 flex-1">
              <h1 className="truncate text-[15px] font-bold leading-tight">MAX Стрит</h1>
              <p className="truncate text-xs text-slate-500 dark:text-slate-400">{subtitle}</p>
            </div>
          </div>
          <button
            type="button"
            onClick={() => setModal('my-games')}
            aria-label="Мои сборы"
            title="Мои сборы"
            className="glass relative flex h-[52px] w-[52px] shrink-0 items-center justify-center rounded-2xl shadow-float transition active:scale-95"
          >
            <CalendarDays className="h-6 w-6 text-accent" />
            {myGamesCount > 0 && (
              <span className="absolute -right-1 -top-1 flex h-5 min-w-[20px] items-center justify-center rounded-full bg-accent px-1 text-[11px] font-bold text-white ring-2 ring-[#F2F3F7] dark:ring-[#0F1115]">
                {myGamesCount}
              </span>
            )}
          </button>
        </div>
        <FiltersBar
          className="pointer-events-auto mt-2"
          sport={sport}
          onSportChange={setSport}
          onlyWithGames={onlyWithGames}
          onOnlyWithGamesChange={setOnlyWithGames}
          onlyRental={onlyRental}
          onOnlyRentalChange={setOnlyRental}
        />
      </div>

      {!pickMode && (
        <div
          className={`absolute right-3 z-[1100] flex-col gap-2 md:!bottom-[112px] ${selectedCourt ? 'hidden md:flex' : 'flex'}`}
          style={{ bottom: 'calc(max(env(safe-area-inset-bottom), 16px) + 8px)' }}
        >
          <button
            type="button"
            onClick={startPick}
            aria-label="Добавить площадку"
            title="Добавить площадку"
            className="glass flex h-[52px] w-[52px] items-center justify-center rounded-2xl shadow-float transition active:scale-95"
          >
            <MapPinPlus className="h-6 w-6 text-accent" />
          </button>
          <button
            type="button"
            onClick={locate}
            aria-label="Моё местоположение"
            title="Моё местоположение"
            className="glass flex h-[52px] w-[52px] items-center justify-center rounded-2xl shadow-float transition active:scale-95"
          >
            {locating ? <Spinner className="h-6 w-6 text-accent" /> : <LocateFixed className="h-6 w-6 text-accent" />}
          </button>
        </div>
      )}

      {loading && courts.length === 0 && (
        <div className="glass absolute left-1/2 top-1/2 z-[1050] flex -translate-x-1/2 -translate-y-1/2 items-center gap-3 rounded-2xl px-5 py-4 shadow-float">
          <Spinner className="h-5 w-5 text-accent" />
          <span className="text-sm font-medium">Загружаем карту площадок…</span>
        </div>
      )}

      {!loading && loadError && courts.length === 0 && (
        <div className="absolute inset-x-4 top-1/3 z-[1150] mx-auto max-w-sm rounded-3xl bg-white p-5 text-center shadow-float dark:bg-[#1C1E24]">
          <p className="font-semibold">Не удалось загрузить площадки</p>
          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">{loadError}</p>
          <button
            type="button"
            className="btn-primary mt-4 w-full"
            onClick={() => {
              setLoading(true);
              void loadCourts();
            }}
          >
            <RefreshCw className="h-5 w-5" />
            Повторить
          </button>
        </div>
      )}

      {!loading && !loadError && visibleCourts.length === 0 && (
        <div className="pointer-events-none absolute inset-x-0 top-[150px] z-[1050] flex justify-center px-4">
          <div className="glass rounded-2xl px-4 py-3 text-sm font-medium shadow-float">Нет площадок по выбранным фильтрам</div>
        </div>
      )}

      {selectedCourt && (
        <CourtDetailsSheet
          key={selectedCourt.id}
          court={selectedCourt}
          detail={detail && detail.id === selectedCourt.id ? detail : null}
          loading={detailLoading}
          identity={identity}
          busyGameId={busyGameId}
          onClose={() => setSelectedId(null)}
          onCreateGame={() => withIdentity(() => setModal('create-game'))}
          onReportDefect={() => setModal('report-defect')}
          onJoin={joinGame}
          onLeave={(gameId) => void leaveGame(gameId)}
          onPay={(game) => openPay(game, selectedCourt.title)}
          onQuickSimulatePay={simulateQuickPay}
          onRoute={() => openExternalLink(routeUrl(selectedCourt.latitude, selectedCourt.longitude))}
          onShare={() => void shareCourt(selectedCourt)}
        />
      )}

      {pickMode && <PickLocationOverlay onCancel={() => setPickMode(false)} onConfirm={confirmPick} />}

      {modal === 'create-game' && selectedCourt && (
        <CreateGameModal
          court={selectedCourt}
          identity={identity}
          onClose={() => setModal(null)}
          onCreated={handleGameCreated}
        />
      )}
      {modal === 'report-defect' && selectedCourt && (
        <ReportDefectModal
          court={selectedCourt}
          identity={identity}
          onClose={() => setModal(null)}
          onReported={handleDefectReported}
        />
      )}
      {modal === 'add-court' && pickedPoint && (
        <AddCourtModal point={pickedPoint} onClose={() => setModal(null)} onCreated={handleCourtCreated} />
      )}
      {modal === 'my-games' && (
        <MyGamesSheet
          identity={identity}
          botInfo={botInfo}
          refreshToken={refreshToken}
          busyGameId={busyGameId}
          onClose={() => setModal(null)}
          onOpenCourt={openCourtFromGame}
          onLeave={(gameId) => void leaveGame(gameId)}
          onPay={openPay}
        />
      )}
      {payTarget && (
        <PayModal
          key={payTarget.game.id}
          game={payTarget.game}
          courtTitle={payTarget.courtTitle}
          identity={identity}
          onClose={() => setPayTarget(null)}
          onPaid={handlePaid}
        />
      )}
      {pendingAction && <NamePromptModal onClose={() => setPendingAction(null)} onSubmit={submitName} />}

      <Toast toast={toast} onHide={hideToast} />
    </div>
  );
}
