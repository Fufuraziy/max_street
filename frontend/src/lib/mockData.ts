import type { Court, CourtDetail, Defect, Game, SportType } from '../types';

export const FALLBACK_COURTS: Court[] = [
  {
    id: 1,
    title: 'Стритбол-парк на Крестовском (Сибур Арена)',
    sport_types: ['basketball'],
    is_commercial: false,
    price_from: null,
    address: 'Футбольная аллея, 8, Санкт-Петербург',
    latitude: 59.9723,
    longitude: 30.2214,
    has_lighting: true,
    surface_type: 'rubber',
    is_indoor: false,
    rating: 4.8,
    active_games_today: 1,
    description: 'Популярный спот на открытом воздухе с профессиональным резиновым покрытием и стандартными кольцами.',
  },
  {
    id: 2,
    title: 'Баскетбольная площадка в Новой Голландии',
    sport_types: ['basketball'],
    is_commercial: false,
    price_from: null,
    address: 'наб. Адмиралтейского канала, 2, Санкт-Петербург',
    latitude: 59.9298,
    longitude: 30.2891,
    has_lighting: true,
    surface_type: 'acrylic',
    is_indoor: false,
    rating: 4.7,
    active_games_today: 1,
    description: 'Открытая площадка на острове Новая Голландия. Хорошее освещение и ограждение сеткой.',
  },
  {
    id: 3,
    title: 'Дворовая площадка на Таврической',
    sport_types: ['basketball'],
    is_commercial: false,
    price_from: null,
    address: 'Таврическая ул., 17, Санкт-Петербург',
    latitude: 59.9458,
    longitude: 30.3789,
    has_lighting: false,
    surface_type: 'asphalt',
    is_indoor: false,
    rating: 4.4,
    active_games_today: 0,
    description: 'Классический уличный корт с двумя кольцами в тихом дворе Центрального района.',
  },
  {
    id: 4,
    title: 'Стритбольный спот в Севкабель Порту',
    sport_types: ['basketball'],
    is_commercial: false,
    price_from: null,
    address: 'Кожевенная линия, 40, Санкт-Петербург',
    latitude: 59.9242,
    longitude: 30.2415,
    has_lighting: true,
    surface_type: 'rubber',
    is_indoor: false,
    rating: 4.9,
    active_games_today: 1,
    description: 'Видовая площадка на берегу Финского залива. Регулярные вечерние игры 3х3.',
  },
  {
    id: 5,
    title: 'Футбольная коробка в Парке Победы',
    sport_types: ['football'],
    is_commercial: false,
    price_from: null,
    address: 'Кузнецовская ул., 25, Санкт-Петербург',
    latitude: 59.8665,
    longitude: 30.3228,
    has_lighting: true,
    surface_type: 'artificial_grass',
    is_indoor: false,
    rating: 4.6,
    active_games_today: 1,
    description: 'Общедоступная огороженная коробка с искусственным газоном и мини-футбольными воротами.',
  },
  {
    id: 6,
    title: 'Футбольный манеж «Фабрика Футбола»',
    sport_types: ['football'],
    is_commercial: true,
    price_from: 3600,
    address: 'Софийская ул., 14, Санкт-Петербург',
    latitude: 59.8781,
    longitude: 30.3842,
    has_lighting: true,
    surface_type: 'artificial_grass',
    is_indoor: true,
    rating: 4.9,
    active_games_today: 1,
    description: 'Крытый манеж с раздевалками, душевыми и качественным газоном 4G. Идеально для Safe Split сборов.',
  },
  {
    id: 7,
    title: 'Спортивный центр «Локомотив» (Мини-футбол)',
    sport_types: ['football'],
    is_commercial: true,
    price_from: 3000,
    address: 'ул. Константина Заслонова, 23/4, Санкт-Петербург',
    latitude: 59.9176,
    longitude: 30.3491,
    has_lighting: true,
    surface_type: 'parquet',
    is_indoor: true,
    rating: 4.8,
    active_games_today: 1,
    description: 'Крытый паркетный зал с трибунами для мини-футбола и футзала.',
  },
  {
    id: 8,
    title: 'Открытая коробка в Удельном парке',
    sport_types: ['football'],
    is_commercial: false,
    price_from: null,
    address: 'Фермское шоссе, 21, Санкт-Петербург',
    latitude: 60.0072,
    longitude: 30.3155,
    has_lighting: false,
    surface_type: 'rubber',
    is_indoor: false,
    rating: 4.3,
    active_games_today: 0,
    description: 'Бесплатная дворовая площадка рядом с тренировочной базой, доступна для свободных матчей.',
  },
  {
    id: 9,
    title: 'Padel Pro Arena (Петроградка)',
    sport_types: ['padel'],
    is_commercial: true,
    price_from: 2800,
    address: 'Вязовая ул., 10, Санкт-Петербург',
    latitude: 59.9715,
    longitude: 30.2798,
    has_lighting: true,
    surface_type: 'panoramic_glass_turf',
    is_indoor: false,
    rating: 4.9,
    active_games_today: 1,
    description: 'Панорамные корты с профессиональным кварцевым песком и итальянским освещением.',
  },
  {
    id: 10,
    title: 'Падел-клуб «Стрела»',
    sport_types: ['padel'],
    is_commercial: true,
    price_from: 2400,
    address: 'Лиговский пр., 50, Санкт-Петербург',
    latitude: 59.9248,
    longitude: 30.3592,
    has_lighting: true,
    surface_type: 'padel_turf',
    is_indoor: false,
    rating: 4.7,
    active_games_today: 1,
    description: 'Удобная локация в центре города. Аренда ракеток и мячей на ресепшене.',
  },
  {
    id: 11,
    title: 'Padel Hub Приморский',
    sport_types: ['padel'],
    is_commercial: true,
    price_from: 2600,
    address: 'Приморский пр., 72, Санкт-Петербург',
    latitude: 59.9832,
    longitude: 30.2071,
    has_lighting: true,
    surface_type: 'panoramic_glass_turf',
    is_indoor: true,
    rating: 4.8,
    active_games_today: 0,
    description: 'Крытый центр с 4 падел-кортами рядом с парком 300-летия.',
  },
  {
    id: 12,
    title: 'Теннисный клуб «Гулливер»',
    sport_types: ['tennis'],
    is_commercial: true,
    price_from: 2200,
    address: 'Торфяная дорога, 7, Санкт-Петербург',
    latitude: 59.9912,
    longitude: 30.3014,
    has_lighting: true,
    surface_type: 'hard',
    is_indoor: true,
    rating: 4.8,
    active_games_today: 1,
    description: 'Закрытые корты с покрытием Hard, комфортная зона ожидания и душевые.',
  },
  {
    id: 13,
    title: 'Корты спортивного комплекса «Динамо»',
    sport_types: ['tennis'],
    is_commercial: true,
    price_from: 1800,
    address: 'пр. Динамо, 44, Санкт-Петербург',
    latitude: 59.9678,
    longitude: 30.2647,
    has_lighting: true,
    surface_type: 'clay',
    is_indoor: false,
    rating: 4.7,
    active_games_today: 0,
    description: 'Классические грунтовые корты на Крестовском острове с вековой спортивной историей.',
  },
  {
    id: 14,
    title: 'Теннисный центр «Арсенал»',
    sport_types: ['tennis'],
    is_commercial: true,
    price_from: 2000,
    address: 'пр. Металлистов, 51, Санкт-Петербург',
    latitude: 59.9664,
    longitude: 30.3989,
    has_lighting: true,
    surface_type: 'tera_flex',
    is_indoor: true,
    rating: 4.6,
    active_games_today: 1,
    description: 'Крытый зал с мягким амортизирующим покрытием для тренировок и парных матчей.',
  },
  {
    id: 15,
    title: 'Воркаут и мультиспорт зона в Муринском парке',
    sport_types: ['workout', 'basketball'],
    is_commercial: false,
    price_from: null,
    address: 'пр. Луначарского, 82, Санкт-Петербург',
    latitude: 60.0345,
    longitude: 30.4012,
    has_lighting: true,
    surface_type: 'rubber',
    is_indoor: false,
    rating: 4.6,
    active_games_today: 1,
    description: 'Большой открытый кластер с турниками, брусьями, стритбольным кольцом и зоной разминки.',
  },
];

