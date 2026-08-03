import { NavLink } from 'react-router-dom'

const TABS = [
  { to: '/', label: 'Home' },
  { to: '/history', label: 'History' },
  { to: '/insights', label: 'Insights' },
  { to: '/export', label: 'Export' },
]

export default function TabBar() {
  return (
    <nav className="fixed inset-x-0 bottom-0 flex border-t border-gray-200 bg-white">
      {TABS.map((tab) => (
        <NavLink
          key={tab.to}
          to={tab.to}
          end={tab.to === '/'}
          className={({ isActive }) =>
            `flex-1 py-3 text-center text-sm ${
              isActive ? 'font-semibold text-purple-700' : 'text-gray-500'
            }`
          }
        >
          {tab.label}
        </NavLink>
      ))}
    </nav>
  )
}
