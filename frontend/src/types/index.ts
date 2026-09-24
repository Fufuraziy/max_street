export type SportType =
  | 'basketball'
  | 'football'
  | 'volleyball'
  | 'table_tennis'
  | 'workout'
  | 'tennis'
export type SurfaceType =
  | 'rubber'
  | 'asphalt'
  | 'artificial_turf'
  | 'hard'
  | 'parquet'
  | 'acrylic'
  | 'artificial_grass'
  | 'panoramic_glass_turf'
  | 'padel_turf'
  | 'clay'
  | 'tera_flex'
  | string;
export type GameStatus = 'recruiting' | 'confirmed' | 'booked' | 'finished' | 'cancelled';
export type PaymentStatus = 'pending' | 'funded' | 'paid_to_court' | 'refunded';
export type SlotStatus = 'free' | 'reserved' | 'booked';
export type DefectType = 'broken_ring' | 'surface_damage' | 'lighting_broken' | 'net_missing' | 'trash';
export type DefectStatus = 'reported' | 'sent_to_city' | 'resolved';

export interface Court {
  id: number;
  title: string;
  sport_types: SportType[];
  address: string;
  latitude: number;
  longitude: number;
  surface_type: SurfaceType;
  has_lighting: boolean;
  is_indoor: boolean;
  is_commercial: boolean;
  rating: number;
  description: string;
  active_games_today: number;
  price_from: number | null;
}

export interface Participant {
  user_max_id: string;
  user_name: string;
  joined_at: string;
  has_paid: boolean;
  paid_amount: number;
  paid_at: string | null;
}

export interface SlotBrief {
  id: number;
  start_time: string;
  end_time: string;
  price: number;
  duration_minutes: number;
}

export interface Slot extends SlotBrief {
  court_id: number;
  is_booked: boolean;
  status: SlotStatus;
  is_available: boolean;
}

export interface Game {
  id: number;
  court_id: number;
  creator_max_id: string;
  sport_type: SportType;
  start_time: string;
  required_players: number;
  current_players: number;
  status: GameStatus;
  status_label: string;
  comment: string;
  created_at: string;
  participants: Participant[];
  spots_left: number;
  slot_id: number | null;
  slot: SlotBrief | null;
  escrow_account_id: string | null;
  total_cost: number;
  collected_amount: number;
  payment_status: PaymentStatus;
  payment_status_label: string | null;
  payment_deadline: string | null;
  booking_reference: string | null;
  is_paid: boolean;
  share_amount: number;
  paid_count: number;
}

export interface GameCourt {
  id: number;
  title: string;
  address: string;
  latitude: number;
  longitude: number;
}

export interface GameWithCourt extends Game {
  court: GameCourt;
}

export interface Defect {
  id: number;
  court_id: number;
  defect_type: DefectType;
  defect_label: string;
  description: string;
  status: DefectStatus;
  status_label: string;
  created_at: string;
}

export interface CourtDetail extends Court {
  games: Game[];
  defects: Defect[];
}

export interface JoinResponse {
  game: GameWithCourt;
  joined: boolean;
  confirmed: boolean;
  message: string;
}

export interface LeaveResponse {
  game: GameWithCourt;
  message: string;
}

export interface EscrowTransaction {
  reference: string;
  kind: 'deposit' | 'payout' | 'refund';
  amount: number;
  method: string;
  user_max_id: string | null;
  created_at: string;
}

export interface PayResponse {
  game: GameWithCourt;
  transaction: EscrowTransaction;
  booked: boolean;
  booking_reference: string | null;
  message: string;
}

export interface BotInfo {
  enabled: boolean;
  connected: boolean;
  mode: string;
  name: string | null;
  username: string | null;
  deep_link: string | null;
  miniapp_url: string;
}

export interface Identity {
  maxUserId: string;
  name: string;
  username: string | null;
  isGuest: boolean;
}

export interface CreateGamePayload {
  court_id: number;
  sport_type: SportType;
  start_time?: string;
  slot_id?: number;
  required_players: number;
  comment: string;
  creator_max_id: string;
  creator_name: string;
  creator_username?: string | null;
}

export interface PlayerPayload {
  user_max_id: string;
  user_name: string;
  username?: string | null;
}

export interface PayPayload {
  user_max_id: string;
  user_name?: string | null;
  amount?: number;
  payment_method: 'sbp_mock';
}

export interface CreateCourtPayload {
  title: string;
  sport_types: SportType[];
  address: string;
  latitude: number;
  longitude: number;
  surface_type: SurfaceType;
  has_lighting: boolean;
  is_indoor: boolean;
  description: string;
}

export interface ReportDefectPayload {
  user_max_id: string;
  user_name?: string | null;
  defect_type: DefectType;
  description: string;
}