const todayEvening = new Date();
todayEvening.setHours(19, 30, 0, 0);

const INITIAL_LOKO_GAME: Game = {
  id: 701,
  court_id: 7,
  creator_max_id: 'demo_jury_1',
  sport_type: 'football',
  start_time: todayEvening.toISOString(),
  required_players: 6,
  current_players: 5,
  status: 'recruiting',
  status_label: 'Идёт набор',
  comment: 'Мини-футбол 3×3 на паркете. Ждём 6-го игрока для выкупа зала!',
  created_at: new Date(Date.now() - 3600000).toISOString(),
  spots_left: 1,
  slot_id: 7010,
  escrow_account_id: 'ESC-7042-LOKO',
  total_cost: 3000,
  collected_amount: 2500,
  payment_status: 'pending',
  payment_status_label: 'Идёт сбор средств',
  payment_deadline: new Date(todayEvening.getTime() - 7200000).toISOString(),
  booking_reference: null,
  share_amount: 500,
  paid_count: 5,
  is_paid: true,
  participants: [
    {
      user_max_id: 'demo_jury_1',
      user_name: 'Артём',
      reliability_score: 98,
      joined_at: new Date(Date.now() - 3600000).toISOString(),
      has_paid: true,
      paid_amount: 500,
      paid_at: new Date(Date.now() - 3500000).toISOString(),
    },
    {
      user_max_id: 'demo_jury_2',
      user_name: 'Михаил',
      reliability_score: 95,
      joined_at: new Date(Date.now() - 3000000).toISOString(),
      has_paid: true,
      paid_amount: 500,
      paid_at: new Date(Date.now() - 2900000).toISOString(),
    },
    {
      user_max_id: 'demo_jury_3',
      user_name: 'Алексей',
      reliability_score: 100,
      joined_at: new Date(Date.now() - 2400000).toISOString(),
      has_paid: true,
      paid_amount: 500,
      paid_at: new Date(Date.now() - 2300000).toISOString(),
    },
    {
      user_max_id: 'demo_jury_4',
      user_name: 'Денис',
      reliability_score: 96,
      joined_at: new Date(Date.now() - 1800000).toISOString(),
      has_paid: true,
      paid_amount: 500,
      paid_at: new Date(Date.now() - 1700000).toISOString(),
    },
    {
      user_max_id: 'demo_jury_5',
      user_name: 'Илья',
      reliability_score: 97,
      joined_at: new Date(Date.now() - 1200000).toISOString(),
      has_paid: true,
      paid_amount: 500,
      paid_at: new Date(Date.now() - 1100000).toISOString(),
    },
  ],
  slot: {
    id: 7010,
    start_time: todayEvening.toISOString(),
    end_time: new Date(todayEvening.getTime() + 5400000).toISOString(),
    price: 3000,
    duration_minutes: 90,
  },
};

