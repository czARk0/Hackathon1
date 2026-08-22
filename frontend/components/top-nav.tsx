'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { Activity } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Wordmark } from '@/components/brand'

const tabs = [
  { href: '/', label: 'Student' },
  { href: '/admin', label: 'Command Center' },
]

export function TopNav() {
  const pathname = usePathname()

  return (
    <header className="sticky top-0 z-30 border-b border-border/70 bg-background/80 backdrop-blur-xl">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between gap-4 px-5">
        <Link href="/" className="rounded-lg outline-none focus-visible:ring-2 focus-visible:ring-ring">
          <Wordmark subtitle="Your campus operations agent" />
        </Link>

        <nav className="flex items-center gap-1 rounded-full border border-border/70 bg-card/60 p-1">
          {tabs.map((tab) => {
            const active =
              tab.href === '/'
                ? pathname === '/'
                : pathname.startsWith(tab.href)
            return (
              <Link
                key={tab.href}
                href={tab.href}
                className={cn(
                  'rounded-full px-4 py-1.5 text-sm font-medium transition-colors',
                  active
                    ? 'bg-primary text-primary-foreground'
                    : 'text-muted-foreground hover:text-foreground',
                )}
              >
                {tab.label}
              </Link>
            )
          })}
        </nav>

        <div className="hidden items-center gap-2 rounded-full border border-border/70 bg-card/60 px-3 py-1.5 text-xs text-muted-foreground md:flex">
          <span className="relative flex size-2">
            <span className="absolute inline-flex size-full animate-ai-pulse-ring rounded-full bg-resolved" />
            <span className="relative inline-flex size-2 rounded-full bg-resolved" />
          </span>
          <Activity className="size-3.5" />
          Agent online
        </div>
      </div>
    </header>
  )
}
