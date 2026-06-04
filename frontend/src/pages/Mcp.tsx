import { useEffect, useState } from 'react'
import { Card, Pill, SectionTitle } from '../components/ui'
import { apiGet } from '../lib/api'

type Tool = { name: string; category: string; form: string; status: string }

export default function Mcp() {
  const [tools, setTools] = useState<Tool[]>([])
  const [note, setNote] = useState('')

  useEffect(() => {
    apiGet<{ tools: Tool[]; note: string }>('/api/tools')
      .then((d) => {
        setTools(d.tools)
        setNote(d.note)
      })
      .catch(() => setTools([]))
  }, [])

  return (
    <div>
      <SectionTitle>工具适配 · 默认薄适配器（ADR-0004，来自后端注册表）</SectionTitle>
      <Card>
        <table className="w-full">
          <thead>
            <tr className="text-[12px] text-dim uppercase tracking-wide">
              <th className="text-left font-normal pb-2.5">名称</th>
              <th className="text-left font-normal pb-2.5">分类</th>
              <th className="text-left font-normal pb-2.5">形态</th>
              <th className="text-left font-normal pb-2.5">状态</th>
            </tr>
          </thead>
          <tbody>
            {tools.map((t) => (
              <tr key={t.name} className="border-t border-dotted border-line text-[14px]">
                <td className="py-3">{t.name}</td>
                <td className="py-3 text-dim">{t.category}</td>
                <td className="py-3">
                  <Pill tone={t.form === '完整 MCP' ? 'warn' : 'dim'}>{t.form}</Pill>
                </td>
                <td className="py-3 text-dim">{t.status}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
      {note && <div className="text-dim text-[13px] mt-3">{note}</div>}
    </div>
  )
}