const INITIAL_FREE_BASKETBALL: Game = {
  id: 101,
  court_id: 1,
  creator_max_id: 'demo_free_101',
  sport_type: 'basketball',
  start_time: new Date(Date.now() + 7200000).toISOString(),
  required_players: 6,
  current_players: 4,
  status: 'recruiting',
  status_label: 'Идёт набор',
  comment: 'Стритбол 3×3 на Сибур Арене, уровень средний. Присоединяйтесь!',
  created_at: new Date(Date.now() - 3600000).toISOString(),
  spots_left: 2,
  slot_id: null,
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
  participants: [
    { user_max_id: 'demo_free_101', user_name: 'Даниил', joined_at: new Date(Date.now() - 3600000).toISOString(), has_paid: false, paid_amount: 0, paid_at: null },
    { user_max_id: 'demo_free_102', user_name: 'Максим', joined_at: new Date(Date.now() - 2700000).toISOString(), has_paid: false, paid_amount: 0, paid_at: null },
    { user_max_id: 'demo_free_103', user_name: 'Никита', joined_at: new Date(Date.now() - 1800000).toISOString(), has_paid: false, paid_amount: 0, paid_at: null },
    { user_max_id: 'demo_free_104', user_name: 'Егор', joined_at: new Date(Date.now() - 900000).toISOString(), has_paid: false, paid_amount: 0, paid_at: null },
  ],
};

const INITIAL_FREE_FOOTBALL: Game = {
  id: 501,
  court_id: 5,
  creator_max_id: 'demo_free_201',
  sport_type: 'football',
  start_time: new Date(Date.now() + 10800000).toISOString(),
  required_players: 10,
  current_players: 7,
  status: 'recruiting',
  status_label: 'Идёт набор',
  comment: 'Футбол 5×5 в коробке. Есть мяч и манишки, ищем ещё троих!',
  created_at: new Date(Date.now() - 7200000).toISOString(),
  spots_left: 3,
  slot_id: null,
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
  participants: [
    { user_max_id: 'demo_free_201', user_name: 'Сергей', joined_at: new Date(Date.now() - 7200000).toISOString(), has_paid: false, paid_amount: 0, paid_at: null },
    { user_max_id: 'demo_free_202', user_name: 'Павел', joined_at: new Date(Date.now() - 6000000).toISOString(), has_paid: false, paid_amount: 0, paid_at: null },
    { user_max_id: 'demo_free_203', user_name: 'Александр', joined_at: new Date(Date.now() - 4800000).toISOString(), has_paid: false, paid_amount: 0, paid_at: null },
    { user_max_id: 'demo_free_204', user_name: 'Тимур', joined_at: new Date(Date.now() - 3600000).toISOString(), has_paid: false, paid_amount: 0, paid_at: null },
    { user_max_id: 'demo_free_205', user_name: 'Владимир', joined_at: new Date(Date.now() - 2400000).toISOString(), has_paid: false, paid_amount: 0, paid_at: null },
    { user_max_id: 'demo_free_206', user_name: 'Олег', joined_at: new Date(Date.now() - 1200000).toISOString(), has_paid: false, paid_amount: 0, paid_at: null },
    { user_max_id: 'demo_free_207', user_name: 'Ярослав', joined_at: new Date(Date.now() - 600000).toISOString(), has_paid: false, paid_amount: 0, paid_at: null },
  ],
};

