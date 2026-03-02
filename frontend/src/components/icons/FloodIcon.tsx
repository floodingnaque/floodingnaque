/**
 * FloodIcon - Custom brand icon for Floodingnaque.
 *
 * Combines a water droplet with wave lines at its base
 * to emphasise the flood-monitoring theme.
 *
 * Accepts the same `className` / sizing props as lucide-react icons
 * so it can be used as a drop-in replacement for `<Droplets />`.
 */

import { type SVGProps } from 'react';
import { cn } from '@/lib/utils';

interface FloodIconProps extends SVGProps<SVGSVGElement> {
  className?: string;
}

export function FloodIcon({ className, ...props }: FloodIconProps) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={cn('shrink-0', className)}
      aria-hidden="true"
      {...props}
    >
      {/* Water droplet */}
      <path d="M12 2.69l5.66 5.66a8 8 0 1 1-11.32 0L12 2.69z" />

      {/* Wave lines inside the droplet base */}
      <path
        d="M7.5 14.5c1 -1 2 -1 3 0s2 1 3 0 2 -1 3 0"
        strokeWidth={1.5}
      />
      <path
        d="M7.5 17.5c1 -1 2 -1 3 0s2 1 3 0 2 -1 3 0"
        strokeWidth={1.5}
      />
    </svg>
  );
}

export default FloodIcon;
