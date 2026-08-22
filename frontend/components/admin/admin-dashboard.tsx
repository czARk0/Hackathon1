import { MetricCards } from "./metric-cards"
import { PriorityTable } from "./priority-table"
import { AgentActivity } from "./agent-activity"
import { IssueDistribution } from "./issue-distribution"
import { CampusMap } from "./campus-map"

export function AdminDashboard() {
  return (
    <div className="mx-auto flex max-w-[1400px] flex-col gap-5 px-4 py-6 md:px-6">
      <header className="flex flex-col gap-2 md:flex-row md:items-end md:justify-between">
        <div className="flex flex-col gap-1">
          <div className="flex items-center gap-2">
            <span className="relative flex size-2">
              <span className="absolute inline-flex size-full animate-ai-pulse-ring rounded-full bg-resolved" />
              <span className="relative inline-flex size-2 rounded-full bg-resolved" />
            </span>
            <span className="text-xs font-medium uppercase tracking-[0.18em] text-muted-foreground">
              Live · Campus Operations
            </span>
          </div>
          <h1 className="text-pretty text-2xl font-semibold tracking-tight md:text-3xl">
            Command Center
          </h1>
        </div>
        <p className="max-w-md text-sm leading-relaxed text-muted-foreground">
          Agent-managed campus operations across 9 zones. Prioritized by severity,
          repetition, and escalation risk.
        </p>
      </header>

      <MetricCards />

      <div className="grid grid-cols-1 gap-5 xl:grid-cols-3">
        <div className="xl:col-span-2">
          <CampusMap />
        </div>
        <IssueDistribution />
      </div>

      <div className="grid grid-cols-1 gap-5 xl:grid-cols-3">
        <div className="xl:col-span-2">
          <PriorityTable />
        </div>
        <AgentActivity />
      </div>
    </div>
  )
}