const INITIAL_FREE_WORKOUT: Game = {
  id: 1501,
  court_id: 15,
  creator_max_id: 'demo_free_301',
  sport_type: 'workout',
  start_time: new Date(Date.now() + 5400000).toISOString(),
  required_players: 4,
  current_players: 3,
  status: 'recruiting',
  status_label: 'Идёт набор',
  comment: 'Совместная тренировка на турниках и брусьях, разминка и подтягивания.',
  created_at: new Date(Date.now() - 5400000).toISOString(),
  spots_left: 1,
  slot_id: null,
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
  participants: [
    { user_max_id: 'demo_free_301', user_name: 'Константин', joined_at: new Date(Date.now() - 5400000).toISOString(), has_paid: false, paid_amount: 0, paid_at: null },
    { user_max_id: 'demo_free_302', user_name: 'Матвей', joined_at: new Date(Date.now() - 3600000).toISOString(), has_paid: false, paid_amount: 0, paid_at: null },
    { user_max_id: 'demo_free_303', user_name: 'Арсений', joined_at: new Date(Date.now() - 1800000).toISOString(), has_paid: false, paid_amount: 0, paid_at: null },
  ],
};

const INITIAL_NEW_HOLLAND_GAME: Game = {
  id: 201,
  court_id: 2,
  creator_max_id: 'demo_free_111',
  sport_type: 'basketball',
  start_time: new Date(Date.now() + 14400000).toISOString(),
  required_players: 10,
  current_players: 6,
  status: 'recruiting',
  status_label: 'Идёт набор',
  comment: 'Баскетбол 5×5 на острове Новая Голландия. Хорошая динамичная игра.',
  created_at: new Date(Date.now() - 5400000).toISOString(),
  spots_left: 4,
  slot_id: null,
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
  participants: [
    { user_max_id: 'demo_free_111', user_name: 'Тимофей', reliability_score: 98, joined_at: new Date(Date.now() - 5400000).toISOString(), has_paid: false, paid_amount: 0, paid_at: null },
    { user_max_id: 'demo_free_112', user_name: 'Марк', reliability_score: 95, joined_at: new Date(Date.now() - 4500000).toISOString(), has_paid: false, paid_amount: 0, paid_at: null },
    { user_max_id: 'demo_free_113', user_name: 'Лев', reliability_score: 100, joined_at: new Date(Date.now() - 3600000).toISOString(), has_paid: false, paid_amount: 0, paid_at: null },
    { user_max_id: 'demo_free_114', user_name: 'Степан', reliability_score: 96, joined_at: new Date(Date.now() - 2700000).toISOString(), has_paid: false, paid_amount: 0, paid_at: null },
    { user_max_id: 'demo_free_115', user_name: 'Богдан', reliability_score: 94, joined_at: new Date(Date.now() - 1800000).toISOString(), has_paid: false, paid_amount: 0, paid_at: null },
    { user_max_id: 'demo_free_116', user_name: 'Семён', reliability_score: 97, joined_at: new Date(Date.now() - 900000).toISOString(), has_paid: false, paid_amount: 0, paid_at: null },
  ],
};

const INITIAL_SEVKABEL_GAME: Game = {
  id: 401,
  court_id: 4,
  creator_max_id: 'demo_free_121',
  sport_type: 'basketball',
  start_time: new Date(Date.now() + 18000000).toISOString(),
  required_players: 6,
  current_players: 3,
  status: 'recruiting',
  status_label: 'Идёт набор',
  comment: 'Стритбол на закате у Финского залива! Ищем 3 игроков для полноценной игры 3х3.',
  created_at: new Date(Date.now() - 3600000).toISOString(),
  spots_left: 3,
  slot_id: null,
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
  participants: [
    { user_max_id: 'demo_free_121', user_name: 'Григорий', reliability_score: 99, joined_at: new Date(Date.now() - 3600000).toISOString(), has_paid: false, paid_amount: 0, paid_at: null },
    { user_max_id: 'demo_free_122', user_name: 'Ян', reliability_score: 96, joined_at: new Date(Date.now() - 2400000).toISOString(), has_paid: false, paid_amount: 0, paid_at: null },
    { user_max_id: 'demo_free_123', user_name: 'Артур', reliability_score: 95, joined_at: new Date(Date.now() - 1200000).toISOString(), has_paid: false, paid_amount: 0, paid_at: null },
  ],
};

