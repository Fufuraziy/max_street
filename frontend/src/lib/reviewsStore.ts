export interface CourtReview {
  id: string;
  courtId: number;
  authorName: string;
  rating: number;
  text: string;
  tags: string[];
  createdAt: string;
}

const SEED_REVIEWS: Record<number, CourtReview[]> = {
  1: [
    {
      id: 'r-1-1',
      courtId: 1,
      authorName: 'Алексей М.',
      rating: 5,
      text: 'Топовый спот на Крестовском! Кольца ровные, сетки целые, вечером всегда плотные сборы 3×3.',
      tags: ['#ХорошиеКольца', '#МногоИгроков', '#ЕстьСветВечером'],
      createdAt: '2026-09-27T18:30:00Z',
    },
    {
      id: 'r-1-2',
      courtId: 1,
      authorName: 'Дмитрий К.',
      rating: 5,
      text: 'Отличное полимерное покрытие, не скользит даже после дождя. Рекомендую!',
      tags: ['#ОтличноеПокрытие'],
      createdAt: '2026-09-25T14:15:00Z',
    },
  ],
  2: [
    {
      id: 'r-2-1',
      courtId: 2,
      authorName: 'Сергей В.',
      rating: 5,
      text: 'Очень атмосферная площадка в Новой Голландии. Всегда чисто, отличная разметка.',
      tags: ['#ЧистаяПлощадка', '#ХорошиеКольца'],
      createdAt: '2026-09-26T16:00:00Z',
    },
  ],
  3: [
    {
      id: 'r-3-1',
      courtId: 3,
      authorName: 'Михаил Т.',
      rating: 4,
      text: 'Хороший спот в Таврическом, покрытие мягкое. Вечером немного не хватает бокового света, но играть супер.',
      tags: ['#ОтличноеПокрытие'],
      createdAt: '2026-09-24T19:20:00Z',
    },
  ],
  6: [
    {
      id: 'r-6-1',
      courtId: 6,
      authorName: 'Иван П.',
      rating: 5,
      text: 'Манеж «Фабрика Футбола» — газон высшего уровня, тёплые раздевалки и душ. Сплит через MAX очень удобен!',
      tags: ['#ОтличноеПокрытие', '#ЧистаяПлощадка'],
      createdAt: '2026-09-27T20:10:00Z',
    },
  ],
  7: [
    {
      id: 'r-7-1',
      courtId: 7,
      authorName: 'Артур Г.',
      rating: 5,
      text: 'Локомотив — классика мини-футбола. Собрали 6/6 за 15 минут через Safe Split, всё прошло гладко.',
      tags: ['#МногоИгроков'],
      createdAt: '2026-09-28T12:00:00Z',
    },
  ],
};

const STORAGE_KEY = 'maxstreet_user_reviews';

function loadStoredReviews(): CourtReview[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    return JSON.parse(raw);
  } catch {
    return [];
  }
}

function saveStoredReviews(reviews: CourtReview[]) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(reviews));
  } catch {
    // ignore
  }
}

export const reviewsStore = {
  getCourtReviews(courtId: number): CourtReview[] {
    const custom = loadStoredReviews().filter((r) => r.courtId === courtId);
    const seeded = SEED_REVIEWS[courtId] ?? [];
    return [...custom, ...seeded];
  },

  addReview(
    courtId: number,
    data: { rating: number; text: string; tags: string[]; authorName: string }
  ): CourtReview {
    const all = loadStoredReviews();
    const newReview: CourtReview = {
      id: `usr-${Date.now()}`,
      courtId,
      authorName: data.authorName,
      rating: data.rating,
      text: data.text,
      tags: data.tags,
      createdAt: new Date().toISOString(),
    };
    all.unshift(newReview);
    saveStoredReviews(all);
    return newReview;
  },
};
