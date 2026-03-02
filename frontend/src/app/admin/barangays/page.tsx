/**
 * Admin Barangay Management Page
 *
 * View and manage barangay configuration for all 16 barangays
 * of Paranaque City. Displays flood risk levels, evacuation centers,
 * population data, and coordinates in an editable table.
 */

import { useState, useMemo } from 'react';
import {
  MapPin,
  Search,
  AlertTriangle,
  Shield,
  CheckCircle,
  Edit2,
  Save,
  X,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { cn } from '@/lib/utils';
import { toast } from 'sonner';
import { BARANGAYS, type BarangayData } from '@/config/paranaque';

type FloodRisk = 'low' | 'moderate' | 'high';

const RISK_STYLES: Record<FloodRisk, string> = {
  high: 'bg-red-50 text-red-700 border-red-300',
  moderate: 'bg-amber-50 text-amber-700 border-amber-300',
  low: 'bg-green-50 text-green-700 border-green-300',
};

const RISK_ICONS: Record<FloodRisk, React.ElementType> = {
  high: AlertTriangle,
  moderate: Shield,
  low: CheckCircle,
};

interface BarangayOverride {
  evacuationCenter?: string;
  floodRisk?: FloodRisk;
}

function loadOverrides(): Record<string, BarangayOverride> {
  try {
    const raw = localStorage.getItem('barangay_overrides');
    return raw ? JSON.parse(raw) : {};
  } catch {
    return {};
  }
}

function saveOverrides(overrides: Record<string, BarangayOverride>) {
  localStorage.setItem('barangay_overrides', JSON.stringify(overrides));
}

export default function AdminBarangaysPage() {
  const [search, setSearch] = useState('');
  const [riskFilter, setRiskFilter] = useState<string>('all');
  const [overrides, setOverrides] = useState<Record<string, BarangayOverride>>(loadOverrides);
  const [editingKey, setEditingKey] = useState<string | null>(null);
  const [editEvac, setEditEvac] = useState('');
  const [editRisk, setEditRisk] = useState<FloodRisk>('low');

  const barangays = useMemo(() => {
    return BARANGAYS.map((b) => ({
      ...b,
      evacuationCenter: overrides[b.key]?.evacuationCenter ?? b.evacuationCenter,
      floodRisk: overrides[b.key]?.floodRisk ?? b.floodRisk,
    }));
  }, [overrides]);

  const filtered = useMemo(() => {
    return barangays.filter((b) => {
      const matchesSearch = !search || b.name.toLowerCase().includes(search.toLowerCase());
      const matchesRisk = riskFilter === 'all' || b.floodRisk === riskFilter;
      return matchesSearch && matchesRisk;
    });
  }, [barangays, search, riskFilter]);

  const riskCounts = useMemo(() => {
    const counts = { high: 0, moderate: 0, low: 0 };
    barangays.forEach((b) => counts[b.floodRisk]++);
    return counts;
  }, [barangays]);

  function startEdit(b: BarangayData & { evacuationCenter: string; floodRisk: FloodRisk }) {
    setEditingKey(b.key);
    setEditEvac(b.evacuationCenter);
    setEditRisk(b.floodRisk);
  }

  function cancelEdit() {
    setEditingKey(null);
  }

  function saveEdit(key: string) {
    const next = { ...overrides };
    const original = BARANGAYS.find((b) => b.key === key);
    if (!original) return;

    // Only store override if different from defaults
    const override: BarangayOverride = {};
    if (editEvac !== original.evacuationCenter) override.evacuationCenter = editEvac;
    if (editRisk !== original.floodRisk) override.floodRisk = editRisk;

    if (Object.keys(override).length > 0) {
      next[key] = override;
    } else {
      delete next[key];
    }

    setOverrides(next);
    saveOverrides(next);
    setEditingKey(null);
    toast.success('Barangay configuration updated');
  }

  return (
    <div className="container mx-auto px-4 py-6 space-y-6">
      {/* Header */}
      <header className="flex items-center gap-3">
        <div className="p-2 rounded-lg bg-primary/10">
          <MapPin className="h-6 w-6 text-primary" />
        </div>
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Barangay Management</h1>
          <p className="text-sm text-muted-foreground">
            Configure flood risk and evacuation data for all 16 barangays
          </p>
        </div>
      </header>

      {/* Risk Summary */}
      <div className="grid gap-4 sm:grid-cols-3">
        {(['high', 'moderate', 'low'] as const).map((level) => {
          const Icon = RISK_ICONS[level];
          return (
            <Card key={level}>
              <CardContent className="pt-4 pb-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Icon className={cn('h-4 w-4', level === 'high' ? 'text-red-600' : level === 'moderate' ? 'text-amber-600' : 'text-green-600')} />
                    <span className="text-sm font-medium capitalize">{level} Risk</span>
                  </div>
                  <span className="text-2xl font-bold">{riskCounts[level]}</span>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3">
        <div className="relative flex-1 min-w-50 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search barangay..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9"
          />
        </div>
        <Select value={riskFilter} onValueChange={setRiskFilter}>
          <SelectTrigger className="w-40">
            <SelectValue placeholder="Risk Level" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Risk Levels</SelectItem>
            <SelectItem value="high">High</SelectItem>
            <SelectItem value="moderate">Moderate</SelectItem>
            <SelectItem value="low">Low</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Table */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-base">
            <MapPin className="h-4 w-4" />
            Barangay Directory
          </CardTitle>
          <CardDescription>
            {filtered.length} of {BARANGAYS.length} barangays shown
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Barangay</TableHead>
                <TableHead>Population</TableHead>
                <TableHead>Flood Risk</TableHead>
                <TableHead>Evacuation Center</TableHead>
                <TableHead>Coordinates</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filtered.map((b) => {
                const isEditing = editingKey === b.key;
                const RiskIcon = RISK_ICONS[b.floodRisk];
                return (
                  <TableRow key={b.key}>
                    <TableCell className="font-medium">{b.name}</TableCell>
                    <TableCell className="text-muted-foreground">
                      {b.population.toLocaleString()}
                    </TableCell>
                    <TableCell>
                      {isEditing ? (
                        <Select value={editRisk} onValueChange={(v) => setEditRisk(v as FloodRisk)}>
                          <SelectTrigger className="w-30 h-8">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="high">High</SelectItem>
                            <SelectItem value="moderate">Moderate</SelectItem>
                            <SelectItem value="low">Low</SelectItem>
                          </SelectContent>
                        </Select>
                      ) : (
                        <Badge
                          variant="outline"
                          className={cn('text-xs capitalize', RISK_STYLES[b.floodRisk])}
                        >
                          <RiskIcon className="h-3 w-3 mr-1" />
                          {b.floodRisk}
                        </Badge>
                      )}
                    </TableCell>
                    <TableCell>
                      {isEditing ? (
                        <Input
                          value={editEvac}
                          onChange={(e) => setEditEvac(e.target.value)}
                          className="h-8 text-sm"
                        />
                      ) : (
                        <span className="text-sm text-muted-foreground">{b.evacuationCenter}</span>
                      )}
                    </TableCell>
                    <TableCell className="text-xs font-mono text-muted-foreground">
                      {b.lat.toFixed(4)}, {b.lon.toFixed(4)}
                    </TableCell>
                    <TableCell className="text-right">
                      {isEditing ? (
                        <div className="flex justify-end gap-1">
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-8 w-8"
                            onClick={() => saveEdit(b.key)}
                          >
                            <Save className="h-4 w-4 text-green-600" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-8 w-8"
                            onClick={cancelEdit}
                          >
                            <X className="h-4 w-4 text-muted-foreground" />
                          </Button>
                        </div>
                      ) : (
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-8 w-8"
                          onClick={() => startEdit(b)}
                        >
                          <Edit2 className="h-4 w-4" />
                        </Button>
                      )}
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
