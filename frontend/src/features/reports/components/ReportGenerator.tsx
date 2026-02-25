/**
 * ReportGenerator Component
 *
 * Form component for configuring and generating reports in PDF or CSV format.
 * Supports date range selection and multiple report types.
 */

import { useState, useCallback } from 'react';
import { useForm, useWatch } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { FileText, Download, Loader2, Calendar, FileSpreadsheet } from 'lucide-react';
import { format } from 'date-fns';

import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { useReportExport } from '../hooks/useReports';
import type { ReportType } from '../services/reportsApi';

/**
 * Report type options
 */
const REPORT_TYPES: { value: ReportType; label: string; description: string }[] = [
  {
    value: 'predictions',
    label: 'Flood Predictions',
    description: 'Historical flood prediction data and analysis',
  },
  {
    value: 'weather',
    label: 'Weather Data',
    description: 'Weather observations and forecast data',
  },
  {
    value: 'alerts',
    label: 'Flood Alerts',
    description: 'Alert history and acknowledgement records',
  },
];

/**
 * Export format options
 */
const EXPORT_FORMATS: { value: 'pdf' | 'csv'; label: string; icon: typeof FileText }[] = [
  { value: 'pdf', label: 'PDF Document', icon: FileText },
  { value: 'csv', label: 'CSV Spreadsheet', icon: FileSpreadsheet },
];

/**
 * Form validation schema
 */
const reportFormSchema = z.object({
  reportType: z.enum(['predictions', 'weather', 'alerts']),
  format: z.enum(['pdf', 'csv']),
  startDate: z.string().optional(),
  endDate: z.string().optional(),
}).refine(
  (data) => {
    if (data.startDate && data.endDate) {
      return new Date(data.startDate) <= new Date(data.endDate);
    }
    return true;
  },
  {
    message: 'Start date must be before or equal to end date',
    path: ['endDate'],
  }
);

type ReportFormValues = z.infer<typeof reportFormSchema>;

export interface ReportGeneratorProps {
  /** Additional CSS classes */
  className?: string;
}

/**
 * ReportGenerator - Form for generating and downloading reports
 *
 * @example
 * <ReportGenerator />
 */
export function ReportGenerator({ className }: ReportGeneratorProps) {
  const { exportReport, isExporting } = useReportExport();
  const [selectedReportType, setSelectedReportType] = useState<ReportType>('predictions');

  const {
    register,
    handleSubmit,
    setValue,
    control,
    formState: { errors },
  } = useForm<ReportFormValues>({
    resolver: zodResolver(reportFormSchema),
    defaultValues: {
      reportType: 'predictions',
      format: 'pdf',
      startDate: '',
      endDate: '',
    },
  });

  const watchFormat = useWatch({ control, name: 'format' });

  // Handle form submission
  const onSubmit = useCallback(
    (data: ReportFormValues) => {
      exportReport(
        {
          report_type: data.reportType,
          start_date: data.startDate || undefined,
          end_date: data.endDate || undefined,
        },
        data.format
      );
    },
    [exportReport]
  );

  // Set quick date range
  const setQuickRange = useCallback(
    (days: number) => {
      const endDate = new Date();
      const startDate = new Date();
      startDate.setDate(startDate.getDate() - days);

      setValue('startDate', format(startDate, 'yyyy-MM-dd'));
      setValue('endDate', format(endDate, 'yyyy-MM-dd'));
    },
    [setValue]
  );

  return (
    <Card className={cn('w-full', className)}>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <FileText className="h-5 w-5" />
          Generate Report
        </CardTitle>
        <CardDescription>
          Configure and export reports in PDF or CSV format
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
          {/* Report Type Selection */}
          <div className="space-y-2">
            <Label htmlFor="reportType">Report Type</Label>
            <Select
              value={selectedReportType}
              onValueChange={(value: ReportType) => {
                setSelectedReportType(value);
                setValue('reportType', value);
              }}
            >
              <SelectTrigger id="reportType">
                <SelectValue placeholder="Select report type" />
              </SelectTrigger>
              <SelectContent>
                {REPORT_TYPES.map((type) => (
                  <SelectItem key={type.value} value={type.value}>
                    <div className="flex flex-col">
                      <span>{type.label}</span>
                      <span className="text-xs text-muted-foreground">
                        {type.description}
                      </span>
                    </div>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Export Format Selection */}
          <div className="space-y-2">
            <Label htmlFor="format">Export Format</Label>
            <Select
              value={watchFormat}
              onValueChange={(value: 'pdf' | 'csv') => setValue('format', value)}
            >
              <SelectTrigger id="format">
                <SelectValue placeholder="Select format" />
              </SelectTrigger>
              <SelectContent>
                {EXPORT_FORMATS.map((fmt) => (
                  <SelectItem key={fmt.value} value={fmt.value}>
                    <div className="flex items-center gap-2">
                      <fmt.icon className="h-4 w-4" />
                      <span>{fmt.label}</span>
                    </div>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Date Range */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <Label>Date Range (Optional)</Label>
              <div className="flex gap-2">
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={() => setQuickRange(7)}
                >
                  7 days
                </Button>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={() => setQuickRange(30)}
                >
                  30 days
                </Button>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={() => setQuickRange(90)}
                >
                  90 days
                </Button>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1">
                <Label htmlFor="startDate" className="text-xs text-muted-foreground">
                  Start Date
                </Label>
                <div className="relative">
                  <Calendar className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                  <Input
                    id="startDate"
                    type="date"
                    className="pl-10"
                    {...register('startDate')}
                  />
                </div>
              </div>
              <div className="space-y-1">
                <Label htmlFor="endDate" className="text-xs text-muted-foreground">
                  End Date
                </Label>
                <div className="relative">
                  <Calendar className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                  <Input
                    id="endDate"
                    type="date"
                    className="pl-10"
                    {...register('endDate')}
                  />
                </div>
                {errors.endDate && (
                  <p className="text-xs text-destructive">{errors.endDate.message}</p>
                )}
              </div>
            </div>
          </div>

          {/* Generate Button */}
          <Button type="submit" className="w-full" disabled={isExporting}>
            {isExporting ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Generating Report...
              </>
            ) : (
              <>
                <Download className="mr-2 h-4 w-4" />
                Generate & Download
              </>
            )}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}

export default ReportGenerator;
