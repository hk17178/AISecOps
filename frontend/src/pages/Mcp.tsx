import { Card, Pill, SectionTitle } from '../components/ui'

const TOOLS = [
  { name: 'Elasticsearch', cat: 'data_sources', form: '薄适配器', fTone: 'dim' as const, status: '主日志源' },
  { name: 'Syslog', cat: 'data_sources', form: '薄适配器', fTone: 'dim' as const, status: '已接入' },
  { name: 'Splunk', cat: 'security_tools', form: '薄适配器', fTone: 'dim' as const, status: '按需' },
  { name: 'CrowdStrike', cat: 'security_tools', form: '完整 MCP', fTone: 'warn' as const, status: '按需' },
  { name: '企业微信通知', cat: 'custom', form: '薄适配器', fTone: 'dim' as const, status: '已接入' },
]

export default function Mcp() {
  return (
    <div>
      <SectionTitle>工具适配 · 默认薄适配器（ADR-0004）</SectionTitle>
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
            {TOOLS.map((t) => (
              <tr key={t.name} className="border-t border-dotted border-line text-[14px]">
                <td className="py-3">{t.name}</td>
                <td className="py-3 text-dim">{t.cat}</td>
                <td className="py-3"><Pill tone={t.fTone}>{t.form}</Pill></td>
                <td className="py-3 text-dim">{t.status}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </div>
  )
}
