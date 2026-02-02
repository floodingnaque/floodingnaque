/**
 * Weather Feature Module
 *
 * Barrel exports for the weather feature including services,
 * hooks, and components.
 */

// Services
export { weatherApi } from './services/weatherApi';

// Hooks
export {
  useWeatherData,
  useHourlyWeather,
  useWeatherStats,
  weatherKeys,
} from './hooks/useWeather';

// Components
export { WeatherStatsCards } from './components/WeatherStatsCards';
export { WeatherChart } from './components/WeatherChart';
export { WeatherTable } from './components/WeatherTable';
export { DateRangeFilter, type DateRange } from './components/DateRangeFilter';
