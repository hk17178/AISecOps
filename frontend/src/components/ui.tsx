import type { ReactNode } from 'react'

export function Card({ children, className = '' }: { children: ReactNode; className?: string }) {
  return (
    <div className={`bg-paper border border-line rounded-[10px] p-5 lift ${className}`}>{children}</div>
  )
}

export function SectionTitle({ children }: { children: ReactNode }) {
  return <div className="text-[13px] text-dim uppercase tracking-wide mb-3">{children}</div>
}

type Tone = 'ok' | 'warn' | 't' | 'dim'
const TONE: Record<Tone, string> = {
  ok: 'text-sage border-sage',
  warn: 'text-ochre border-ochre',
  t: 'text-terra border-terra',
  dim: 'text-dim border-line',
}

export function Pill({ children, tone = 'dim' }: { children: ReactNode; tone?: Tone }) {
  return <span className={`text-[12px] border rounded-full px-2 ${TONE[tone]}`}>{children}</span>
}

export function Row({ children }: { children: ReactNode }) {
  return (
    <div className="flex justify-between items-center py-2.5 border-b border-dotted border-line text-[14px]">
      {children}
    </div>
  )
}

export function EmptyState({ icon, title, desc }: { icon: string; title: string; desc: string }) {
  return (
    <div className="text-center py-24 text-dim">
      <div className="text-[40px] font-serif opacity-50 mb-4">{icon}</div>
      <div className="text-lg text-ink mb-2">{title}</div>
      <div>{desc}</div>
    </div>
  )
}

export const btnGhost =
  'border border-clay rounded-lg px-4 py-2 text-[14px] hover:bg-paper2'
export const btnPrimary =
  'bg-terra text-paper font-medium rounded-lg px-4 py-2 text-[14px] hover:bg-[#9a4527]'

export function Cards3({ children }: { children: ReactNode }) {
  return <div className="grid grid-cols-3 gap-[18px]">{children}</div>
}