const INITIAL_FABRIKA_GAME: Game = {
  id: 601,
  court_id: 6,
  creator_max_id: 'demo_ff_1',
  sport_type: 'football',
  start_time: new Date(Date.now() + 21600000).toISOString(),
  required_players: 10,
  current_players: 7,
  status: 'recruiting',
  status_label: 'Идёт набор',
  comment: 'Футбол 5×5 на искусственном газоне 4G. Идёт сбор долей на эскроу-счёт.',
  created_at: new Date(Date.now() - 7200000).toISOString(),
  spots_left: 3,
  slot_id: 6010,
  escrow_account_id: 'ESC-6088-FABR',
  total_cost: 3600,
  collected_amount: 2520,
  payment_status: 'pending',
  payment_status_label: 'Идёт сбор средств',
  payment_deadline: new Date(Date.now() + 18000000).toISOString(),
  booking_reference: null,
  share_amount: 360,
  paid_count: 7,
  is_paid: true,
  participants: [
    { user_max_id: 'demo_ff_1', user_name: 'Роман', reliability_score: 98, joined_at: new Date(Date.now() - 7200000).toISOString(), has_paid: true, paid_amount: 360, paid_at: new Date().toISOString() },
    { user_max_id: 'demo_ff_2', user_name: 'Глеб', reliability_score: 95, joined_at: new Date(Date.now() - 6000000).toISOString(), has_paid: true, paid_amount: 360, paid_at: new Date().toISOString() },
    { user_max_id: 'demo_ff_3', user_name: 'Виктор', reliability_score: 97, joined_at: new Date(Date.now() - 5000000).toISOString(), has_paid: true, paid_amount: 360, paid_at: new Date().toISOString() },
    { user_max_id: 'demo_ff_4', user_name: 'Андрей', reliability_score: 100, joined_at: new Date(Date.now() - 4000000).toISOString(), has_paid: true, paid_amount: 360, paid_at: new Date().toISOString() },
    { user_max_id: 'demo_ff_5', user_name: 'Максим', reliability_score: 93, joined_at: new Date(Date.now() - 3000000).toISOString(), has_paid: true, paid_amount: 360, paid_at: new Date().toISOString() },
    { user_max_id: 'demo_ff_6', user_name: 'Станислав', reliability_score: 96, joined_at: new Date(Date.now() - 2000000).toISOString(), has_paid: true, paid_amount: 360, paid_at: new Date().toISOString() },
    { user_max_id: 'demo_ff_7', user_name: 'Фёдор', reliability_score: 94, joined_at: new Date(Date.now() - 1000000).toISOString(), has_paid: true, paid_amount: 360, paid_at: new Date().toISOString() },
  ],
  slot: {
    id: 6010,
    start_time: new Date(Date.now() + 21600000).toISOString(),
    end_time: new Date(Date.now() + 27000000).toISOString(),
    price: 3600,
    duration_minutes: 90,
  },
};

const INITIAL_PADEL_GAME: Game = {
  id: 901,
  court_id: 9,
  creator_max_id: 'demo_padel_1',
  sport_type: 'padel',
  start_time: new Date(Date.now() + 18000000).toISOString(),
  required_players: 4,
  current_players: 3,
  status: 'recruiting',
  status_label: 'Идёт набор',
  comment: 'Падел 2×2 для продолжающих. Остался 1 слот, корт выкупается сразу при сборе!',
  created_at: new Date(Date.now() - 3600000).toISOString(),
  spots_left: 1,
  slot_id: 9010,
  escrow_account_id: 'ESC-9124-PADL',
  total_cost: 2800,
  collected_amount: 2100,
  payment_status: 'pending',
  payment_status_label: 'Идёт сбор средств',
  payment_deadline: new Date(Date.now() + 14400000).toISOString(),
  booking_reference: null,
  share_amount: 700,
  paid_count: 3,
  is_paid: true,
  participants: [
    { user_max_id: 'demo_padel_1', user_name: 'Ольга', reliability_score: 99, joined_at: new Date(Date.now() - 3600000).toISOString(), has_paid: true, paid_amount: 700, paid_at: new Date().toISOString() },
    { user_max_id: 'demo_padel_2', user_name: 'Кирилл', reliability_score: 96, joined_at: new Date(Date.now() - 2400000).toISOString(), has_paid: true, paid_amount: 700, paid_at: new Date().toISOString() },
    { user_max_id: 'demo_padel_3', user_name: 'Дмитрий', reliability_score: 94, joined_at: new Date(Date.now() - 1200000).toISOString(), has_paid: true, paid_amount: 700, paid_at: new Date().toISOString() },
  ],
  slot: {
    id: 9010,
    start_time: new Date(Date.now() + 18000000).toISOString(),
    end_time: new Date(Date.now() + 23400000).toISOString(),
    price: 2800,
    duration_minutes: 90,
  },
};

