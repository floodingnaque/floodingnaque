/**
 * EmptyState Component
 *
 * Reusable placeholder for lists / data views that have no content.
 * Renders an icon, heading, description, and optional action button.
 *
 * @example
 * ```tsx
 * <EmptyState
 *   icon={Bell}
 *   title="No alerts"
 *   description="All systems are operating normally."
 *   action={{ label: 'Refresh', onClick: refetch }}
 * />
 * ```
 */

import { type ElementType } from 'react';
import { Inbox } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface EmptyStateAction {
  /** Button label */
  label: string;
  /** Click handler */
  onClick: () => void;
  /** Button variant (default: "outline") */
  variant?: 'default' | 'outline' | 'secondary' | 'ghost';
}

interface EmptyStateProps {
  /** Lucide icon component */
  icon?: ElementType;
  /** Heading text */
  title: string;
  /** Supporting description */
  description?: string;
  /** Optional call-to-action button */
  action?: EmptyStateAction;
  /** Extra wrapper classes */
  className?: string;
  /** Size variant */
  size?: 'sm' | 'md' | 'lg';
}

// ---------------------------------------------------------------------------
// Size presets
// ---------------------------------------------------------------------------

const sizeConfig = {
  sm: {
    wrapper: 'py-6',
    iconBg: 'p-2 mb-2',
    icon: 'h-5 w-5',
    title: 'text-sm font-medium',
    description: 'text-xs',
  },
  md: {
    wrapper: 'py-8',
    iconBg: 'p-3 mb-3',
    icon: 'h-6 w-6',
    title: 'text-base font-medium',
    description: 'text-sm',
  },
  lg: {
    wrapper: 'py-12',
    iconBg: 'p-4 mb-4',
    icon: 'h-8 w-8',
    title: 'text-lg font-semibold',
    description: 'text-sm',
  },
} as const;

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function EmptyState({
  icon: Icon = Inbox,
  title,
  description,
  action,
  className,
  size = 'md',
}: EmptyStateProps) {
  const s = sizeConfig[size];

  return (
    <div
      className={cn(
        'flex flex-col items-center justify-center text-center',
        s.wrapper,
        className,
      )}
      role="status"
    >
      <div
        className={cn(
          'rounded-full bg-muted',
          s.iconBg,
        )}
      >
        <Icon
          className={cn(s.icon, 'text-muted-foreground')}
          aria-hidden="true"
        />
      </div>

      <p className={cn(s.title)}>{title}</p>

      {description && (
        <p className={cn('mt-1 text-muted-foreground', s.description)}>
          {description}
        </p>
      )}

      {action && (
        <Button
          variant={action.variant ?? 'outline'}
          size="sm"
          onClick={action.onClick}
          className="mt-4"
        >
          {action.label}
        </Button>
      )}
    </div>
  );
}

export default EmptyState;
