'use client'

import { Cell, Label, Pie, PieChart } from 'recharts'
import { distribution, priorityBreakdown, type Priority } from '@/lib/data'
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from '@/components/ui/chart'
import { cn } from '@/lib/utils'

const priorityColor: Record<Priority, string> = {
  high: 'var(--high)',
  medium: 'var(--medium)',
  low: 'var(--low)',
  resolved: 'var(--resolved)',
}

const toneBar: Record<'high' | 'medium' | 'low', string> = {
  high: 'bg-high',
  medium: 'bg-medium',
  low: 'bg-low',
}

const chartConfig: ChartConfig = {
  value: { label: 'Issues' },
  high: { label: 'High', color: 'var(--high)' },
  medium: { label: 'Medium', color: 'var(--medium)' },
  low: { label: 'Low', color: 'var(--low)' },
  resolved: { label: 'Resolved', color: 'var(--resolved)' },
}

export function IssueDistribution() {
  const total = priorityBreakdown.reduce((acc, p) => acc + p.value, 0)
  const maxCat = Math.max(...distribution.map((d) => d.count))

  return (
    <div className="flex h-full flex-col gap-4 rounded-2xl bg-card/60 p-4 ring-1 ring-foreground/10">
      <h2 className="text-sm font-semibold">Issue distribution</h2>

      <div className="flex items-center gap-4">
        <ChartContainer
          config={chartConfig}
          className="aspect-square h-36 w-36 shrink-0"
        >
          <PieChart>
            <ChartTooltip
              cursor={false}
              content={<ChartTooltipContent hideLabel />}
            />
            <Pie
              data={priorityBreakdown}
              dataKey="value"
              nameKey="name"
              innerRadius={42}
              outerRadius={64}
              strokeWidth={2}
              stroke="var(--card)"
            >
              {priorityBreakdown.map((entry) => (
                <Cell key={entry.key} fill={priorityColor[entry.key]} />
              ))}
              <Label
                content={({ viewBox }) => {
                  if (viewBox && 'cx' in viewBox && 'cy' in viewBox) {
                    return (
                      <text
                        x={viewBox.cx}
                        y={viewBox.cy}
                        textAnchor="middle"
                        dominantBaseline="middle"
                      >
                        <tspan
                          x={viewBox.cx}
                          y={viewBox.cy}
                          className="fill-foreground text-xl font-semibold"
                        >
                          {total}
                        </tspan>
                        <tspan
                          x={viewBox.cx}
                          y={(viewBox.cy ?? 0) + 16}
                          className="fill-muted-foreground text-[10px]"
                        >
                          total
                        </tspan>
                      </text>
                    )
                  }
                  return null
                }}
              />
            </Pie>
          </PieChart>
        </ChartContainer>

        <ul className="flex flex-1 flex-col gap-2">
          {priorityBreakdown.map((p) => (
            <li key={p.key} className="flex items-center gap-2 text-sm">
              <span
                className="size-2.5 rounded-full"
                style={{ backgroundColor: priorityColor[p.key] }}
              />
              <span className="text-muted-foreground">{p.name}</span>
              <span className="ml-auto font-medium tabular-nums">{p.value}</span>
            </li>
          ))}
        </ul>
      </div>

      <div className="border-t border-border/60 pt-3">
        <p className="mb-3 text-xs font-medium tracking-wide text-muted-foreground uppercase">
          By category
        </p>
        <ul className="flex flex-col gap-2.5">
          {distribution.map((d) => (
            <li key={d.category} className="flex items-center gap-3 text-sm">
              <span className="w-28 shrink-0 truncate text-muted-foreground">
                {d.category}
              </span>
              <div className="h-2 flex-1 overflow-hidden rounded-full bg-muted">
                <div
                  className={cn('h-full rounded-full', toneBar[d.tone])}
                  style={{ width: `${(d.count / maxCat) * 100}%` }}
                />
              </div>
              <span className="w-5 shrink-0 text-right font-medium tabular-nums">
                {d.count}
              </span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  )
}
