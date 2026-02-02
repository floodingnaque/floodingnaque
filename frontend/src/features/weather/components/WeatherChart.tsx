/**
 * WeatherChart Component
 *
 * Interactive line/bar chart displaying weather data over time.
 * Shows temperature, humidity, and precipitation with dual Y-axes.
 */

import { useMemo } from 'react';
import { format } from 'date-fns';
import {
  ResponsiveContainer,
  ComposedChart,
  Line,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from 'recharts';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import type { WeatherData } from '@/types';

interface WeatherChartProps {
  /** Weather data to display */
  data: WeatherData[];
  /** Loading state */
  isLoading?: boolean;
  /** Chart title */
  title?: string;
}

/**
 * Custom tooltip component for the chart
 */
interface TooltipProps {
  active?: boolean;
  payload?: Array<{
    name: string;
    value: number;
    color: string;
    dataKey: string;
  }>;
  label?: string;
}

/**
 * Map data keys to color classes
 */
const colorClasses: Record<string, string> = {
  temperature: 'text-orange-500',
  humidity: 'text-cyan-500',
  precipitation: 'text-blue-500',
};

function CustomTooltip({ active, payload, label }: TooltipProps) {
  if (!active || !payload?.length) return null;

  return (
    <div className="bg-background border rounded-lg shadow-lg p-3">
      <p className="font-medium text-sm mb-2">{label}</p>
      {payload.map((entry, index) => (
        <p key={index} className={`text-sm ${colorClasses[entry.dataKey] || ''}`}>
          {entry.name}: {formatValue(entry.dataKey, entry.value)}
        </p>
      ))}
    </div>
  );
}

/**
 * Format values based on the data type
 */
function formatValue(key: string, value: number): string {
  switch (key) {
    case 'temperature':
      return `${value.toFixed(1)}°C`;
    case 'humidity':
      return `${value.toFixed(1)}%`;
    case 'precipitation':
      return `${value.toFixed(2)} mm`;
    default:
      return value.toString();
  }
}

/**
 * WeatherChart component
 *
 * @example
 * <WeatherChart data={weatherData} isLoading={isLoading} />
 */
export function WeatherChart({ data, isLoading, title = 'Weather Trends' }: WeatherChartProps) {
  // Transform data for the chart
  const chartData = useMemo(() => {
    return data.map((item) => ({
      ...item,
      // Format timestamp for display
      time: format(new Date(item.recorded_at), 'MMM dd HH:mm'),
      // Convert Kelvin to Celsius for display
      temperature: item.temperature - 273.15,
    }));
  }, [data]);

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>{title}</CardTitle>
        </CardHeader>
        <CardContent>
          <Skeleton className="h-[400px] w-full" />
        </CardContent>
      </Card>
    );
  }

  if (!data.length) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>{title}</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-[400px] flex items-center justify-center text-muted-foreground">
            No weather data available for the selected period
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={400}>
          <ComposedChart data={chartData} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
            
            {/* X-Axis with timestamps */}
            <XAxis
              dataKey="time"
              tick={{ fontSize: 12 }}
              tickLine={false}
              axisLine={false}
              className="text-muted-foreground"
            />
            
            {/* Left Y-Axis for Temperature and Humidity */}
            <YAxis
              yAxisId="left"
              tick={{ fontSize: 12 }}
              tickLine={false}
              axisLine={false}
              className="text-muted-foreground"
              label={{
                value: 'Temp (°C) / Humidity (%)',
                angle: -90,
                position: 'insideLeft',
                style: { textAnchor: 'middle', fontSize: 12 },
              }}
            />
            
            {/* Right Y-Axis for Precipitation */}
            <YAxis
              yAxisId="right"
              orientation="right"
              tick={{ fontSize: 12 }}
              tickLine={false}
              axisLine={false}
              className="text-muted-foreground"
              label={{
                value: 'Precipitation (mm)',
                angle: 90,
                position: 'insideRight',
                style: { textAnchor: 'middle', fontSize: 12 },
              }}
            />
            
            {/* Tooltip */}
            <Tooltip content={<CustomTooltip />} />
            
            {/* Legend */}
            <Legend
              wrapperStyle={{ paddingTop: '20px' }}
              formatter={(value) => <span className="text-sm">{value}</span>}
            />
            
            {/* Precipitation bars */}
            <Bar
              yAxisId="right"
              dataKey="precipitation"
              name="Precipitation"
              fill="#3b82f6"
              opacity={0.6}
              radius={[4, 4, 0, 0]}
            />
            
            {/* Temperature line */}
            <Line
              yAxisId="left"
              type="monotone"
              dataKey="temperature"
              name="Temperature"
              stroke="#f97316"
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 6 }}
            />
            
            {/* Humidity line */}
            <Line
              yAxisId="left"
              type="monotone"
              dataKey="humidity"
              name="Humidity"
              stroke="#06b6d4"
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 6 }}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}

export default WeatherChart;
