import FlipCard from '../components/FlipCard'

export default function Dashboard() {
  return (
    <div>
      <div className="grid grid-cols-4 gap-[18px] mb-[26px]">
        <FlipCard
          label="今日告警"
          value="1,284"
          delay={0}
          back={[
            { k: '严重', v: '41' },
            { k: '高', v: '217' },
            { k: '中', v: '638' },
            { k: '低', v: '388' },
          ]}
        />
        <FlipCard
          label="真威胁"
          value="23"
          valueClass="text-terra"
          delay={80}
          back={[
            { k: 'EDR', v: '9' },
            { k: 'SIEM', v: '7' },
            { k: 'NDR', v: '4' },
            { k: '防火墙', v: '3' },
          ]}
        />
        <FlipCard
          label="待审 HITL"
          value="6"
          valueClass="text-ochre"
          delay={160}
          back={[
            { k: '隔离主机', v: '3' },
            { k: '禁用账号', v: '2' },
            { k: '封 IP', v: '1' },
          ]}
        />
        <FlipCard
          label="本月 Token"
          value="¥312"
          delay={240}
          back={[
            { k: '分诊', v: '¥181' },
            { k: '调查', v: '¥96' },
            { k: '报告', v: '¥35' },
          ]}
        />
      </div>

      <div className="grid grid-cols-[1.7fr_1fr] gap-[34px]">
        <div className="bg-paper border border-line rounded-[10px] p-5 lift">
          <div className="text-[13px] text-dim uppercase tracking-wide mb-3">最新真威胁</div>
          <div className="flex items-center justify-between py-2.5 border-b border-line">
            <span>
              <span className="inline-block w-2 h-2 rounded-full bg-terra pulse-dot mr-2 align-middle" />
              检测到横向移动 (PsExec) · WIN-APP-07
            </span>
            <span className="text-terra font-semibold">真威胁</span>
          </div>
          <div className="flex items-center justify-between py-2.5 border-b border-line">
            <span>
              <span className="inline-block w-2 h-2 rounded-full bg-sage mr-2 align-middle" />
              出站连接到已知 C2 域名 · DEV-12
            </span>
            <span className="text-terra font-semibold">真威胁</span>
          </div>
        </div>
        <div className="bg-paper border border-line rounded-[10px] p-5 lift">
          <div className="text-[13px] text-dim uppercase tracking-wide mb-3">本月预算</div>
          <div className="flex justify-between py-2.5">
            <span>¥312 / ¥500</span>
            <span className="text-ochre border border-ochre rounded-full px-2 text-[12px]">62%</span>
          </div>
          <div className="h-2 bg-paper2 rounded-full mt-1.5 overflow-hidden">
            <div className="h-full bg-terra rounded-full bar-grow" style={{ width: '62%' }} />
          </div>
        </div>
      </div>
    </div>
  )
}
