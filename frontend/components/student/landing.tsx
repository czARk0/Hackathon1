'use client'

import { CommandInput } from '@/components/student/command-input'
import { RecentRequests } from '@/components/student/recent-requests'
import { Reporter } from '@/lib/api'
import { StoredRequest } from '@/lib/recent-requests'

const capabilities = [
  'Understands the issue',
  'Finds the asset & history',
  'Dispatches the right team',
  'Tracks it to resolution',
]

export function Landing({
  onSubmit,
  reporters,
  selectedReporterId,
  onSelectReporter,
  requests,
  onSelectRequest,
}: {
  onSubmit: (value: string, reporterId: number) => void
  reporters: Reporter[]
  selectedReporterId: number
  onSelectReporter: (id: number) => void
  requests: StoredRequest[]
  onSelectRequest: (req: StoredRequest) => void
}) {
  return (
    <div className="relative flex min-h-[calc(100vh-4rem)] flex-col">
      <div className="bg-grid pointer-events-none absolute inset-0 [mask-image:radial-gradient(ellipse_60%_50%_at_50%_35%,#000_40%,transparent_100%)]" />

      <div className="relative mx-auto flex w-full max-w-3xl flex-1 flex-col items-center justify-center px-5 py-16">
        {/* Agent orb */}
        <div className="relative mb-8 flex size-16 items-center justify-center">
          <span className="absolute inline-flex size-16 animate-ai-pulse-ring rounded-full bg-primary/40" />
          <span className="absolute inline-flex size-16 animate-ai-orbit rounded-full border border-dashed border-primary/40" />
          <span className="relative flex size-11 items-center justify-center rounded-full bg-primary/15 ring-1 ring-primary/30">
            <span className="size-3 rounded-full bg-primary shadow-[0_0_16px_2px_var(--primary)]" />
          </span>
        </div>

        <p className="mb-3 inline-flex items-center gap-2 rounded-full border border-border/70 bg-card/50 px-3 py-1 text-xs text-muted-foreground">
          <span className="size-1.5 animate-ai-blink rounded-full bg-resolved" />
          Autonomous campus operations agent
        </p>

        <h1 className="text-center text-4xl font-semibold tracking-tight text-balance md:text-5xl">
          What happened?
        </h1>
        <p className="mt-4 max-w-md text-center text-base text-pretty text-muted-foreground">
          Just tell Campus Commander what&apos;s wrong. It handles the rest — no
          forms, no ticket numbers, no chasing anyone.
        </p>

        <div className="mt-10 w-full">
          <CommandInput
            onSubmit={onSubmit}
            reporters={reporters}
            selectedReporterId={selectedReporterId}
            onSelectReporter={onSelectReporter}
          />
        </div>

        <div className="mt-8 flex flex-wrap items-center justify-center gap-x-5 gap-y-2">
          {capabilities.map((c, i) => (
            <div
              key={c}
              className="flex items-center gap-2 text-xs text-muted-foreground"
            >
              <span className="font-mono text-[10px] text-primary/70">
                0{i + 1}
              </span>
              {c}
            </div>
          ))}
        </div>
      </div>

      <div className="relative mx-auto w-full max-w-3xl px-5 pb-14">
        <RecentRequests
          requests={requests}
          onSelectRequest={onSelectRequest}
        />
      </div>
    </div>
  )
}
