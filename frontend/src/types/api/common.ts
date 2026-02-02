export interface ApiResponse<T> {
  success: boolean;
  data: T;
  message?: string;
  request_id: string;
}

export interface ApiError {
  code: string;
  message: string;
  status?: number;
  details?: Record<string, unknown>;
  field_errors?: FieldError[];
  retry_after?: number;
  timestamp?: string;
}

export interface FieldError {
  field: string;
  message: string;
}

export interface PaginatedResponse<T> {
  success: boolean;
  data: T[];
  total: number;
  page: number;
  limit: number;
  pages: number;
  request_id: string;
}

export interface PaginationParams {
  limit?: number;
  page?: number;
  sort_by?: string;
  order?: 'asc' | 'desc';
}

export interface DateRangeParams {
  start_date?: string;
  end_date?: string;
}
