import { rawRequest } from './client';

export interface WeatherInfo {
  temp_c: number;
  feels_like_c: number;
  description: string;
  icon: string;
  precipitation_chance: number;
  is_rain: boolean;
  summary: string;
  location?: string;
}

const DEFAULT_WEATHER: WeatherInfo = {
  temp_c: 14,
  feels_like_c: 13,
  description: 'Переменная облачность',
  icon: '⛅',
  precipitation_chance: 10,
  is_rain: false,
  summary: '+14°C, переменная облачность, без осадков',
  location: 'Санкт-Петербург',
};

const cache = new Map<string, { ts: number; data: WeatherInfo }>();
const CACHE_TTL = 10 * 60 * 1000; // 10 минут

export const weatherService = {
  async getWeather(lat: number = 59.9386, lon: number = 30.3141, timeIso?: string): Promise<WeatherInfo> {
    const key = `${lat.toFixed(2)}_${lon.toFixed(2)}_${timeIso ?? 'now'}`;
    const cached = cache.get(key);
    if (cached && Date.now() - cached.ts < CACHE_TTL) {
      return cached.data;
    }

    try {
      const data = await rawRequest<WeatherInfo>('/weather', {
        query: {
          lat,
          lon,
          time: timeIso,
        },
      });
      if (data && typeof data.temp_c === 'number') {
        cache.set(key, { ts: Date.now(), data });
        return data;
      }
    } catch {
      // Fallback
    }

    return DEFAULT_WEATHER;
  },
};
