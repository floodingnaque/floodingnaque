/**
 * Admin AI Model Control Page
 *
 * ML model management: view current model info, trigger retraining,
 * check training status, compare versions, and rollback.
 * Reuses AnalyticsCharts and ModelManagement components.
 */

import { useState, useCallback } from 'react';
import {
  Brain,
  RefreshCw,
  Loader2,
  ArrowDownToLine,
  Activity,
  CheckCircle,
  Clock,
  AlertTriangle,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Skeleton } from '@/components/ui/skeleton';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { cn } from '@/lib/utils';
import { toast } from 'sonner';
import { useSystemHealth } from '@/features/admin/hooks/useAdmin';
import {
  useModels,
  useTriggerRetrain,
  useRollbackModel,
} from '@/features/admin/hooks/useAdmin';

export default function AdminModelsPage() {
  const [retrainDialogOpen, setRetrainDialogOpen] = useState(false);
  const [rollbackDialogOpen, setRollbackDialogOpen] = useState(false);
  const [rollbackVersion, setRollbackVersion] = useState('');
  const [taskId, setTaskId] = useState<string | null>(null);

  const { data: health, isLoading: healthLoading } = useSystemHealth();
  const { isLoading: modelsLoading } = useModels();
  const triggerRetrain = useTriggerRetrain();
  const rollback = useRollbackModel();

  const model = health?.model;
  const modelLoaded = health?.checks?.model_available ?? false;

  const handleRetrain = useCallback(() => {
    triggerRetrain.mutate(undefined, {
      onSuccess: (res) => {
        const tid = res.data?.task_id;
        if (tid) setTaskId(tid);
        toast.success('Retraining job queued successfully');
        setRetrainDialogOpen(false);
      },
      onError: () => toast.error('Failed to queue retraining job'),
    });
  }, [triggerRetrain]);

  const handleRollback = useCallback(() => {
    if (!rollbackVersion.trim()) {
      toast.error('Please enter a version identifier');
      return;
    }
    rollback.mutate(rollbackVersion.trim(), {
      onSuccess: (res) => {
        toast.success(res.message || `Rolled back to ${rollbackVersion}`);
        setRollbackDialogOpen(false);
        setRollbackVersion('');
      },
      onError: () => toast.error('Rollback failed'),
    });
  }, [rollback, rollbackVersion]);

  return (
    <div className="container mx-auto px-4 py-6 space-y-6">
      {/* Header */}
      <header className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-primary/10">
            <Brain className="h-6 w-6 text-primary" />
          </div>
          <div>
            <h1 className="text-2xl font-bold tracking-tight">AI Model Control</h1>
            <p className="text-sm text-muted-foreground">
              Manage the Random Forest flood prediction model
            </p>
          </div>
        </div>
        <div className="flex gap-2">
          <Button
            variant="outline"
            onClick={() => setRollbackDialogOpen(true)}
          >
            <ArrowDownToLine className="h-4 w-4 mr-2" />
            Rollback
          </Button>
          <Button onClick={() => setRetrainDialogOpen(true)}>
            <RefreshCw className="h-4 w-4 mr-2" />
            Retrain Model
          </Button>
        </div>
      </header>

      {/* Model Status */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardContent className="pt-4 pb-3">
            <div className="flex items-center gap-2 mb-1">
              {modelLoaded ? (
                <CheckCircle className="h-4 w-4 text-green-600" />
              ) : (
                <AlertTriangle className="h-4 w-4 text-red-600" />
              )}
              <span className="text-xs text-muted-foreground">Status</span>
            </div>
            {healthLoading ? (
              <Skeleton className="h-7 w-20" />
            ) : (
              <p className="text-xl font-bold">
                {modelLoaded ? 'Loaded' : 'Unavailable'}
              </p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-4 pb-3">
            <div className="flex items-center gap-2 mb-1">
              <Activity className="h-4 w-4 text-muted-foreground" />
              <span className="text-xs text-muted-foreground">Model Type</span>
            </div>
            {healthLoading ? (
              <Skeleton className="h-7 w-28" />
            ) : (
              <p className="text-xl font-bold">{model?.type ?? '---'}</p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-4 pb-3">
            <div className="flex items-center gap-2 mb-1">
              <Clock className="h-4 w-4 text-muted-foreground" />
              <span className="text-xs text-muted-foreground">Version</span>
            </div>
            {healthLoading ? (
              <Skeleton className="h-7 w-16" />
            ) : (
              <p className="text-xl font-bold">{model?.version ?? '---'}</p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-4 pb-3">
            <div className="flex items-center gap-2 mb-1">
              <Brain className="h-4 w-4 text-muted-foreground" />
              <span className="text-xs text-muted-foreground">Features</span>
            </div>
            {healthLoading ? (
              <Skeleton className="h-7 w-12" />
            ) : (
              <p className="text-xl font-bold">{model?.features_count ?? '---'}</p>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Performance Metrics */}
      {model?.metrics && Object.keys(model.metrics).length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Activity className="h-4 w-4" />
              Performance Metrics
            </CardTitle>
            <CardDescription>
              Current model accuracy and performance scores
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 sm:grid-cols-2 md:grid-cols-4">
              {Object.entries(model.metrics).map(([key, value]) => (
                <div key={key} className="space-y-1 p-3 rounded-lg bg-muted/30">
                  <p className="text-sm text-muted-foreground capitalize">
                    {key.replace(/_/g, ' ')}
                  </p>
                  <p className="text-2xl font-bold">
                    {typeof value === 'number'
                      ? value < 1
                        ? `${(value * 100).toFixed(1)}%`
                        : value.toFixed(2)
                      : String(value)}
                  </p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Model Details */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Brain className="h-4 w-4" />
            Model Details
          </CardTitle>
        </CardHeader>
        <CardContent>
          {modelsLoading || healthLoading ? (
            <div className="space-y-3">
              {Array.from({ length: 3 }).map((_, i) => (
                <Skeleton key={i} className="h-5 w-full" />
              ))}
            </div>
          ) : (
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">Created</span>
                <span className="font-medium">
                  {model?.created_at
                    ? new Date(model.created_at).toLocaleString()
                    : '---'}
                </span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">Feature Count</span>
                <span className="font-medium">{model?.features_count ?? '---'}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">Model File</span>
                <span className="font-medium">
                  {model?.version ? `flood_model_${model.version}.joblib` : '---'}
                </span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">Inference Status</span>
                <Badge
                  variant="outline"
                  className={cn(
                    'text-xs',
                    modelLoaded
                      ? 'bg-green-50 text-green-700 border-green-300'
                      : 'bg-red-50 text-red-700 border-red-300',
                  )}
                >
                  {modelLoaded ? 'Ready' : 'Not Loaded'}
                </Badge>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Task Status */}
      {taskId && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Loader2 className="h-4 w-4 animate-spin" />
              Retraining Task
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-3">
              <Badge variant="outline" className="bg-blue-50 text-blue-700 border-blue-300">
                In Progress
              </Badge>
              <span className="text-sm text-muted-foreground font-mono">{taskId}</span>
            </div>
            <p className="text-xs text-muted-foreground mt-2">
              The model is being retrained in the background. This may take several minutes.
            </p>
          </CardContent>
        </Card>
      )}

      {/* Retrain Confirmation */}
      <AlertDialog open={retrainDialogOpen} onOpenChange={setRetrainDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Retrain Model</AlertDialogTitle>
            <AlertDialogDescription>
              This will queue a full retraining of the Random Forest model using
              the latest ingested weather data. The current model will remain active
              until the new version is ready.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleRetrain}
              disabled={triggerRetrain.isPending}
            >
              {triggerRetrain.isPending && (
                <Loader2 className="h-4 w-4 animate-spin mr-2" />
              )}
              Start Retraining
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Rollback Dialog */}
      <AlertDialog open={rollbackDialogOpen} onOpenChange={setRollbackDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Rollback Model</AlertDialogTitle>
            <AlertDialogDescription>
              Load a previous model version for inference. The current model will be
              replaced immediately.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <div className="px-6 pb-2">
            <Label htmlFor="rollback-version" className="text-sm">
              Version identifier (e.g., v5, v6)
            </Label>
            <Input
              id="rollback-version"
              value={rollbackVersion}
              onChange={(e) => setRollbackVersion(e.target.value)}
              placeholder="v5"
              className="mt-1"
            />
          </div>
          <AlertDialogFooter>
            <AlertDialogCancel onClick={() => setRollbackVersion('')}>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleRollback}
              disabled={rollback.isPending || !rollbackVersion.trim()}
              className="bg-amber-600 hover:bg-amber-700"
            >
              {rollback.isPending && (
                <Loader2 className="h-4 w-4 animate-spin mr-2" />
              )}
              Rollback
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
