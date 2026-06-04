import { useCountUp } from '../lib/useCountUp'

export type BackRow = { k: string; v: string }

export default function FlipCard({
  label,
  value,
  valueClass = '',
  back,
  delay = 0,
}: {
  label: string
  value: string
  valueClass?: string
  back: BackRow[]
  delay?: number
}) {
  const display = useCountUp(value)
  const face =
    'flip-face bg-paper border border-line rounded-[10px] p-4 px-[18px] flex flex-col justify-center'

  return (
    <div className="flip h-[120px] fade-up" style={{ animationDelay: `${delay}ms` }}>
      <div className="flip-inner">
        <div className={face}>
          <span className="absolute top-3 right-3.5 text-[11px] text-clay/70">悬停看明细 ⤺</span>
          <div className="text-[13px] text-dim mb-1.5">{label}</div>
          <div className={`text-[34px] font-semibold leading-none ${valueClass}`}>{display}</div>
        </div>
        <div className={`${face} flip-back bg-paper2`}>
          <div className="text-[12px] text-dim mb-1.5 uppercase tracking-wide">{label} · 明细</div>
          {back.map((r) => (
            <div key={r.k} className="flex justify-between text-[13px] py-0.5">
              <span>{r.k}</span>
              <span className="text-dim">{r.v}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
