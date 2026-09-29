import { useEffect, useRef, useState, type ReactNode, type TouchEvent } from 'react';
import {
  CalendarDays,
  CircleCheck,
  FileText,
  Globe,
  Layers,
  Lightbulb,
  LightbulbOff,
  MapPin,
  Navigation,
  Plus,
  Route,
  Share2,
  ShieldCheck,
  Star,
  Trees,
  Warehouse,
  Wrench,
  X,
} from 'lucide-react';
import { api } from '../api/client';
import { DEFECT_STATUS_STYLES, SPORTS, SURFACES } from '../lib/constants';
import {
  calculateDistanceMeters,
  formatDistance,
  formatOfficialAppealText,
  formatRub,
  hexToRgba,
  timeAgo,
} from '../lib/format';
import { openExternalLink } from '../lib/max';
import { reviewsStore, type CourtReview } from '../lib/reviewsStore';
import type { Court, CourtDetail, Defect, Game, Identity } from '../types';
import GameCard from './GameCard';
import { IconButton, SectionTitle } from './ui';

/** «https://www.sportclub.ru/about/» → «sportclub.ru/about» */
function websiteLabel(url: string): string {
  return url.replace(/^https?:\/\//, '').replace(/^www\./, '').replace(/\/$/, '');
}

interface CourtDetailsSheetProps {
  court: Court;
  detail: CourtDetail | null;
  loading: boolean;
  identity: Identity;
  busyGameId: number | null;
  userLocation?: [number, number] | null;
  onClose: () => void;
  onCreateGame: () => void;
  onReportDefect: () => void;
  onAddReview: () => void;
  onJoin: (gameId: number) => void;
  onLeave: (gameId: number) => void;
  onPay: (game: Game) => void;
  onQuickSimulatePay?: (game: Game) => void;
  onRoute: () => void;
  onShare: () => void;
  onNotify?: (message: string, kind?: 'info' | 'success' | 'error') => void;
  onGameUpdated?: (game: Game) => void;
  reviewsVersion?: number;
}

function InfoTile({ icon, label, value }: { icon: ReactNode; label: string; value: string }) {
  return (
    <div className="flex items-center gap-3 rounded-2xl bg-white px-3 py-2.5 dark:bg-[#1C1E24]">
      <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-slate-100 text-slate-600 dark:bg-white/10 dark:text-slate-300">
        {icon}
      </span>
      <span className="min-w-0">
        <span className="block text-xs text-slate-500 dark:text-slate-400">{label}</span>
        <span className="block truncate text-sm font-semibold">{value}</span>
      </span>
    </div>
  );
}

function GameSkeleton() {
  return (
    <div className="card mt-2 animate-pulse">
      <div className="flex gap-3">
        <div className="h-11 w-11 rounded-2xl bg-slate-200 dark:bg-white/10" />
        <div className="flex-1 space-y-2">
          <div className="h-4 w-2/3 rounded bg-slate-200 dark:bg-white/10" />
          <div className="h-3 w-1/3 rounded bg-slate-200 dark:bg-white/10" />
        </div>
      </div>
      <div className="mt-4 h-2 rounded bg-slate-200 dark:bg-white/10" />
      <div className="mt-4 h-12 rounded-2xl bg-slate-200 dark:bg-white/10" />
    </div>
  );
}

export default function CourtDetailsSheet({
  court,
  detail,
  loading,
  identity,
  busyGameId,
  userLocation,
  onClose,
  onCreateGame,
  onReportDefect,
  onAddReview,
  onJoin,
  onLeave,
  onPay,
  onQuickSimulatePay,
  onRoute,
  onShare,
  onNotify,
  onGameUpdated,
  reviewsVersion = 0,
}: CourtDetailsSheetProps) {
  const [expanded, setExpanded] = useState(false);
  const touchStartY = useRef<number | null>(null);
  const info = detail ?? court;
  const games = Array.isArray(detail?.games) ? detail.games : [];
  const defects = Array.isArray(detail?.defects) ? detail.defects : [];
  const openDefects = (defects || []).filter((d) => d.status !== 'resolved');
  const resolvedDefects = (defects || []).filter((d) => d.status === 'resolved');

  const [reviews, setReviews] = useState<CourtReview[]>(() => reviewsStore.getCourtReviews(court.id));

  useEffect(() => {
    setReviews(reviewsStore.getCourtReviews(court.id));
  }, [court.id, reviewsVersion]);

  const distance = userLocation
    ? calculateDistanceMeters(userLocation[0], userLocation[1], info.latitude, info.longitude)
    : info.distance_meters;

  useEffect(() => {
    if (!games.length || !onGameUpdated) return undefined;
    const unsubs = games.map((g) =>
      api.subscribeGameEvents(g.id, (updatedGame) => {
        onGameUpdated(updatedGame);
      })
    );
    return () => {
      unsubs.forEach((unsub) => unsub());
    };
  }, [games, onGameUpdated]);

  const copyAppeal = (defect: Defect) => {
    const text = formatOfficialAppealText(info.title, info.address, defect.defect_label, defect.description);
    navigator.clipboard
      .writeText(text)
      .then(() => {
        onNotify?.('📋 Текст заявления для «Наш СПб» / Госуслуг скопирован в буфер!', 'success');
      })
      .catch(() => {
        onNotify?.('Не удалось скопировать текст в буфер', 'error');
      });
  };

  const onTouchStart = (event: TouchEvent) => {
    touchStartY.current = event.touches[0]?.clientY ?? null;
  };
  const onTouchEnd = (event: TouchEvent) => {
    if (touchStartY.current === null) return;
    const delta = (event.changedTouches[0]?.clientY ?? touchStartY.current) - touchStartY.current;
    touchStartY.current = null;
    if (delta > 60) {
      if (expanded) setExpanded(false);
      else onClose();
    } else if (delta < -40) {
      setExpanded(true);
    }
  };

  const averageRating =
    reviews.length > 0
      ? reviews.reduce((sum, r) => sum + r.rating, 0) / reviews.length
      : info.rating;

  return (
    <section
      aria-label={`Площадка ${info.title}`}
      className={`fixed inset-x-0 bottom-0 z-[1200] flex animate-slide-up flex-col rounded-t-3xl bg-[#F2F3F7] shadow-sheet transition-[max-height] duration-300 dark:bg-[#15171C] md:bottom-4 md:left-4 md:right-auto md:top-[136px] md:max-h-none md:w-[420px] md:rounded-3xl ${
        expanded ? 'max-h-[92dvh]' : 'max-h-[64dvh]'
      }`}
    >
      <div
        className="flex cursor-grab justify-center pb-1 pt-2 md:hidden"
        onClick={() => setExpanded((value) => !value)}
        onTouchStart={onTouchStart}
        onTouchEnd={onTouchEnd}
        role="button"
        aria-label={expanded ? 'Свернуть' : 'Развернуть'}
      >
        <span className="h-1.5 w-10 rounded-full bg-slate-300 dark:bg-white/20" />
      </div>

      <header className="flex items-start gap-3 px-5 pb-3 pt-2 md:pt-5" onTouchStart={onTouchStart} onTouchEnd={onTouchEnd}>
        <div className="min-w-0 flex-1">
          <div className="mb-1.5 flex flex-wrap gap-1.5">
            {info.sport_types.map((sport) => (
              <span
                key={sport}
                className="rounded-full px-2.5 py-1 text-xs font-semibold"
                style={{ background: hexToRgba(SPORTS[sport].color, 0.14), color: SPORTS[sport].color }}
              >
                {SPORTS[sport].emoji} {SPORTS[sport].label}
              </span>
            ))}
          </div>
          <h2 className="text-xl font-bold leading-tight">{info.title}</h2>
          <div className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1 text-sm text-slate-500 dark:text-slate-400">
            <span className="flex items-start gap-1.5">
              <MapPin className="mt-0.5 h-4 w-4 shrink-0" />
              {info.address}
            </span>
            {distance !== undefined && (
              <span className="inline-flex items-center gap-1 rounded-full bg-emerald-100/90 px-2 py-0.5 text-xs font-semibold text-emerald-800 dark:bg-emerald-400/15 dark:text-emerald-300">
                <Navigation className="h-3 w-3" />
                {formatDistance(distance)} от вас
              </span>
            )}
          </div>
        </div>
        <IconButton label="Закрыть" onClick={onClose}>
          <X className="h-5 w-5" />
        </IconButton>
      </header>

      <div className="scroll-area pb-safe flex-1 overflow-y-auto px-4">
        <div className="grid grid-cols-2 gap-2">
          <InfoTile icon={<Layers className="h-5 w-5" />} label="Покрытие" value={SURFACES[info.surface_type] ?? info.surface_type} />
          <InfoTile
            icon={info.has_lighting ? <Lightbulb className="h-5 w-5 text-amber-500" /> : <LightbulbOff className="h-5 w-5" />}
            label="Освещение"
            value={info.has_lighting ? 'Есть' : 'Нет'}
          />
          <div
            onClick={onAddReview}
            role="button"
            className="flex items-center gap-3 rounded-2xl bg-white px-3 py-2.5 dark:bg-[#1C1E24] cursor-pointer hover:bg-slate-50 dark:hover:bg-white/5 transition active:scale-[0.98]"
            title="Нажмите, чтобы оценить площадку"
          >
            <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-amber-50 text-amber-500 dark:bg-amber-400/10 dark:text-amber-400">
              <Star className="h-5 w-5 fill-amber-400 text-amber-400" />
            </span>
            <span className="min-w-0 flex-1">
              <div className="flex items-center justify-between">
                <span className="block text-xs text-slate-500 dark:text-slate-400">Рейтинг</span>
                <span className="text-[10px] font-semibold text-accent hover:underline">+ отзыв</span>
              </div>
              <span className="block truncate text-sm font-semibold">
                {averageRating > 0 ? `${averageRating.toFixed(1)} ⭐ (${reviews.length})` : 'Новая ⭐'}
              </span>
            </span>
          </div>
          <InfoTile
            icon={info.is_indoor ? <Warehouse className="h-5 w-5" /> : <Trees className="h-5 w-5 text-emerald-600" />}
            label="Тип"
            value={info.is_indoor ? 'Крытая' : 'Открытая'}
          />
        </div>

        {info.is_commercial && (
          <div className="mt-3 flex gap-3 rounded-2xl bg-emerald-600 px-4 py-3 text-white">
            <ShieldCheck className="mt-0.5 h-5 w-5 shrink-0" />
            <div className="text-sm">
              <p className="font-semibold">
                Коммерческий корт · аренда {info.price_from ? `от ${formatRub(info.price_from)}` : 'по расписанию'} за 90 мин
              </p>
              <p className="mt-0.5 text-white/85">
                Оплата через безопасный сбор MAX Escrow: каждый вносит свою долю, корт выкупается при 100%.
              </p>
            </div>
          </div>
        )}

        {info.description && (
          <p className="mt-3 px-1 text-[15px] leading-relaxed text-slate-700 dark:text-slate-300">{info.description}</p>
        )}

        {info.website && (
          <a
            href={info.website}
            target="_blank"
            rel="noopener noreferrer"
            onClick={(event) => {
              event.preventDefault();
              openExternalLink(info.website!);
            }}
            className="mt-3 flex items-center gap-3 rounded-2xl bg-white px-3 py-2.5 transition hover:bg-slate-50 active:scale-[0.98] dark:bg-[#1C1E24] dark:hover:bg-white/5"
          >
            <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-sky-50 text-sky-600 dark:bg-sky-400/10 dark:text-sky-400">
              <Globe className="h-5 w-5" />
            </span>
            <span className="min-w-0 flex-1">
              <span className="block text-xs text-slate-500 dark:text-slate-400">Сайт организации</span>
              <span className="block truncate text-sm font-semibold text-accent">{websiteLabel(info.website)}</span>
            </span>
          </a>
        )}

        <div className="mt-4 flex gap-2">
          <button
            type="button"
            className={`btn-primary flex-1 ${info.is_commercial ? 'bg-emerald-600 hover:bg-emerald-700' : ''}`}
            onClick={onCreateGame}
          >
            <Plus className="h-5 w-5" />
            {info.is_commercial ? 'Выбрать слот и собрать' : 'Создать сбор'}
          </button>
          <button type="button" className="btn-secondary w-12 px-0" onClick={onRoute} aria-label="Маршрут" title="Маршрут">
            <Route className="h-5 w-5" />
          </button>
          <button type="button" className="btn-secondary w-12 px-0" onClick={onShare} aria-label="Поделиться" title="Поделиться">
            <Share2 className="h-5 w-5" />
          </button>
        </div>

        <SectionTitle title="Сборы" count={games.length} />
        {loading && !detail ? (
          <GameSkeleton />
        ) : games.length === 0 ? (
          <div className="card mt-2 flex flex-col items-center py-6 text-center">
            <CalendarDays className="h-9 w-9 text-slate-300 dark:text-slate-600" />
            <p className="mt-2 font-semibold">Пока никто не собирается</p>
            <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
              Создайте сбор: бот позовёт игроков и сообщит, когда команда будет в сборе
            </p>
          </div>
        ) : (
          games.map((game) => (
            <GameCard
              key={game.id}
              game={game}
              court={info}
              identity={identity}
              busy={busyGameId === game.id}
              onJoin={() => onJoin(game.id)}
              onLeave={() => onLeave(game.id)}
              onPay={() => onPay(game)}
              onQuickSimulatePay={onQuickSimulatePay ? () => onQuickSimulatePay(game) : undefined}
            />
          ))
        )}

        <SectionTitle title="Состояние площадки" />
        {detail && openDefects.length === 0 && (
          <div className="card mt-2 flex items-center gap-3">
            <CircleCheck className="h-6 w-6 shrink-0 text-emerald-500" />
            <p className="text-sm text-slate-600 dark:text-slate-300">
              Открытых заявок о неисправностях нет
              {resolvedDefects.length > 0 && ` · устранено: ${resolvedDefects.length}`}
            </p>
          </div>
        )}
        {openDefects.map((defect) => (
          <div key={defect.id} className="card mt-2">
            <div className="flex items-start justify-between gap-2">
              <p className="font-semibold">{defect.defect_label}</p>
              <span className={`shrink-0 rounded-full px-2.5 py-1 text-xs font-semibold ${DEFECT_STATUS_STYLES[defect.status]}`}>
                {defect.status_label}
              </span>
            </div>
            {defect.description && <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">{defect.description}</p>}
            <p className="mt-1 text-xs text-slate-400">
              Заявка №{defect.id} · {timeAgo(defect.created_at)}
            </p>
            <button
              type="button"
              className="mt-2.5 flex items-center justify-center gap-1.5 w-full rounded-xl border border-slate-200/80 bg-white/70 py-1.5 text-xs font-semibold text-slate-700 hover:bg-white dark:border-white/10 dark:bg-white/5 dark:text-slate-200 dark:hover:bg-white/10 transition active:scale-[0.98]"
              onClick={() => copyAppeal(defect)}
            >
              <FileText className="h-3.5 w-3.5 text-accent" />
              Скопировать обращение для «Наш СПб» / Госуслуг
            </button>
          </div>
        ))}
        <button type="button" className="btn-secondary mb-2 mt-2 w-full" onClick={onReportDefect}>
          <Wrench className="h-5 w-5" />
          Сообщить о поломке
        </button>

        <div className="mt-5 flex items-center justify-between">
          <SectionTitle title="Отзывы игроков" count={reviews.length} />
          <button
            type="button"
            className="flex items-center gap-1 text-xs font-semibold text-accent hover:underline"
            onClick={onAddReview}
          >
            <Star className="h-3.5 w-3.5 fill-amber-400 text-amber-400" />
            Оставить отзыв
          </button>
        </div>

        {reviews.length === 0 ? (
          <div className="card mt-2 flex flex-col items-center py-5 text-center">
            <Star className="h-8 w-8 text-slate-300 dark:text-slate-600" />
            <p className="mt-2 text-sm font-semibold">Пока нет отзывов</p>
            <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">
              Были на этой площадке? Поделитесь впечатлениями первыми!
            </p>
            <button
              type="button"
              className="btn-secondary mt-3 text-xs py-1.5 px-3"
              onClick={onAddReview}
            >
              Написать отзыв
            </button>
          </div>
        ) : (
          <div className="mt-2 space-y-2 pb-2">
            {reviews.map((rev) => (
              <div key={rev.id} className="card p-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-sm">{rev.authorName}</span>
                    <span className="flex items-center text-xs font-bold text-amber-500">
                      {'⭐'.repeat(rev.rating)}
                    </span>
                  </div>
                  <span className="text-[11px] text-slate-400">{timeAgo(rev.createdAt)}</span>
                </div>
                {rev.text && (
                  <p className="mt-1.5 text-sm text-slate-700 dark:text-slate-300 leading-relaxed">
                    {rev.text}
                  </p>
                )}
                {rev.tags && rev.tags.length > 0 && (
                  <div className="mt-2 flex flex-wrap gap-1">
                    {rev.tags.map((tag) => (
                      <span
                        key={tag}
                        className="rounded-lg bg-slate-100 px-2 py-0.5 text-[11px] font-medium text-slate-600 dark:bg-white/10 dark:text-slate-300"
                      >
                        {tag}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </section>
  );
}
