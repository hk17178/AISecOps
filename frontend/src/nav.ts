// L01 导航（= 设计语言 IA 17 项）。改菜单先改设计语言文档。
export type NavItem = {
  key: string
  label: string
  path: string
  group: string
  badge?: string
  tag?: string
}

export const NAV: NavItem[] = [
  { group: '概览', key: 'dashboard', label: '仪表盘', path: '/' },
  { group: '安全运营', key: 'dedupe', label: '告警降噪', path: '/dedupe' },
  { group: '安全运营', key: 'triage', label: '告警分诊', path: '/triage', badge: '38' },
  { group: '安全运营', key: 'correlate', label: '关联分析', path: '/correlate' },
  { group: '安全运营', key: 'invest', label: '事件调查', path: '/invest' },
  { group: '安全运营', key: 'hunt', label: '威胁狩猎', path: '/hunt', tag: 'V2' },
  { group: '安全运营', key: 'soar', label: 'SOAR 处置', path: '/soar' },
  { group: '协作', key: 'cockpit', label: '协作驾驶舱', path: '/cockpit', tag: '★' },
  { group: '协作', key: 'ticket', label: '工单 & HITL', path: '/ticket', badge: '6' },
  { group: '协作', key: 'dispatch', label: '外发 · 通知分发', path: '/dispatch' },
  { group: '协作', key: 'report', label: '报表中心', path: '/report' },
  { group: '资产 · 情报', key: 'cmdb', label: '资产 CMDB', path: '/cmdb' },
  { group: '资产 · 情报', key: 'intel', label: '威胁情报', path: '/intel' },
  { group: '资产 · 情报', key: 'knowledge', label: '知识库 · RAG', path: '/knowledge', tag: 'RAG' },
  { group: '资产 · 情报', key: 'ai-compliance', label: 'AI 资产合规', path: '/ai-compliance', tag: 'C-3' },
  { group: '平台', key: 'agent', label: 'AI Agent', path: '/agent' },
  { group: '平台', key: 'mcp', label: 'MCP 工具', path: '/mcp' },
  { group: '平台', key: 'log-sources', label: '日志接入', path: '/log-sources' },
  { group: '平台', key: 'prompt', label: 'Prompt 治理', path: '/prompt' },
  { group: '平台', key: 'cost', label: '模型 & 成本', path: '/cost' },
  { group: '平台', key: 'settings', label: '系统设置', path: '/settings' },
]

export const NAV_GROUPS = [...new Set(NAV.map((n) => n.group))]
