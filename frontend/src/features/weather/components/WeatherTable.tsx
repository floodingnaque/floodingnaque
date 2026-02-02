/**
 * WeatherTable Component
 *
 * Sortable data table displaying detailed weather records.
 * Supports client-side sorting and loading states.
 */

import { useState, useMemo } from 'react';
import { format } from 'date-fns';
import { ArrowUpDown, ArrowUp, ArrowDown } from 'lucide-react';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { Badge } from '@/components/ui/badge';
import type { WeatherData, WeatherSource } from '@/types';

interface WeatherTableProps {
  /** Weather data to display */
  data: WeatherData[];
  /** Loading state */
  isLoading?: boolean;
}

type SortField = 'recorded_at' | 'temperature' | 'humidity' | 'precipitation' | 'wind_speed' | 'pressure';
type SortOrder = 'asc' | 'desc';

interface SortState {
  field: SortField;
  order: SortOrder;
}

/**
 * Source badge color mapping
 */
const sourceColors: Record<WeatherSource, string> = {
  OWM: 'bg-orange-100 text-orange-800 hover:bg-orange-100',
  Manual: 'bg-gray-100 text-gray-800 hover:bg-gray-100',
  Meteostat: 'bg-blue-100 text-blue-800 hover:bg-blue-100',
  Google: 'bg-green-100 text-green-800 hover:bg-green-100',
};

/**
 * Convert Kelvin to Celsius
 */
function kelvinToCelsius(kelvin: number): number {
  return kelvin - 273.15;
}

/**
 * Format temperature for display
 */
function formatTemperature(kelvin: number): string {
  return `${kelvinToCelsius(kelvin).toFixed(1)}°C`;
}

/**
 * Table column headers configuration
 */
const columns: Array<{ key: SortField | 'source'; label: string; sortable: boolean }> = [
  { key: 'recorded_at', label: 'Date', sortable: true },
  { key: 'temperature', label: 'Temperature', sortable: true },
  { key: 'humidity', label: 'Humidity', sortable: true },
  { key: 'precipitation', label: 'Precipitation', sortable: true },
  { key: 'wind_speed', label: 'Wind Speed', sortable: true },
  { key: 'pressure', label: 'Pressure', sortable: true },
  { key: 'source', label: 'Source', sortable: false },
];

/**
 * Skeleton loading row component
 */
function TableRowSkeleton() {
  return (
    <TableRow>
      {columns.map((_, index) => (
        <TableCell key={index}>
          <Skeleton className="h-4 w-full" />
        </TableCell>
      ))}
    </TableRow>
  );
}

/**
 * WeatherTable component
 *
 * @example
 * <WeatherTable data={weatherData} isLoading={isLoading} />
 */
export function WeatherTable({ data, isLoading }: WeatherTableProps) {
  // Sort state
  const [sort, setSort] = useState<SortState>({
    field: 'recorded_at',
    order: 'desc',
  });

  // Handle sort click
  const handleSort = (field: SortField) => {
    setSort((prev) => ({
      field,
      order: prev.field === field && prev.order === 'desc' ? 'asc' : 'desc',
    }));
  };

  // Get sort icon for column
  const getSortIcon = (field: SortField) => {
    if (sort.field !== field) {
      return <ArrowUpDown className="ml-2 h-4 w-4" />;
    }
    return sort.order === 'asc' ? (
      <ArrowUp className="ml-2 h-4 w-4" />
    ) : (
      <ArrowDown className="ml-2 h-4 w-4" />
    );
  };

  // Sort data
  const sortedData = useMemo(() => {
    if (!data.length) return [];

    return [...data].sort((a, b) => {
      let comparison = 0;

      switch (sort.field) {
        case 'recorded_at':
          comparison = new Date(a.recorded_at).getTime() - new Date(b.recorded_at).getTime();
          break;
        case 'temperature':
          comparison = a.temperature - b.temperature;
          break;
        case 'humidity':
          comparison = a.humidity - b.humidity;
          break;
        case 'precipitation':
          comparison = a.precipitation - b.precipitation;
          break;
        case 'wind_speed':
          comparison = a.wind_speed - b.wind_speed;
          break;
        case 'pressure':
          comparison = a.pressure - b.pressure;
          break;
      }

      return sort.order === 'asc' ? comparison : -comparison;
    });
  }, [data, sort]);

  // Loading state
  if (isLoading) {
    return (
      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              {columns.map((column) => (
                <TableHead key={column.key}>{column.label}</TableHead>
              ))}
            </TableRow>
          </TableHeader>
          <TableBody>
            {Array.from({ length: 10 }).map((_, index) => (
              <TableRowSkeleton key={index} />
            ))}
          </TableBody>
        </Table>
      </div>
    );
  }

  // Empty state
  if (!data.length) {
    return (
      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              {columns.map((column) => (
                <TableHead key={column.key}>{column.label}</TableHead>
              ))}
            </TableRow>
          </TableHeader>
          <TableBody>
            <TableRow>
              <TableCell colSpan={columns.length} className="h-24 text-center">
                <div className="text-muted-foreground">
                  No weather data available for the selected period
                </div>
              </TableCell>
            </TableRow>
          </TableBody>
        </Table>
      </div>
    );
  }

  return (
    <div className="rounded-md border">
      <Table>
        <TableHeader>
          <TableRow>
            {columns.map((column) => (
              <TableHead key={column.key}>
                {column.sortable ? (
                  <Button
                    variant="ghost"
                    onClick={() => handleSort(column.key as SortField)}
                    className="h-8 px-2 -ml-2 font-medium"
                  >
                    {column.label}
                    {getSortIcon(column.key as SortField)}
                  </Button>
                ) : (
                  column.label
                )}
              </TableHead>
            ))}
          </TableRow>
        </TableHeader>
        <TableBody>
          {sortedData.map((item) => (
            <TableRow key={item.id}>
              <TableCell>
                {format(new Date(item.recorded_at), 'MMM dd, yyyy HH:mm')}
              </TableCell>
              <TableCell>{formatTemperature(item.temperature)}</TableCell>
              <TableCell>{item.humidity.toFixed(1)}%</TableCell>
              <TableCell>{item.precipitation.toFixed(2)} mm</TableCell>
              <TableCell>{item.wind_speed.toFixed(1)} m/s</TableCell>
              <TableCell>{item.pressure.toFixed(0)} hPa</TableCell>
              <TableCell>
                <Badge variant="secondary" className={sourceColors[item.source]}>
                  {item.source}
                </Badge>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}

export default WeatherTable;
