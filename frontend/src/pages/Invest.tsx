const TIMELINE = [
  { t: '09:31', e: 'DEV-12 连接 C2 域名', src: '防火墙' },
  { t: '09:38', e: 'admin 账号异常登录成功', src: 'SIEM' },
  { t: '09:42', e: 'WIN-APP-07 横向移动至 6 台主机', src: 'EDR' },
  { t: '09:44', e: '尝试访问域控 DC-01', src: 'EDR' },
]

export default function Invest() {
  return (
    <div className="grid grid-cols-[1.7fr_1fr] gap-[34px]">
      <div className="bg-paper border border-line rounded-[10px] p-5 lift">
        <div className="text-[13px] text-dim uppercase tracking-wide mb-3">攻击时间线 · INC-2026-0042</div>
        {TIMELINE.map((row, i) => (
          <div key={i} className="flex gap-3 py-3 border-b border-dotted border-line fade-up" style={{ animationDelay: `${i * 80}ms` }}>
            <span className="text-terra font-semibold w-12">{row.t}</span>
            <div>
              <div>{row.e}</div>
              <div className="text-dim text-[12px] mt-0.5">{row.src}</div>
            </div>
          </div>
        ))}
      </div>
      <div className="bg-paper border border-line rounded-[10px] p-5 lift">
        <div className="text-[13px] text-dim uppercase tracking-wide mb-3">向 AI 提问取证</div>
        <div className="bg-[#e7dcc6] rounded-xl px-4 py-3 text-[14px] mb-3 ml-auto max-w-[85%]">
          这次入侵的攻击链是什么？
        </div>
        <div className="bg-paper2 border border-line rounded-xl px-4 py-3 text-[14px]">
          初判为 <b>凭证窃取 → 横向移动</b>：C2 回连(09:31) → 异常登录(09:38) → PsExec 横移(09:42)，目标域控。涉及 6 台主机，建议优先隔离 WIN-APP-07。
          <div className="text-dim text-[12px] mt-2">引用 3 条证据 · 置信度 0.86</div>
        </div>
        <div className="text-dim text-[12px] mt-3">（接 L02 Investigation Agent，当前为示意）</div>
      </div>
    </div>
  )
}
