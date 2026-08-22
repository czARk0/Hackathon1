'use client'

import { useState } from 'react'
import { MapPin } from 'lucide-react'
import { buildings, type Building, type Priority } from '@/lib/data'
import { cn } from '@/lib/utils'

const markerColor: Record<Priority, string> = {
  high: 'bg-high',
  medium: 'bg-medium',
  low: 'bg-low',
  resolved: 'bg-resolved',
}

const legend: Array<{ label: string; priority: Priority }> = [
  { label: 'High', priority: 'high' },
  { label: 'Medium', priority: 'medium' },
  { label: 'Low', priority: 'low' },
  { label: 'Clear', priority: 'resolved' },
]

export function CampusMap() {
  const [selected, setSelected] = useState<Building>(
    buildings.find((b) => b.id === 'eng') ?? buildings[0],
  )

  return (
    <div className="flex h-full flex-col rounded-2xl bg-card/60 ring-1 ring-foreground/10">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border/60 px-4 py-3">
        <div className="flex items-center gap-2">
          <MapPin className="size-4 text-primary" />
          <h2 className="text-sm font-semibold">Campus situation map</h2>
        </div>
        <div className="flex items-center gap-3">
          {legend.map((l) => (
            <div key={l.label} className="flex items-center gap-1.5">
              <span className={cn('size-2 rounded-full', markerColor[l.priority])} />
              <span className="text-xs text-muted-foreground">{l.label}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="grid flex-1 gap-4 p-4 lg:grid-cols-[minmax(0,1fr)_15rem]">
        {/* Map canvas */}
        <div className="bg-grid relative aspect-[4/3] w-full overflow-hidden rounded-xl border border-border/60 bg-background/40">
          {/* paths */}
          <div className="pointer-events-none absolute inset-x-0 top-1/2 h-px -translate-y-1/2 bg-border/70" />
          <div className="pointer-events-none absolute inset-y-0 left-1/2 w-px -translate-x-1/2 bg-border/70" />

          {buildings.map((b) => {
            const isSel = b.id === selected.id
            const hasActive = b.active > 0
            return (
              <button
                key={b.id}
                type="button"
                onClick={() => setSelected(b)}
                style={{
                  left: `${b.x}%`,
                  top: `${b.y}%`,
                  width: `${b.w}%`,
                  height: `${b.h}%`,
                }}
                className={cn(
                  'group absolute flex flex-col items-start justify-between rounded-lg border p-2 text-left transition-all',
                  isSel
                    ? 'border-primary/60 bg-primary/10 ring-2 ring-primary/30'
                    : 'border-border/70 bg-card/70 hover:border-border hover:bg-card',
                )}
              >
                <span className="font-mono text-[10px] font-medium tracking-wide text-muted-foreground">
                  {b.short}
                </span>
                {hasActive ? (
                  <span className="flex items-center gap-1">
                    <span className="relative flex size-2.5">
                      {b.topPriority === 'high' && (
                        <span
                          className={cn(
                            'absolute inline-flex size-full animate-ai-pulse-ring rounded-full',
                            markerColor[b.topPriority],
                          )}
                        />
                      )}
                      <span
                        className={cn(
                          'relative inline-flex size-2.5 rounded-full',
                          markerColor[b.topPriority],
                        )}
                      />
                    </span>
                    <span className="text-xs font-semibold tabular-nums">
                      {b.active}
                    </span>
                  </span>
                ) : (
                  <span className={cn('size-2 rounded-full', markerColor.resolved)} />
                )}
              </button>
            )
          })}
        </div>

        {/* Detail panel */}
        <div className="flex flex-col gap-3 rounded-xl border border-border/60 bg-background/40 p-4">
          <div>
            <p className="text-xs text-muted-foreground">Selected building</p>
            <p className="text-base font-semibold text-pretty">{selected.name}</p>
          </div>

          <div className="grid grid-cols-3 gap-2">
            <Stat label="Active" value={selected.active} tone="active" />
            <Stat label="Resolved" value={selected.resolved} tone="resolved" />
            <Stat
              label="Priority"
              value={selected.active > 0 ? 1 : 0}
              tone={selected.topPriority}
            />
          </div>

          <div className="mt-1 flex items-center gap-2 rounded-lg bg-muted/40 px-3 py-2 text-xs">
            <span className={cn('size-2 rounded-full', markerColor[selected.topPriority])} />
            <span className="text-muted-foreground">
              {selected.active > 0
                ? `Top priority: ${selected.topPriority}`
                : 'No active issues — all clear'}
            </span>
          </div>
        </div>
      </div>
    </div>
  )
}

function Stat({
  label,
  value,
  tone,
}: {
  label: string
  value: number
  tone: 'active' | Priority
}) {
  const color =
    tone === 'active'
      ? 'text-primary'
      : tone === 'high'
        ? 'text-high'
        : tone === 'medium'
          ? 'text-medium'
          : tone === 'low'
            ? 'text-low'
            : 'text-resolved'
  return (
    <div className="flex flex-col gap-1 rounded-lg bg-card/70 p-2.5 ring-1 ring-border/60">
      <span className={cn('text-xl font-semibold tabular-nums', color)}>
        {value}
      </span>
      <span className="text-[11px] text-muted-foreground">{label}</span>
    </div>
  )
}
