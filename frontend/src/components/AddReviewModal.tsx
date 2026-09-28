import { useState } from 'react';
import { Star, Send } from 'lucide-react';
import { Modal } from './ui';

interface AddReviewModalProps {
  courtTitle: string;
  authorName: string;
  onClose: () => void;
  onSubmit: (review: { rating: number; text: string; tags: string[]; authorName: string }) => void;
}

const QUICK_TAGS = [
  '#ХорошиеКольца',
  '#ОтличноеПокрытие',
  '#ЕстьСветВечером',
  '#МногоИгроков',
  '#ЧистаяПлощадка',
  '#ЕстьСетки',
];

export default function AddReviewModal({
  courtTitle,
  authorName,
  onClose,
  onSubmit,
}: AddReviewModalProps) {
  const [rating, setRating] = useState(5);
  const [hoverRating, setHoverRating] = useState<number | null>(null);
  const [text, setText] = useState('');
  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  const [name, setName] = useState(authorName || '');
  const [busy, setBusy] = useState(false);

  const toggleTag = (tag: string) => {
    setSelectedTags((prev) =>
      prev.includes(tag) ? prev.filter((t) => t !== tag) : [...prev, tag]
    );
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!text.trim() && selectedTags.length === 0) {
      alert('Пожалуйста, напишите пару слов или выберите тег');
      return;
    }
    setBusy(true);
    onSubmit({
      rating,
      text: text.trim(),
      tags: selectedTags,
      authorName: name.trim() || 'Анонимный спортсмен',
    });
  };

  return (
    <Modal
      title="Отзыв о площадке"
      subtitle={courtTitle}
      onClose={onClose}
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Выбор рейтинга звёздами */}
        <div className="flex flex-col items-center justify-center rounded-2xl bg-slate-50 py-4 dark:bg-white/5">
          <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
            Ваша оценка
          </p>
          <div className="flex items-center gap-2">
            {[1, 2, 3, 4, 5].map((star) => {
              const active = (hoverRating ?? rating) >= star;
              return (
                <button
                  key={star}
                  type="button"
                  onClick={() => setRating(star)}
                  onMouseEnter={() => setHoverRating(star)}
                  onMouseLeave={() => setHoverRating(null)}
                  className="p-1 transition-transform hover:scale-125 active:scale-95 focus:outline-none"
                  aria-label={`${star} звезд`}
                >
                  <Star
                    className={`h-8 w-8 transition-colors ${
                      active
                        ? 'fill-amber-400 text-amber-400 drop-shadow-sm'
                        : 'text-slate-300 dark:text-slate-600'
                    }`}
                  />
                </button>
              );
            })}
          </div>
          <span className="mt-2 text-sm font-bold text-slate-700 dark:text-slate-200">
            {rating === 5 && '🔥 Отличная площадка!'}
            {rating === 4 && '👍 Хороший спот'}
            {rating === 3 && '👌 Нормально, играть можно'}
            {rating === 2 && '👎 Требует ремонта'}
            {rating === 1 && '⚠️ Плохое состояние'}
          </span>
        </div>

        {/* Быстрые теги */}
        <div>
          <label className="block text-xs font-semibold text-slate-600 dark:text-slate-400 mb-1.5">
            Быстрые теги
          </label>
          <div className="flex flex-wrap gap-1.5">
            {QUICK_TAGS.map((tag) => {
              const isSelected = selectedTags.includes(tag);
              return (
                <button
                  key={tag}
                  type="button"
                  onClick={() => toggleTag(tag)}
                  className={`rounded-full px-2.5 py-1 text-xs font-medium transition ${
                    isSelected
                      ? 'bg-accent text-white shadow-sm'
                      : 'bg-slate-100 text-slate-600 hover:bg-slate-200 dark:bg-white/10 dark:text-slate-300'
                  }`}
                >
                  {tag}
                </button>
              );
            })}
          </div>
        </div>

        {/* Текст отзыва */}
        <div>
          <label className="block text-xs font-semibold text-slate-600 dark:text-slate-400 mb-1">
            Ваш комментарий
          </label>
          <textarea
            rows={3}
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="Расскажите, как кольца, покрытие, освещение и собираются ли люди..."
            className="input w-full resize-none text-sm"
          />
        </div>

        {/* Имя автора */}
        <div>
          <label className="block text-xs font-semibold text-slate-600 dark:text-slate-400 mb-1">
            Ваше имя
          </label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Ваше имя в MAX"
            className="input w-full text-sm"
          />
        </div>

        <button
          type="submit"
          disabled={busy}
          className="btn-primary w-full flex items-center justify-center gap-2"
        >
          <Send className="h-4 w-4" />
          {busy ? 'Публикуем…' : 'Опубликовать отзыв'}
        </button>
      </form>
    </Modal>
  );
}
