import { useState } from 'react'
import { Cards3, SectionTitle } from '../components/ui'

const TEMPLATES = [
  { name: '安全日报', desc: '昨日告警/真威胁/处置概览，管理层简版。' },
  { name: '安全周报', desc: '趋势 + Top 风险 + 处置统计。' },
  { name: '事件复盘', desc: '单事件时间线 + 根因 + 改进项。' },
]

export default function Report() {
  const [done, setDone] = useState<string>('')
  return (
    <div>
      <SectionTitle>报告模板 · 一键生成</SectionTitle>
      <Cards3>
        {TEMPLATES.map((t) => (
          <div key={t.name} className="bg-paper border border-line rounded-[10px] p-[18px] lift">
            <div className="font-semibold mb-1.5">{t.name}</div>
            <p className="text-[13px] text-dim min-h-[40px]">{t.desc}</p>
            <button
              onClick={() => setDone(t.name)}
              className="mt-3 border border-clay rounded-lg px-4 py-2 text-[13px] hover:bg-paper2"
            >
              生成
            </button>
          </div>
        ))}
      </Cards3>
      {done && <div className="text-ochre text-[13px] mt-4">已生成《{done}》（示意）</div>}
    </div>
  )
}
