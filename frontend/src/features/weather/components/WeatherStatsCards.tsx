/**
 * WeatherStatsCards Component
 *
 * Displays aggregated weather statistics in a responsive grid of metric cards.
 * Shows temperature, humidity, precipitation, wind speed, and record count.
 */

import { Thermometer, Droplets, CloudRain, Wind, Database } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { formatTemperature } from '@/features/flooding/utils/temperature';
import type { WeatherStats } from '@/types';

interface WeatherStatsCardsProps {
  /** Weather statistics data */
  stats?: WeatherStats;
  /** Loading state */
  isLoading?: boolean;
}

/**
 * Individual stat card configuration
 */
interface StatCardConfig {
  title: string;
  icon: React.ElementType;
  getValue: (stats: WeatherStats) => string;
  iconColor: string;
}

/**
 * Configuration for all stat cards
 */
const statCards: StatCardConfig[] = [
  {
    title: 'Avg Temperature',
    icon: Thermometer,
    getValue: (stats) => formatTemperature(stats.avg_temperature, 'C'),
    iconColor: 'text-orange-500',
  },
  {
    title: 'Avg Humidity',
    icon: Droplets,
    getValue: (stats) => `${stats.avg_humidity.toFixed(1)}%`,
    iconColor: 'text-blue-500',
  },
  {
    title: 'Total Precipitation',
    icon: CloudRain,
    getValue: (stats) => `${stats.total_precipitation.toFixed(2)} mm`,
    iconColor: 'text-cyan-500',
  },
  {
    title: 'Avg Wind Speed',
    icon: Wind,
    getValue: (stats) => `${stats.avg_wind_speed.toFixed(1)} m/s`,
    iconColor: 'text-gray-500',
  },
  {
    title: 'Record Count',
    icon: Database,
    getValue: (stats) => stats.record_count.toLocaleString(),
    iconColor: 'text-purple-500',
  },
];

/**
 * Skeleton loading card component
 */
function StatCardSkeleton() {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <Skeleton className="h-4 w-24" />
        <Skeleton className="h-4 w-4 rounded" />
      </CardHeader>
      <CardContent>
        <Skeleton className="h-8 w-20" />
      </CardContent>
    </Card>
  );
}

/**
 * WeatherStatsCards component
 *
 * @example
 * <WeatherStatsCards stats={weatherStats} isLoading={isLoadingStats} />
 */
export function WeatherStatsCards({ stats, isLoading }: WeatherStatsCardsProps) {
  // Show skeleton cards while loading
  if (isLoading) {
    return (
      <div className="grid gap-4 grid-cols-1 sm:grid-cols-2 lg:grid-cols-5">
        {statCards.map((_, index) => (
          <StatCardSkeleton key={index} />
        ))}
      </div>
    );
  }

  // Show placeholder when no stats available
  if (!stats) {
    return (
      <div className="grid gap-4 grid-cols-1 sm:grid-cols-2 lg:grid-cols-5">
        {statCards.map((config, index) => {
          const Icon = config.icon;
          return (
            <Card key={index}>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  {config.title}
                </CardTitle>
                <Icon className={`h-4 w-4 ${config.iconColor}`} />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-muted-foreground">--</div>
              </CardContent>
            </Card>
          );
        })}
      </div>
    );
  }

  return (
    <div className="grid gap-4 grid-cols-1 sm:grid-cols-2 lg:grid-cols-5">
      {statCards.map((config, index) => {
        const Icon = config.icon;
        return (
          <Card key={index}>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">
                {config.title}
              </CardTitle>
              <Icon className={`h-4 w-4 ${config.iconColor}`} />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {config.getValue(stats)}
              </div>
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}

export default WeatherStatsCards;
