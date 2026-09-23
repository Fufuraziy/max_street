export type SportType = 'basketball' | 'football' | 'volleyball' | 'table_tennis' | 'workout';
export type SurfaceType = 'rubber' | 'asphalt' | 'artificial_turf';
export type GameStatus = 'recruiting' | 'confirmed' | 'finished' | 'cancelled';
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
  rating: number;
  description: string;
  active_games_today: number;
}

export interface Participant {
  user_max_id: string;
  user_name: string;
  joined_at: string;
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
  start_time: string;
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
