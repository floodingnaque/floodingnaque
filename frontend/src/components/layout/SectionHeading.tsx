/**
 * SectionHeading - Landing-page section heading pattern
 *
 * Green uppercase label → bold heading → muted subtitle.
 * Matches the design language used in the landing page sections.
 */

interface SectionHeadingProps {
  label: string;
  title: string;
  subtitle?: string;
}

export function SectionHeading({
  label,
  title,
  subtitle,
}: SectionHeadingProps) {
  return (
    <div className="mb-8">
      <p className="text-xs font-semibold uppercase tracking-[0.2em] text-risk-safe mb-2">
        {label}
      </p>
      <h2 className="text-2xl sm:text-3xl font-bold text-foreground tracking-tight">
        {title}
      </h2>
      {subtitle && (
        <p className="mt-2 text-muted-foreground max-w-xl leading-relaxed text-sm">
          {subtitle}
        </p>
      )}
    </div>
  );
}