const INITIAL_STRELA_GAME: Game = {
  id: 1001,
  court_id: 10,
  creator_max_id: 'demo_str_1',
  sport_type: 'padel',
  start_time: new Date(Date.now() + 25200000).toISOString(),
  required_players: 4,
  current_players: 2,
  status: 'recruiting',
  status_label: 'Идёт набор',
  comment: 'Падел на Лиговском. 2 места свободно, по 600 ₽ с человека.',
  created_at: new Date(Date.now() - 4800000).toISOString(),
  spots_left: 2,
  slot_id: 10010,
  escrow_account_id: 'ESC-1044-STRL',
  total_cost: 2400,
  collected_amount: 1200,
  payment_status: 'pending',
  payment_status_label: 'Идёт сбор средств',
  payment_deadline: new Date(Date.now() + 21600000).toISOString(),
  booking_reference: null,
  share_amount: 600,
  paid_count: 2,
  is_paid: true,
  participants: [
    { user_max_id: 'demo_str_1', user_name: 'Валерий', reliability_score: 96, joined_at: new Date(Date.now() - 4800000).toISOString(), has_paid: true, paid_amount: 600, paid_at: new Date().toISOString() },
    { user_max_id: 'demo_str_2', user_name: 'Елена', reliability_score: 98, joined_at: new Date(Date.now() - 2400000).toISOString(), has_paid: true, paid_amount: 600, paid_at: new Date().toISOString() },
  ],
  slot: {
    id: 10010,
    start_time: new Date(Date.now() + 25200000).toISOString(),
    end_time: new Date(Date.now() + 30600000).toISOString(),
    price: 2400,
    duration_minutes: 90,
  },
};

const INITIAL_GULLIVER_GAME: Game = {
  id: 1201,
  court_id: 12,
  creator_max_id: 'demo_ten_1',
  sport_type: 'tennis',
  start_time: new Date(Date.now() + 18000000).toISOString(),
  required_players: 2,
  current_players: 1,
  status: 'recruiting',
  status_label: 'Идёт набор',
  comment: 'Теннисный спарринг на закрытом харде. Организатор внёс свою долю 1100 ₽.',
  created_at: new Date(Date.now() - 3600000).toISOString(),
  spots_left: 1,
  slot_id: 12010,
  escrow_account_id: 'ESC-1205-GULL',
  total_cost: 2200,
  collected_amount: 1100,
  payment_status: 'pending',
  payment_status_label: 'Идёт сбор средств',
  payment_deadline: new Date(Date.now() + 14400000).toISOString(),
  booking_reference: null,
  share_amount: 1100,
  paid_count: 1,
  is_paid: true,
  participants: [
    { user_max_id: 'demo_ten_1', user_name: 'Георгий', reliability_score: 99, joined_at: new Date(Date.now() - 3600000).toISOString(), has_paid: true, paid_amount: 1100, paid_at: new Date().toISOString() },
  ],
  slot: {
    id: 12010,
    start_time: new Date(Date.now() + 18000000).toISOString(),
    end_time: new Date(Date.now() + 23400000).toISOString(),
    price: 2200,
    duration_minutes: 90,
  },
};

const INITIAL_ARSENAL_GAME: Game = {
  id: 1401,
  court_id: 14,
  creator_max_id: 'demo_ars_1',
  sport_type: 'tennis',
  start_time: new Date(Date.now() + 21600000).toISOString(),
  required_players: 2,
  current_players: 1,
  status: 'recruiting',
  status_label: 'Идёт набор',
  comment: 'Большой теннис на корте TeraFlex. Ищу партнёра для игры, 1000 ₽ с человека.',
  created_at: new Date(Date.now() - 5400000).toISOString(),
  spots_left: 1,
  slot_id: 14010,
  escrow_account_id: 'ESC-1412-ARSN',
  total_cost: 2000,
  collected_amount: 1000,
  payment_status: 'pending',
  payment_status_label: 'Идёт сбор средств',
  payment_deadline: new Date(Date.now() + 18000000).toISOString(),
  booking_reference: null,
  share_amount: 1000,
  paid_count: 1,
  is_paid: true,
  participants: [
    { user_max_id: 'demo_ars_1', user_name: 'Константин', reliability_score: 97, joined_at: new Date(Date.now() - 5400000).toISOString(), has_paid: true, paid_amount: 1000, paid_at: new Date().toISOString() },
  ],
  slot: {
    id: 14010,
    start_time: new Date(Date.now() + 21600000).toISOString(),
    end_time: new Date(Date.now() + 27000000).toISOString(),
    price: 2000,
    duration_minutes: 90,
  },
};

