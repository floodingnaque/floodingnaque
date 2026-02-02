/**
 * QuickActions Component
 *
 * Grid of quick action buttons for common dashboard operations.
 * Responsive layout: 2x2 on mobile, 4x1 on desktop.
 */

import { Link } from 'react-router-dom';
import {
  CloudRain,
  Bell,
  History,
  FileText,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

interface QuickAction {
  label: string;
  description: string;
  href: string;
  icon: React.ReactNode;
  iconColor: string;
  bgColor: string;
}

const quickActions: QuickAction[] = [
  {
    label: 'New Prediction',
    description: 'Run flood risk analysis',
    href: '/predict',
    icon: <CloudRain className="h-5 w-5" />,
    iconColor: 'text-blue-600',
    bgColor: 'bg-blue-100 dark:bg-blue-900/30',
  },
  {
    label: 'View Alerts',
    description: 'Check active warnings',
    href: '/alerts',
    icon: <Bell className="h-5 w-5" />,
    iconColor: 'text-amber-600',
    bgColor: 'bg-amber-100 dark:bg-amber-900/30',
  },
  {
    label: 'Weather History',
    description: 'Browse past data',
    href: '/history',
    icon: <History className="h-5 w-5" />,
    iconColor: 'text-purple-600',
    bgColor: 'bg-purple-100 dark:bg-purple-900/30',
  },
  {
    label: 'Generate Report',
    description: 'Export analysis report',
    href: '/reports',
    icon: <FileText className="h-5 w-5" />,
    iconColor: 'text-green-600',
    bgColor: 'bg-green-100 dark:bg-green-900/30',
  },
];

/**
 * Individual quick action button
 */
function ActionButton({ action }: { action: QuickAction }) {
  return (
    <Link to={action.href} className="block">
      <Button
        variant="outline"
        className={cn(
          'w-full h-auto py-4 px-4 flex flex-col items-start gap-2',
          'hover:bg-muted/50 transition-colors'
        )}
      >
        <div className={cn('p-2 rounded-md', action.bgColor)}>
          <div className={action.iconColor}>{action.icon}</div>
        </div>
        <div className="text-left">
          <div className="font-medium text-sm">{action.label}</div>
          <div className="text-xs text-muted-foreground font-normal">
            {action.description}
          </div>
        </div>
      </Button>
    </Link>
  );
}

/**
 * QuickActions displays a responsive grid of action buttons
 */
export function QuickActions() {
  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-lg font-semibold">Quick Actions</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          {quickActions.map((action) => (
            <ActionButton key={action.href} action={action} />
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

/**
 * Compact version for sidebar placement
 */
export function QuickActionsCompact() {
  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-lg font-semibold">Quick Actions</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 gap-2">
          {quickActions.map((action) => (
            <Link key={action.href} to={action.href}>
              <Button
                variant="outline"
                size="sm"
                className="w-full justify-start gap-2"
              >
                <span className={action.iconColor}>{action.icon}</span>
                <span className="text-sm">{action.label}</span>
              </Button>
            </Link>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

export default QuickActions;
