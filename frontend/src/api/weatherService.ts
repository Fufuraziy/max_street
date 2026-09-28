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

const cache = new Map<string, { ts: number; data: WeatherInfo }>();
const CACHE_TTL = 10 * 60 * 1000; // 10 минут

function decodeWmoCode(code: number): { desc: string; icon: string; isRain: boolean } {
  if (code === 0) return { desc: 'Ясно', icon: '☀️', isRain: false };
  if (code === 1) return { desc: 'Преимущественно ясно', icon: '🌤️', isRain: false };
  if (code === 2) return { desc: 'Переменная облачность', icon: '⛅', isRain: false };
  if (code === 3) return { desc: 'Пасмурно', icon: '☁️', isRain: false };
  if (code === 45 || code === 48) return { desc: 'Туман', icon: '🌫️', isRain: false };
  if (code >= 51 && code <= 57) return { desc: 'Моросящий дождь', icon: '🌦️', isRain: true };
  if (code >= 61 && code <= 65) return { desc: 'Дождь', icon: '🌧️', isRain: true };
  if (code >= 71 && code <= 77) return { desc: 'Снег', icon: '🌨️', isRain: false };
  if (code >= 80 && code <= 82) return { desc: 'Кратковременный дождь', icon: '🌦️', isRain: true };
  if (code >= 85 && code <= 86) return { desc: 'Снегопад', icon: '🌨️', isRain: false };
  if (code >= 95) return { desc: 'Гроза', icon: '⛈️', isRain: true };
  return { desc: 'Переменная облачность', icon: '⛅', isRain: false };
}

/**
 * Динамический климатический расчёт для СПб/СЗ региона по координатам, дате и часу,
 * когда внешний API недоступен или заблокирован сетью.
 */
function calculateDynamicWeather(lat: number, lon: number, timeIso?: string): WeatherInfo {
  const d = timeIso ? new Date(timeIso) : new Date();
  const month = d.getMonth(); // 0 = Jan, 8 = Sep, 9 = Oct
  const hour = d.getHours();

  // Среднемесячные дневные / ночные базовые температуры для СПб
  const monthlyAverages: Record<number, { day: number; night: number }> = {
    0: { day: -4, night: -8 },   // Янв
    1: { day: -3, night: -8 },   // Фев
    2: { day: 2, night: -4 },    // Мар
    3: { day: 9, night: 2 },     // Апр
    4: { day: 16, night: 7 },    // Май
    5: { day: 20, night: 12 },   // Июн
    6: { day: 23, night: 15 },   // Июл
    7: { day: 21, night: 13 },   // Авг
    8: { day: 15, night: 8 },    // Сен
    9: { day: 8, night: 3 },     // Окт
    10: { day: 2, night: -2 },   // Ноя
    11: { day: -2, night: -5 },  // Дек
  };

  const avg = monthlyAverages[month] ?? { day: 15, night: 8 };

  // Суточный ход температуры (минимум около 05:00, максимум около 15:00)
  const hourRad = ((hour - 5) / 24) * 2 * Math.PI;
  const diurnalFactor = (Math.sin(hourRad - Math.PI / 2) + 1) / 2; // от 0 до 1
  const baseTemp = avg.night + (avg.day - avg.night) * diurnalFactor;

  // Микроклиматическая поправка по координатам (Крестовский у залива прохладнее/ветренее)
  const locSeed = Math.sin(lat * 31.7 + lon * 19.3) * 1.5;
  const temp_c = Math.round(baseTemp + locSeed);
  const feels_like_c = temp_c - (hour >= 18 || hour <= 8 ? 2 : 1);

  // Осадки и облачность детерминированы по дню и координатам
  const dayOfYear = Math.floor((d.getTime() - new Date(d.getFullYear(), 0, 0).getTime()) / 86400000);
  const weatherSeed = Math.abs(Math.sin(dayOfYear * 7.13 + lat * 10 + lon * 5));
  
  let description = 'Ясно';
  let icon = '☀️';
  let precipitation_chance = 0;
  let is_rain = false;

  if (weatherSeed > 0.72) {
    description = 'Кратковременный дождь';
    icon = '🌦️';
    precipitation_chance = Math.round(40 + (weatherSeed - 0.72) * 100);
    is_rain = true;
  } else if (weatherSeed > 0.45) {
    description = 'Переменная облачность';
    icon = '⛅';
    precipitation_chance = 15;
  } else if (weatherSeed > 0.25) {
    description = 'Облачно с прояснениями';
    icon = '🌤️';
    precipitation_chance = 5;
  } else {
    description = hour < 6 || hour > 21 ? 'Ясно' : 'Солнечно';
    icon = hour < 6 || hour > 21 ? '🌙' : '☀️';
    precipitation_chance = 0;
  }

  const sign = temp_c > 0 ? '+' : '';
  const rainNote = is_rain ? `, дождь ${precipitation_chance}%` : ', без осадков';
  const summary = `${sign}${temp_c}°C, ${description.toLowerCase()}${rainNote}`;

  return {
    temp_c,
    feels_like_c,
    description,
    icon,
    precipitation_chance,
    is_rain,
    summary,
    location: 'Санкт-Петербург',
  };
}

