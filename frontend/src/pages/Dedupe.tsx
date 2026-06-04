import FlipCard from '../components/FlipCard'

const MEANS = [
  { label: '精确去重（指纹一致）', value: 2108, pct: 90 },
  { label: '时间窗归并（同源同类聚合）', value: 1602, pct: 68 },
  { label: '抑制规则（已知噪声）', value: 612, pct: 26 },
  { label: '关联聚合（L08 同一事件）', value: 235, pct: 10 },
]

const RULES = [
  { name: '健康检查心跳', hit: '381', on: true },
  { name: '已知扫描器 IP', hit: '146', on: true },
  { name: '测试环境 DEV-*', hit: '85', on: true },
  { name: '备份任务 sudo', hit: '—', on: false },
]

export default function Dedupe() {
  return (
    <div>
      <div className="grid grid-cols-4 gap-[18px] mb-[26px]">
        <FlipCard label="原始告警" value="5,841" delay={0}
          back={[{ k: 'Syslog', v: '2,610' }, { k: 'SIEM', v: '1,902' }, { k: 'EDR', v: '812' }, { k: '其他', v: '517' }]} />
        <FlipCard label="降噪后" value="1,284" valueClass="text-terra" delay={80}
          back={[{ k: '精确去重', v: '-2,108' }, { k: '时间窗归并', v: '-1,602' }, { k: '抑制规则', v: '-612' }, { k: '关联聚合', v: '-235' }]} />
        <FlipCard label="降噪率" value="78%" valueClass="text-ochre" delay={160}
          back={[{ k: '目标', v: '≥70%' }, { k: '本月均值', v: '76%' }]} />
        <FlipCard label="抑制规则" value="23" delay={240}
          back={[{ k: '启用', v: '19' }, { k: '停用', v: '4' }]} />
      </div>

      <div className="grid grid-cols-[1.7fr_1fr] gap-[34px]">
        <div className="bg-paper border border-line rounded-[10px] p-5 lift">
          <div className="text-[13px] text-dim uppercase tracking-wide mb-3">降噪手段拆分 · 分诊前执行</div>
          {MEANS.map((m) => (
            <div key={m.label} className="mb-3">
              <div className="flex justify-between text-[14px] mb-1">
                <span>{m.label}</span>
                <b>{m.value.toLocaleString('en-US')}</b>
              </div>
              <div className="h-2 bg-paper2 rounded-full overflow-hidden">
                <div className="h-full bg-terra rounded-full bar-grow" style={{ width: `${m.pct}%` }} />
              </div>
            </div>
          ))}
        </div>
        <div className="bg-paper border border-line rounded-[10px] p-5 lift">
          <div className="text-[13px] text-dim uppercase tracking-wide mb-3">抑制规则</div>
          {RULES.map((r) => (
            <div key={r.name} className="flex justify-between items-center py-2.5 border-b border-dotted border-line text-[14px]">
              <span>{r.name}</span>
              <span className="flex items-center gap-3">
                <span className="text-dim">{r.hit}</span>
                <span className={`text-[12px] border rounded-full px-2 ${r.on ? 'text-sage border-sage' : 'text-dim border-line'}`}>
                  {r.on ? '启用' : '停用'}
                </span>
              </span>
            </div>
          ))}
          <button className="border border-clay rounded-lg px-4 py-2 text-[14px] mt-3 hover:bg-paper2">+ 新建规则</button>
        </div>
      </div>
    </div>
  )
}
