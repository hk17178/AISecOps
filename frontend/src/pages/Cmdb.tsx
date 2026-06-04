import { Card, Pill, SectionTitle } from '../components/ui'

const ASSETS = [
  { host: 'DC-01', ip: '10.0.0.10', role: '域控', imp: '关键', impTone: 't' as const, status: '正常', stTone: 'ok' as const },
  { host: 'WIN-APP-07', ip: '10.0.2.7', role: '应用服务器', imp: '高', impTone: 'warn' as const, status: '已隔离', stTone: 't' as const },
  { host: 'DEV-12', ip: '10.0.3.12', role: '开发机', imp: '中', impTone: 'dim' as const, status: '观察', stTone: 'warn' as const },
]

export default function Cmdb() {
  return (
    <div>
      <SectionTitle>资产清单 · CMDB 暂不接，先手填（ADR-0010）</SectionTitle>
      <Card>
        <table className="w-full">
          <thead>
            <tr className="text-[12px] text-dim uppercase tracking-wide">
              <th className="text-left font-normal pb-2.5">主机</th>
              <th className="text-left font-normal pb-2.5">IP</th>
              <th className="text-left font-normal pb-2.5">角色</th>
              <th className="text-left font-normal pb-2.5">重要度</th>
              <th className="text-left font-normal pb-2.5">状态</th>
            </tr>
          </thead>
          <tbody>
            {ASSETS.map((a) => (
              <tr key={a.host} className="border-t border-dotted border-line text-[14px]">
                <td className="py-3">{a.host}</td>
                <td className="py-3">{a.ip}</td>
                <td className="py-3">{a.role}</td>
                <td className="py-3"><Pill tone={a.impTone}>{a.imp}</Pill></td>
                <td className="py-3"><Pill tone={a.stTone}>{a.status}</Pill></td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </div>
  )
}