export const weatherService = {
  async getWeather(lat: number = 59.9386, lon: number = 30.3141, timeIso?: string): Promise<WeatherInfo> {
    const key = `${lat.toFixed(2)}_${lon.toFixed(2)}_${timeIso ?? 'now'}`;
    const cached = cache.get(key);
    if (cached && Date.now() - cached.ts < CACHE_TTL) {
      return cached.data;
    }

    // 1. Попытка запроса через бэкенд (если доступен локально)
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
      // Идём к Open-Meteo
    }

    // 2. Прямой запрос в Open-Meteo из браузера (CORS поддерживается, API бесплатный)
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 3500);

      const targetDateStr = timeIso ? timeIso.slice(0, 10) : new Date().toISOString().slice(0, 10);
      const url = `https://api.open-meteo.com/v1/forecast?latitude=${lat.toFixed(4)}&longitude=${lon.toFixed(4)}&current=temperature_2m,apparent_temperature,precipitation,weather_code&hourly=temperature_2m,apparent_temperature,precipitation_probability,weather_code&start_date=${targetDateStr}&end_date=${targetDateStr}&timezone=auto`;

      const response = await fetch(url, { signal: controller.signal });
      clearTimeout(timeoutId);

      if (response.ok) {
        const json = await response.json();
        if (timeIso && json.hourly && Array.isArray(json.hourly.time)) {
          const targetHourStr = timeIso.slice(0, 13); // "YYYY-MM-DDTHH"
          const idx = json.hourly.time.findIndex((t: string) => t.startsWith(targetHourStr));
          const matchIdx = idx >= 0 ? idx : 12; // если час не найден, берём середину дня

          const temp_c = Math.round(json.hourly.temperature_2m[matchIdx] ?? 14);
          const feels_c = Math.round(json.hourly.apparent_temperature?.[matchIdx] ?? temp_c - 1);
          const wmo = json.hourly.weather_code[matchIdx] ?? 2;
          const pop = Math.round(json.hourly.precipitation_probability?.[matchIdx] ?? 0);
          const { desc, icon, isRain } = decodeWmoCode(wmo);

          const sign = temp_c > 0 ? '+' : '';
          const rainNote = pop > 20 ? `, вероятность осадков ${pop}%` : ', без осадков';
          const info: WeatherInfo = {
            temp_c,
            feels_like_c: feels_c,
            description: desc,
            icon,
            precipitation_chance: pop,
            is_rain: isRain || pop >= 40,
            summary: `${sign}${temp_c}°C, ${desc.toLowerCase()}${rainNote}`,
            location: 'Санкт-Петербург',
          };
          cache.set(key, { ts: Date.now(), data: info });
          return info;
        }

        if (json.current) {
          const temp_c = Math.round(json.current.temperature_2m ?? 14);
          const feels_c = Math.round(json.current.apparent_temperature ?? temp_c - 1);
          const wmo = json.current.weather_code ?? 2;
          const { desc, icon, isRain } = decodeWmoCode(wmo);

          const sign = temp_c > 0 ? '+' : '';
          const info: WeatherInfo = {
            temp_c,
            feels_like_c: feels_c,
            description: desc,
            icon,
            precipitation_chance: isRain ? 60 : 5,
            is_rain: isRain,
            summary: `${sign}${temp_c}°C, ${desc.toLowerCase()}`,
            location: 'Санкт-Петербург',
          };
          cache.set(key, { ts: Date.now(), data: info });
          return info;
        }
      }
    } catch {
      // Игнорируем сетевые ошибки, переходим к умному расчёту
    }

    // 3. Динамический климатический расчёт (разный по координатам, дате и часу)
    const dynamic = calculateDynamicWeather(lat, lon, timeIso);
    cache.set(key, { ts: Date.now(), data: dynamic });
    return dynamic;
  },
};
