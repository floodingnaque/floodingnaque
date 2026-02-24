/**
 * VisuallyHidden Component
 *
 * Renders content that is visually hidden but remains accessible
 * to screen readers. Equivalent to the `sr-only` Tailwind utility
 * but as a composable React component.
 *
 * @example
 * ```tsx
 * <Button>
 *   <TrashIcon />
 *   <VisuallyHidden>Delete item</VisuallyHidden>
 * </Button>
 * ```
 */

import { type HTMLAttributes, forwardRef } from 'react';
import { cn } from '@/lib/utils';

const VisuallyHidden = forwardRef<
  HTMLSpanElement,
  HTMLAttributes<HTMLSpanElement>
>(({ className, ...props }, ref) => (
  <span
    ref={ref}
    className={cn(
      'absolute w-px h-px p-0 -m-px overflow-hidden whitespace-nowrap border-0',
      '[clip:rect(0,0,0,0)]',
      className,
    )}
    {...props}
  />
));

VisuallyHidden.displayName = 'VisuallyHidden';

export { VisuallyHidden };
export default VisuallyHidden;
