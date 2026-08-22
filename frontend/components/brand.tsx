import { cn } from '@/lib/utils'

export function Logo({ className }: { className?: string }) {
  return (
    <span
      className={cn(
        'relative inline-flex size-9 items-center justify-center rounded-xl bg-primary/12 text-primary ring-1 ring-primary/25',
        className,
      )}
      aria-hidden="true"
    >
      <svg viewBox="0 0 24 24" className="size-5" fill="none" strokeWidth={2}>
        <path
          d="M12 2.5 4 6v6c0 4.5 3.2 7.6 8 9.5 4.8-1.9 8-5 8-9.5V6l-8-3.5Z"
          stroke="currentColor"
          strokeLinejoin="round"
        />
        <path
          d="m9 12 2 2 4-4.5"
          stroke="currentColor"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
      <span className="absolute -right-0.5 -top-0.5 size-2 rounded-full bg-primary shadow-[0_0_0_3px_var(--background)]" />
    </span>
  )
}

export function Wordmark({
  subtitle,
  className,
}: {
  subtitle?: string
  className?: string
}) {
  return (
    <div className={cn('flex items-center gap-3', className)}>
      <Logo />
      <div className="leading-tight">
        <div className="flex items-center gap-2 text-sm font-semibold tracking-tight">
          Campus Commander
        </div>
        {subtitle ? (
          <div className="text-xs text-muted-foreground">{subtitle}</div>
        ) : null}
      </div>
    </div>
  )
}