const FALLBACK_GAMES_BY_COURT: Record<number, Game[]> = {
  1: [INITIAL_FREE_BASKETBALL],
  2: [INITIAL_NEW_HOLLAND_GAME],
  4: [INITIAL_SEVKABEL_GAME],
  5: [INITIAL_FREE_FOOTBALL],
  6: [INITIAL_FABRIKA_GAME],
  7: [INITIAL_LOKO_GAME],
  9: [INITIAL_PADEL_GAME],
  10: [INITIAL_STRELA_GAME],
  12: [INITIAL_GULLIVER_GAME],
  14: [INITIAL_ARSENAL_GAME],
  15: [INITIAL_FREE_WORKOUT],
};

const FALLBACK_DEFECTS_BY_COURT: Record<number, Defect[]> = {
  1: [
    {
      id: 101,
      court_id: 1,
      defect_type: 'broken_ring',
      defect_label: 'Сломано кольцо или щит',
      description: 'Погнуто кольцо на основном щите после вечерней игры',
      status: 'reported',
      status_label: 'Передано в районные службы',
      created_at: new Date(Date.now() - 86400000).toISOString(),
    },
  ],
  2: [
    {
      id: 102,
      court_id: 2,
      defect_type: 'net_missing',
      defect_label: 'Нет сетки',
      description: 'Порвана сетка на кольце',
      status: 'reported',
      status_label: 'Передано в районные службы',
      created_at: new Date(Date.now() - 172800000).toISOString(),
    },
  ],
  3: [
    {
      id: 103,
      court_id: 3,
      defect_type: 'broken_ring',
      defect_label: 'Сломано кольцо или щит',
      description: 'Погнуто кольцо, мяч застревает при бросках',
      status: 'reported',
      status_label: 'Передано в районные службы',
      created_at: new Date(Date.now() - 259200000).toISOString(),
    },
  ],
  5: [
    {
      id: 104,
      court_id: 5,
      defect_type: 'net_missing',
      defect_label: 'Нет сетки',
      description: 'Порвана сетка на мини-футбольных воротах',
      status: 'reported',
      status_label: 'Передано в районные службы',
      created_at: new Date(Date.now() - 86400000).toISOString(),
    },
  ],
  8: [
    {
      id: 105,
      court_id: 8,
      defect_type: 'surface_damage',
      defect_label: 'Яма или повреждение покрытия',
      description: 'Отслоение резинового покрытия в штрафной площади',
      status: 'reported',
      status_label: 'Передано в районные службы',
      created_at: new Date(Date.now() - 172800000).toISOString(),
    },
  ],
};

export function updateFallbackGameToBooked(
  gameId: number,
  player: { user_max_id: string; user_name: string },
): Game | null {
  for (const courtIdStr of Object.keys(FALLBACK_GAMES_BY_COURT)) {
    const courtId = Number(courtIdStr);
    const games = FALLBACK_GAMES_BY_COURT[courtId];
    const gameIdx = games.findIndex((g) => g.id === gameId);
    if (gameIdx !== -1) {
      const g = games[gameIdx];
      const existingPartIdx = g.participants.findIndex((p) => p.user_max_id === player.user_max_id);
      let newParticipants = [...g.participants];
      if (existingPartIdx !== -1) {
        newParticipants[existingPartIdx] = {
          ...newParticipants[existingPartIdx],
          has_paid: true,
          paid_amount: 500,
          paid_at: new Date().toISOString(),
        };
      } else {
        newParticipants.push({
          user_max_id: player.user_max_id,
          user_name: player.user_name || 'Гость (Жюри)',
          joined_at: new Date().toISOString(),
          has_paid: true,
          paid_amount: 500,
          paid_at: new Date().toISOString(),
        });
      }

      const updatedGame: Game = {
        ...g,
        current_players: 6,
        spots_left: 0,
        collected_amount: 3000,
        payment_status: 'paid_to_court',
        payment_status_label: 'Оплачено площадке',
        status: 'booked',
        status_label: 'Забронировано',
        booking_reference: 'BOOK-LOKO-701',
        paid_count: 6,
        participants: newParticipants,
      };

      FALLBACK_GAMES_BY_COURT[courtId][gameIdx] = updatedGame;
      return updatedGame;
    }
  }
  return null;
}

