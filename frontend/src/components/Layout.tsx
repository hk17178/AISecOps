import { NavLink, Outlet, useLocation } from 'react-router-dom'
import { NAV, NAV_GROUPS } from '../nav'
import { useAuth } from '../auth'

export default function Layout() {
  const { user, logout } = useAuth()
  const loc = useLocation()
  const current = NAV.find((n) => n.path === loc.pathname)

  return (
    <div className="grid grid-cols-[226px_1fr] h-screen">
      {/* 侧边栏 */}
      <aside className="bg-side border-r border-line overflow-auto">
        <div className="px-6 py-5 text-[21px] font-semibold font-serif tracking-wide">AISECOPS</div>
        <nav className="pb-6">
          {NAV_GROUPS.map((group) => (
            <div key={group}>
              <div className="px-6 pt-4 pb-1.5 text-[11px] uppercase tracking-widest text-dim">
                {group}
              </div>
              {NAV.filter((n) => n.group === group).map((n) => (
                <NavLink
                  key={n.key}
                  to={n.path}
                  end
                  className={({ isActive }) =>
                    `flex items-center gap-2.5 px-6 py-2 text-sm no-underline text-ink ${
                      isActive
                        ? 'bg-[#f3ead7] font-semibold shadow-[inset_3px_0_0_#b0512f]'
                        : 'hover:bg-[#e7e0cf]'
                    }`
                  }
                >
                  <span>{n.label}</span>
                  {n.badge && (
                    <span className="ml-auto bg-terra text-paper text-[11px] px-1.5 rounded-full">
                      {n.badge}
                    </span>
                  )}
                  {n.tag && (
                    <span className="ml-auto text-dim text-[10px] border border-line px-1 rounded-full">
                      {n.tag}
                    </span>
                  )}
                </NavLink>
              ))}
            </div>
          ))}
        </nav>
      </aside>

      {/* 主区 */}
      <div className="flex flex-col min-w-0 overflow-auto">
        <header className="flex items-baseline gap-4 px-10 py-5 border-b border-line sticky top-0 bg-bg z-10">
          <h1 className="text-[21px] font-semibold font-serif">{current?.label ?? ''}</h1>
          <div className="flex-1" />
          <span className="text-dim text-[13px]">
            {user?.username}（{user?.role}）
          </span>
          <button onClick={logout} className="text-dim text-[13px] hover:text-terra">
            退出
          </button>
        </header>
        <main className="p-10">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
