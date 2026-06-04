const STATS = [
  { label: '今日告警', value: '1,284', cls: 'text-ink' },
  { label: '真威胁', value: '23', cls: 'text-terra' },
  { label: '待审 HITL', value: '6', cls: 'text-ochre' },
  { label: '本月 Token', value: '¥312', cls: 'text-ink' },
]

export default function Dashboard() {
  return (
    <div>
      <div className="grid grid-cols-4 gap-[18px] mb-[26px]">
        {STATS.map((s) => (
          <div key={s.label} className="bg-paper border border-line rounded-[10px] p-4 px-[18px]">
            <div className="text-[13px] text-dim mb-1.5">{s.label}</div>
            <div className={`text-[34px] font-semibold leading-none ${s.cls}`}>{s.value}</div>
          </div>
        ))}
      </div>
      <div className="grid grid-cols-[1.7fr_1fr] gap-[34px]">
        <div className="bg-paper border border-line rounded-[10px] p-5">
          <div className="text-[13px] text-dim uppercase tracking-wide mb-3">最新真威胁</div>
          <div className="flex justify-between py-2.5 border-b border-line">
            <span>检测到横向移动 (PsExec) · WIN-APP-07</span>
            <span className="text-terra font-semibold">真威胁</span>
          </div>
          <div className="flex justify-between py-2.5 border-b border-line">
            <span>出站连接到已知 C2 域名 · DEV-12</span>
            <span className="text-terra font-semibold">真威胁</span>
          </div>
        </div>
        <div className="bg-paper border border-line rounded-[10px] p-5">
          <div className="text-[13px] text-dim uppercase tracking-wide mb-3">本月预算</div>
          <div className="flex justify-between py-2.5">
            <span>¥312 / ¥500</span>
            <span className="text-ochre border border-ochre rounded-full px-2 text-[12px]">62%</span>
          </div>
          <div className="h-2 bg-paper2 rounded-full mt-1.5 overflow-hidden">
            <div className="h-full bg-terra rounded-full" style={{ width: '62%' }} />
          </div>
        </div>
      </div>
    </div>
  )
}