export function joinFallbackGame(
  gameId: number,
  player: { user_max_id: string; user_name: string },
): { joined: boolean; confirmed: boolean; game: Game } | null {
  for (const courtIdStr of Object.keys(FALLBACK_GAMES_BY_COURT)) {
    const courtId = Number(courtIdStr);
    const games = FALLBACK_GAMES_BY_COURT[courtId];
    const gameIdx = games.findIndex((g) => g.id === gameId);
    if (gameIdx !== -1) {
      const g = games[gameIdx];
      const already = g.participants.some((p) => p.user_max_id === player.user_max_id);
      if (already) {
        return { joined: false, confirmed: g.status === 'confirmed' || g.status === 'booked', game: g };
      }
      const updatedParticipants = [
        ...g.participants,
        {
          user_max_id: player.user_max_id,
          user_name: player.user_name || 'Игрок',
          joined_at: new Date().toISOString(),
          has_paid: false,
          paid_amount: 0,
          paid_at: null,
        },
      ];
      const count = updatedParticipants.length;
      const isConfirmed = count >= g.required_players;
      const updated: Game = {
        ...g,
        current_players: count,
        spots_left: Math.max(0, g.required_players - count),
        status: isConfirmed ? 'confirmed' : 'recruiting',
        status_label: isConfirmed ? 'Состав набран' : 'Идёт набор',
        participants: updatedParticipants,
      };
      FALLBACK_GAMES_BY_COURT[courtId][gameIdx] = updated;
      return { joined: true, confirmed: isConfirmed, game: updated };
    }
  }
  return null;
}

export function leaveFallbackGame(
  gameId: number,
  player: { user_max_id: string },
): { left: boolean; game: Game } | null {
  for (const courtIdStr of Object.keys(FALLBACK_GAMES_BY_COURT)) {
    const courtId = Number(courtIdStr);
    const games = FALLBACK_GAMES_BY_COURT[courtId];
    const gameIdx = games.findIndex((g) => g.id === gameId);
    if (gameIdx !== -1) {
      const g = games[gameIdx];
      const updatedParticipants = g.participants.filter((p) => p.user_max_id !== player.user_max_id);
      const count = updatedParticipants.length;
      const updated: Game = {
        ...g,
        current_players: count,
        spots_left: Math.max(0, g.required_players - count),
        status: 'recruiting',
        status_label: 'Идёт набор',
        participants: updatedParticipants,
      };
      FALLBACK_GAMES_BY_COURT[courtId][gameIdx] = updated;
      return { left: true, game: updated };
    }
  }
  return null;
}

export function reportFallbackDefect(
  courtId: number,
  payload: { defect_type: string; description: string },
): Defect {
  const defect: Defect = {
    id: Date.now(),
    court_id: courtId,
    defect_type: payload.defect_type as Defect['defect_type'],
    defect_label: 'Заявка принята',
    description: payload.description,
    status: 'reported',
    status_label: 'Передано в районные службы',
    created_at: new Date().toISOString(),
  };
  if (!FALLBACK_DEFECTS_BY_COURT[courtId]) {
    FALLBACK_DEFECTS_BY_COURT[courtId] = [];
  }
  FALLBACK_DEFECTS_BY_COURT[courtId].unshift(defect);
  return defect;
}

export function getFallbackSlots(courtId: number, dateStr: string): import('../types').Slot[] {
  const court = FALLBACK_COURTS.find((c) => c.id === courtId);
  if (!court || !court.is_commercial) return [];

  const basePrice = court.price_from || 2500;
  const slotTimes = ['09:00', '10:30', '12:00', '13:30', '15:00', '16:30', '18:00', '19:30', '21:00'];
  return slotTimes.map((timeStr, idx) => {
    const [hh, mm] = timeStr.split(':').map(Number);
    const start = new Date(`${dateStr}T00:00:00`);
    start.setHours(hh, mm, 0, 0);
    const end = new Date(start.getTime() + 90 * 60000);
    const isLoko1930 = courtId === 7 && timeStr === '19:30';

    return {
      id: courtId * 1000 + idx + 1,
      court_id: courtId,
      start_time: start.toISOString(),
      end_time: end.toISOString(),
      price: courtId === 7 ? 3000 : basePrice,
      duration_minutes: 90,
      is_booked: isLoko1930 ? false : idx === 1 || idx === 3, // немного занятых для реализма
      status: isLoko1930 ? 'reserved' : idx === 1 || idx === 3 ? 'booked' : 'free',
      is_available: !isLoko1930 && idx !== 1 && idx !== 3,
    };
  });
}

export function getFallbackCourts(sport?: SportType | null): Court[] {
  if (!sport) return FALLBACK_COURTS;
  return FALLBACK_COURTS.filter((c) => c.sport_types.includes(sport));
}

export function getFallbackDetail(courtId: number): CourtDetail | null {
  const court = FALLBACK_COURTS.find((c) => c.id === courtId);
  if (!court) return null;

  const games: Game[] = FALLBACK_GAMES_BY_COURT[courtId] ? [...FALLBACK_GAMES_BY_COURT[courtId]] : [];
  const defects: Defect[] = FALLBACK_DEFECTS_BY_COURT[courtId] ? [...FALLBACK_DEFECTS_BY_COURT[courtId]] : [];

  return {
    ...court,
    games,
    defects,
  };
}

