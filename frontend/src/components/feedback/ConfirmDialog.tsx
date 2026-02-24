/**
 * ConfirmDialog Component
 *
 * Reusable confirmation dialog for destructive or important actions.
 * Built on top of shadcn/ui AlertDialog (Radix).
 *
 * @example
 * ```tsx
 * <ConfirmDialog
 *   open={showLogout}
 *   onOpenChange={setShowLogout}
 *   title="Logout"
 *   description="Are you sure you want to logout?"
 *   confirmLabel="Logout"
 *   variant="destructive"
 *   onConfirm={handleLogout}
 * />
 * ```
 */

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
import { buttonVariants } from '@/components/ui/button';
import { cn } from '@/lib/utils';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface ConfirmDialogProps {
  /** Controlled open state */
  open: boolean;
  /** Called when open state changes (e.g. backdrop click, cancel) */
  onOpenChange: (open: boolean) => void;
  /** Dialog title */
  title: string;
  /** Dialog description / body */
  description: string;
  /** Confirm button label */
  confirmLabel?: string;
  /** Cancel button label */
  cancelLabel?: string;
  /** Visual style of the confirm button */
  variant?: 'default' | 'destructive';
  /** Called when the user confirms */
  onConfirm: () => void;
  /** Whether the confirm action is in progress */
  loading?: boolean;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function ConfirmDialog({
  open,
  onOpenChange,
  title,
  description,
  confirmLabel = 'Confirm',
  cancelLabel = 'Cancel',
  variant = 'default',
  onConfirm,
  loading = false,
}: ConfirmDialogProps) {
  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>{title}</AlertDialogTitle>
          <AlertDialogDescription>{description}</AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel disabled={loading}>
            {cancelLabel}
          </AlertDialogCancel>
          <AlertDialogAction
            onClick={onConfirm}
            disabled={loading}
            className={cn(
              variant === 'destructive' &&
                buttonVariants({ variant: 'destructive' }),
            )}
          >
            {loading ? 'Please wait…' : confirmLabel}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}

export default ConfirmDialog;
