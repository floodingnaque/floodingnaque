/**
 * PredictionResult Component
 *
 * Displays the complete prediction result including risk level,
 * model details, and action buttons.
 */

import { Clock, RefreshCw, History, Info, Hash } from 'lucide-react';
import { Link } from 'react-router-dom';

import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';

import { RiskDisplay } from './RiskDisplay';
import type { PredictionResponse } from '@/types';

/**
 * PredictionResult component props
 */
interface PredictionResultProps {
  /** Prediction response data */
  result: PredictionResponse;
  /** Callback to reset and make another prediction */
  onReset?: () => void;
}

/**
 * Format timestamp for display
 */
function formatTimestamp(timestamp: string): string {
  const date = new Date(timestamp);
  return date.toLocaleString('en-US', {
    dateStyle: 'medium',
    timeStyle: 'short',
  });
}

/**
 * PredictionResult displays the prediction outcome and details
 */
export function PredictionResult({ result, onReset }: PredictionResultProps) {
  return (
    <div className="w-full max-w-2xl mx-auto space-y-6 animate-in fade-in duration-300">
      {/* Risk Display - Prominent */}
      <RiskDisplay
        riskLevel={result.risk_level}
        probability={result.probability}
      />

      {/* Details Card */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Info className="h-5 w-5 text-muted-foreground" />
            <CardTitle className="text-lg">Prediction Details</CardTitle>
          </div>
          <CardDescription>
            Technical information about this prediction
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Model Version & Timestamp */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="space-y-1">
              <p className="text-sm font-medium text-muted-foreground">
                Model Version
              </p>
              <p className="font-mono text-sm">{result.model_version}</p>
            </div>
            <div className="space-y-1">
              <p className="text-sm font-medium text-muted-foreground flex items-center gap-1">
                <Clock className="h-3 w-3" />
                Timestamp
              </p>
              <p className="text-sm">{formatTimestamp(result.timestamp)}</p>
            </div>
          </div>

          <Separator />

          {/* Features Used */}
          <div className="space-y-2">
            <p className="text-sm font-medium text-muted-foreground">
              Features Used
            </p>
            <div className="flex flex-wrap gap-2">
              {result.features_used.map((feature) => (
                <Badge key={feature} variant="secondary">
                  {feature}
                </Badge>
              ))}
            </div>
          </div>

          <Separator />

          {/* Request ID */}
          <div className="space-y-1">
            <p className="text-sm font-medium text-muted-foreground flex items-center gap-1">
              <Hash className="h-3 w-3" />
              Request ID
            </p>
            <p className="font-mono text-xs text-muted-foreground">
              {result.request_id}
            </p>
          </div>

          {/* Additional Stats */}
          <div className="grid grid-cols-2 gap-4 pt-2">
            <div className="text-center p-3 bg-muted rounded-lg">
              <p className="text-2xl font-bold">
                {Math.round(result.confidence * 100)}%
              </p>
              <p className="text-xs text-muted-foreground">Confidence</p>
            </div>
            <div className="text-center p-3 bg-muted rounded-lg">
              <p className="text-2xl font-bold">{result.prediction}</p>
              <p className="text-xs text-muted-foreground">
                Raw Prediction
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Action Buttons */}
      <div className="flex flex-col sm:flex-row gap-3">
        <Button
          onClick={onReset}
          variant="default"
          size="lg"
          className="flex-1"
        >
          <RefreshCw className="mr-2 h-4 w-4" />
          Make Another Prediction
        </Button>
        <Button
          asChild
          variant="outline"
          size="lg"
          className="flex-1"
        >
          <Link to="/history">
            <History className="mr-2 h-4 w-4" />
            View History
          </Link>
        </Button>
      </div>
    </div>
  );
}

export default PredictionResult;
