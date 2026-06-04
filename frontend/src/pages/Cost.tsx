import FlipCard from '../components/FlipCard'

const PROVIDERS = [
  { name: '豆包（默认 SaaS）', status: '健康', cls: 'text-sage border-sage' },
  { name: '本地 Qwen / Ollama', status: '健康', cls: 'text-sage border-sage' },
  { name: 'Claude（出域开关 · 默认关）', status: '按需', cls: 'text-ochre border-ochre' },
]

export default function Cost() {
  return (
    <div>
      <div className="grid grid-cols-4 gap-[18px] mb-[26px]">
        <FlipCard label="本月成本" value="¥312" valueClass="text-terra" delay={0}
          back={[{ k: '豆包', v: '¥181' }, { k: '通义', v: '¥96' }, { k: '本地 Qwen', v: '¥0' }, { k: 'Claude(出域)', v: '¥35' }]} />
        <FlipCard label="调用次数" value="8,412" delay={80}
          back={[{ k: '分诊', v: '5,108' }, { k: '调查', v: '2,217' }, { k: '报告', v: '1,087' }]} />
        <FlipCard label="预算余量" value="¥188" valueClass="text-ochre" delay={160}
          back={[{ k: '上限', v: '¥500' }, { k: '已用', v: '¥312' }]} />
        <FlipCard label="降级触发" value="2 次" delay={240}
          back={[{ k: '超时降级', v: '1' }, { k: '预算降级', v: '1' }]} />
      </div>
      <div className="bg-paper border border-line rounded-[10px] p-5 lift max-w-[760px]">
        <div className="text-[13px] text-dim uppercase tracking-wide mb-3">Provider 路由</div>
        {PROVIDERS.map((p) => (
          <div key={p.name} className="flex justify-between items-center py-2.5 border-b border-dotted border-line text-[14px]">
            <span>{p.name}</span>
            <span className={`text-[12px] border rounded-full px-2 ${p.cls}`}>{p.status}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
