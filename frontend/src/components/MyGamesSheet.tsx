import { useEffect, useState } from 'react';
import { Bot, CalendarDays } from 'lucide-react';
import { api, errorMessage } from '../api/client';
import { isInsideMax } from '../lib/max';
import type { BotInfo, Game, GameWithCourt, Identity } from '../types';
import GameCard from './GameCard';
import { Modal, Spinner } from './ui';

interface MyGamesSheetProps {
  identity: Identity;
  botInfo: BotInfo | null;
  refreshToken: number;
  busyGameId: number | null;
  onClose: () => void;
  onOpenCourt: (game: GameWithCourt) => void;
  onLeave: (gameId: number) => void;
  onPay: (game: Game, courtTitle: string) => void;
}

export default function MyGamesSheet({
  identity,
  botInfo,
  refreshToken,
  busyGameId,
  onClose,
  onOpenCourt,
  onLeave,
  onPay,
}: MyGamesSheetProps) {
  const [games, setGames] = useState<GameWithCourt[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    api
      .listGames({ user_max_id: identity.maxUserId })
      .then((data) => {
        if (!cancelled) {
          setGames(Array.isArray(data) ? data : []);
          setError(null);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setGames([]);
          setError(errorMessage(err));
        }
      });
    return () => {
      cancelled = true;
    };
  }, [identity.maxUserId, refreshToken]);

  return (
    <Modal title="Мои сборы" subtitle="Предстоящие игры, в которых вы участвуете" onClose={onClose}>
      {error && <p className="rounded-xl bg-rose-50 px-3 py-2 text-sm text-rose-700 dark:bg-rose-400/10 dark:text-rose-300">{error}</p>}
      {games === null && !error && (
        <div className="flex justify-center py-10">
          <Spinner className="h-7 w-7 text-accent" />
        </div>
      )}
      {games?.length === 0 && (
        <div className="card flex flex-col items-center py-8 text-center">
          <CalendarDays className="h-10 w-10 text-slate-300 dark:text-slate-600" />
          <p className="mt-3 font-semibold">Пока нет сборов</p>
          <p className="mt-1 max-w-xs text-sm text-slate-500 dark:text-slate-400">
            Выберите площадку на карте и присоединитесь к игре или создайте свой сбор
          </p>
        </div>
      )}
      {games?.map((game) => (
        <GameCard
          key={game.id}
          game={game}
          court={game.court}
          identity={identity}
          busy={busyGameId === game.id}
          onJoin={() => undefined}
          onLeave={() => onLeave(game.id)}
          onPay={() => onPay(game, game.court.title)}
          onOpenCourt={() => onOpenCourt(game)}
        />
      ))}

      <div className="mt-4 flex items-start gap-3 rounded-2xl bg-white p-4 text-sm text-slate-600 dark:bg-white/5 dark:text-slate-300">
        <Bot className="h-5 w-5 shrink-0 text-accent" />
        <p>
          {isInsideMax()
            ? 'Когда команда соберётся, бот пришлёт уведомление в MAX.'
            : 'Вы открыли приложение в браузере в гостевом режиме. Уведомления от бота приходят, когда мини-приложение запущено из MAX.'}
          {botInfo?.username && (
            <>
              {' '}
              Бот: <span className="font-semibold">@{botInfo.username}</span>
            </>
          )}
        </p>
      </div>
    </Modal>
  );
}
