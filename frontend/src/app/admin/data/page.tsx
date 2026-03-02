/**
 * Admin Dataset Management Page
 *
 * Upload, validate, and ingest CSV/Excel weather data into the system.
 * Provides file upload with preview, validation feedback, and
 * links to existing data export capabilities.
 */

import { useState, useRef, useCallback } from 'react';
import {
  Database,
  Upload,
  FileText,
  CheckCircle,
  AlertTriangle,
  Loader2,
  Download,
  Trash2,
  Eye,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Separator } from '@/components/ui/separator';
import { cn } from '@/lib/utils';
import { toast } from 'sonner';
import api from '@/lib/api-client';
import { API_ENDPOINTS } from '@/config/api.config';

interface UploadResult {
  success: boolean;
  message?: string;
  data?: {
    records_processed?: number;
    records_inserted?: number;
    errors?: string[];
    warnings?: string[];
  };
}

interface ValidationResult {
  success: boolean;
  data?: {
    valid: boolean;
    records: number;
    errors: string[];
    warnings: string[];
    sample?: Record<string, unknown>[];
  };
}

export default function AdminDataPage() {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [validating, setValidating] = useState(false);
  const [validation, setValidation] = useState<ValidationResult | null>(null);
  const [uploadResult, setUploadResult] = useState<UploadResult | null>(null);

  const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const ext = file.name.split('.').pop()?.toLowerCase();
    if (!['csv', 'xlsx', 'xls'].includes(ext ?? '')) {
      toast.error('Only CSV and Excel files are supported');
      return;
    }

    setSelectedFile(file);
    setValidation(null);
    setUploadResult(null);
  }, []);

  const handleValidate = useCallback(async () => {
    if (!selectedFile) return;
    setValidating(true);
    setValidation(null);

    try {
      const formData = new FormData();
      formData.append('file', selectedFile);

      const result = await api.post<ValidationResult>(
        `${API_ENDPOINTS.admin.upload}/validate`,
        formData,
        { headers: { 'Content-Type': 'multipart/form-data' } },
      );
      setValidation(result);

      if (result.data?.valid) {
        toast.success(`Validation passed: ${result.data.records} records`);
      } else {
        toast.error(`Validation failed with ${result.data?.errors?.length ?? 0} error(s)`);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Validation failed';
      toast.error(msg);
    } finally {
      setValidating(false);
    }
  }, [selectedFile]);

  const handleUpload = useCallback(async () => {
    if (!selectedFile) return;
    setUploading(true);
    setUploadResult(null);

    try {
      const formData = new FormData();
      formData.append('file', selectedFile);

      const ext = selectedFile.name.split('.').pop()?.toLowerCase();
      const endpoint = ext === 'csv'
        ? `${API_ENDPOINTS.admin.upload}/csv`
        : `${API_ENDPOINTS.admin.upload}/excel`;

      const result = await api.post<UploadResult>(endpoint, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });

      setUploadResult(result);
      if (result.success) {
        toast.success(
          `Uploaded successfully: ${result.data?.records_inserted ?? 0} records ingested`,
        );
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Upload failed';
      toast.error(msg);
    } finally {
      setUploading(false);
    }
  }, [selectedFile]);

  const handleClear = useCallback(() => {
    setSelectedFile(null);
    setValidation(null);
    setUploadResult(null);
    if (fileInputRef.current) fileInputRef.current.value = '';
  }, []);

  const handleDownloadTemplate = useCallback(async () => {
    try {
      const blob = await api.get<Blob>(`${API_ENDPOINTS.admin.upload}/template`, {
        responseType: 'blob',
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'upload_template.csv';
      a.click();
      URL.revokeObjectURL(url);
      toast.success('Template downloaded');
    } catch {
      toast.error('Failed to download template');
    }
  }, []);

  return (
    <div className="container mx-auto px-4 py-6 space-y-6">
      {/* Header */}
      <header className="flex items-center gap-3">
        <div className="p-2 rounded-lg bg-primary/10">
          <Database className="h-6 w-6 text-primary" />
        </div>
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Dataset Management</h1>
          <p className="text-sm text-muted-foreground">
            Upload, validate, and ingest weather observation data
          </p>
        </div>
      </header>

      {/* Upload Section */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Upload className="h-4 w-4" />
            Upload Weather Data
          </CardTitle>
          <CardDescription>
            Upload CSV or Excel files containing weather observations. Files are validated
            before ingestion into the database.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* File Input */}
          <div className="flex items-center gap-3">
            <input
              ref={fileInputRef}
              type="file"
              accept=".csv,.xlsx,.xls"
              onChange={handleFileSelect}
              className="hidden"
            />
            <Button
              variant="outline"
              onClick={() => fileInputRef.current?.click()}
            >
              <FileText className="h-4 w-4 mr-2" />
              Select File
            </Button>
            <Button variant="ghost" size="sm" onClick={handleDownloadTemplate}>
              <Download className="h-4 w-4 mr-2" />
              Download Template
            </Button>
          </div>

          {/* Selected File Info */}
          {selectedFile && (
            <div className="flex items-center justify-between p-3 rounded-lg border bg-muted/30">
              <div className="flex items-center gap-3">
                <FileText className="h-5 w-5 text-muted-foreground" />
                <div>
                  <p className="font-medium text-sm">{selectedFile.name}</p>
                  <p className="text-xs text-muted-foreground">
                    {(selectedFile.size / 1024).toFixed(1)} KB
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleValidate}
                  disabled={validating}
                >
                  {validating ? (
                    <Loader2 className="h-4 w-4 animate-spin mr-2" />
                  ) : (
                    <Eye className="h-4 w-4 mr-2" />
                  )}
                  Validate
                </Button>
                <Button
                  size="sm"
                  onClick={handleUpload}
                  disabled={uploading}
                >
                  {uploading ? (
                    <Loader2 className="h-4 w-4 animate-spin mr-2" />
                  ) : (
                    <Upload className="h-4 w-4 mr-2" />
                  )}
                  Upload
                </Button>
                <Button variant="ghost" size="icon" className="h-8 w-8" onClick={handleClear}>
                  <Trash2 className="h-4 w-4" />
                </Button>
              </div>
            </div>
          )}

          <Separator />

          {/* Validation Results */}
          {validation && (
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                {validation.data?.valid ? (
                  <Badge className="bg-green-50 text-green-700 border-green-300" variant="outline">
                    <CheckCircle className="h-3 w-3 mr-1" /> Valid
                  </Badge>
                ) : (
                  <Badge className="bg-red-50 text-red-700 border-red-300" variant="outline">
                    <AlertTriangle className="h-3 w-3 mr-1" /> Invalid
                  </Badge>
                )}
                <span className="text-sm text-muted-foreground">
                  {validation.data?.records ?? 0} records found
                </span>
              </div>

              {/* Errors */}
              {validation.data?.errors && validation.data.errors.length > 0 && (
                <div className="rounded-lg border border-red-200 bg-red-50/50 p-3 space-y-1">
                  <p className="text-sm font-medium text-red-700">
                    {validation.data.errors.length} error(s)
                  </p>
                  <ul className="text-xs text-red-600 space-y-0.5 max-h-40 overflow-y-auto">
                    {validation.data.errors.map((e, i) => (
                      <li key={i}>{e}</li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Warnings */}
              {validation.data?.warnings && validation.data.warnings.length > 0 && (
                <div className="rounded-lg border border-amber-200 bg-amber-50/50 p-3 space-y-1">
                  <p className="text-sm font-medium text-amber-700">
                    {validation.data.warnings.length} warning(s)
                  </p>
                  <ul className="text-xs text-amber-600 space-y-0.5 max-h-40 overflow-y-auto">
                    {validation.data.warnings.map((w, i) => (
                      <li key={i}>{w}</li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Preview */}
              {validation.data?.sample && validation.data.sample.length > 0 && (
                <div>
                  <p className="text-sm font-medium mb-2">Preview (first rows)</p>
                  <div className="overflow-x-auto rounded border">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          {Object.keys(validation.data.sample[0]).map((col) => (
                            <TableHead key={col} className="text-xs whitespace-nowrap">
                              {col}
                            </TableHead>
                          ))}
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {validation.data.sample.map((row, i) => (
                          <TableRow key={i}>
                            {Object.values(row).map((val, j) => (
                              <TableCell key={j} className="text-xs">
                                {String(val ?? '')}
                              </TableCell>
                            ))}
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Upload Result */}
          {uploadResult && (
            <div className={cn(
              'rounded-lg border p-4 space-y-2',
              uploadResult.success
                ? 'border-green-200 bg-green-50/50'
                : 'border-red-200 bg-red-50/50',
            )}>
              <div className="flex items-center gap-2">
                {uploadResult.success ? (
                  <CheckCircle className="h-5 w-5 text-green-600" />
                ) : (
                  <AlertTriangle className="h-5 w-5 text-red-600" />
                )}
                <p className="font-medium text-sm">
                  {uploadResult.success ? 'Upload Successful' : 'Upload Failed'}
                </p>
              </div>
              {uploadResult.data?.records_inserted != null && (
                <p className="text-sm text-muted-foreground">
                  {uploadResult.data.records_inserted} of {uploadResult.data.records_processed ?? 0} records ingested
                </p>
              )}
              {uploadResult.data?.errors && uploadResult.data.errors.length > 0 && (
                <ul className="text-xs text-red-600 space-y-0.5">
                  {uploadResult.data.errors.slice(0, 10).map((e, i) => (
                    <li key={i}>{e}</li>
                  ))}
                </ul>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Data Export Quick Links */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Download className="h-4 w-4" />
            Data Export
          </CardTitle>
          <CardDescription>
            Download existing datasets in CSV format
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-3 sm:grid-cols-3">
            {[
              { label: 'Weather Data', endpoint: API_ENDPOINTS.export.weather },
              { label: 'Predictions', endpoint: API_ENDPOINTS.export.predictions },
              { label: 'Alerts', endpoint: API_ENDPOINTS.export.alerts },
            ].map(({ label, endpoint }) => (
              <Button
                key={label}
                variant="outline"
                className="justify-start"
                onClick={async () => {
                  try {
                    const blob = await api.get<Blob>(endpoint, { responseType: 'blob' });
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = `${label.toLowerCase().replace(/\s/g, '_')}.csv`;
                    a.click();
                    URL.revokeObjectURL(url);
                    toast.success(`${label} exported`);
                  } catch {
                    toast.error(`Failed to export ${label.toLowerCase()}`);
                  }
                }}
              >
                <Download className="h-4 w-4 mr-2" />
                {label}
              </Button>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
