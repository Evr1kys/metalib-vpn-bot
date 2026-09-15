import { useLocation, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { 
  HomeIcon, 
  DevicePhoneMobileIcon, 
  GlobeAltIcon,
  UserGroupIcon,
  Cog6ToothIcon 
} from '@heroicons/react/24/outline'
import {
  HomeIcon as HomeIconSolid,
  DevicePhoneMobileIcon as DevicePhoneMobileIconSolid,
  GlobeAltIcon as GlobeAltIconSolid,
  UserGroupIcon as UserGroupIconSolid,
  Cog6ToothIcon as Cog6ToothIconSolid
} from '@heroicons/react/24/solid'

const navItems = [
  { path: '/', icon: HomeIcon, activeIcon: HomeIconSolid, label: 'Главная' },
  { path: '/devices', icon: DevicePhoneMobileIcon, activeIcon: DevicePhoneMobileIconSolid, label: 'Устройства' },
  { path: '/servers', icon: GlobeAltIcon, activeIcon: GlobeAltIconSolid, label: 'Серверы' },
  { path: '/referral', icon: UserGroupIcon, activeIcon: UserGroupIconSolid, label: 'Рефералы' },
  { path: '/settings', icon: Cog6ToothIcon, activeIcon: Cog6ToothIconSolid, label: 'Настройки' },
]

export default function Navigation() {
  const location = useLocation()
  const navigate = useNavigate()

  const handleNavClick = (path: string) => {
    // Haptic feedback
    window.Telegram?.WebApp?.HapticFeedback?.selectionChanged()
    navigate(path)
  }

  return (
    <nav className="fixed bottom-0 left-0 right-0 bg-[var(--bg-secondary)]/95 backdrop-blur-xl border-t border-[var(--border)] safe-area-bottom z-50">
      <div className="flex items-center justify-around py-2 px-4">
        {navItems.map((item) => {
          const isActive = location.pathname === item.path
          const Icon = isActive ? item.activeIcon : item.icon

          return (
            <button
              key={item.path}
              onClick={() => handleNavClick(item.path)}
              className={`nav-item ${isActive ? 'active' : ''}`}
            >
              <div className="relative">
                <Icon 
                  className={`w-6 h-6 transition-all duration-300 ${
                    isActive ? 'text-[var(--primary)]' : 'text-[var(--text-muted)]'
                  }`} 
                />
                {isActive && (
                  <motion.div
                    layoutId="navIndicator"
                    className="absolute -bottom-1 left-1/2 -translate-x-1/2 w-4 h-1 bg-gradient-to-r from-[var(--primary)] to-[var(--secondary)] rounded-full"
                    initial={false}
                    transition={{ type: 'spring', stiffness: 500, damping: 30 }}
                  />
                )}
              </div>
              <span 
                className={`text-xs transition-all duration-300 ${
                  isActive ? 'text-[var(--primary)] font-semibold' : 'text-[var(--text-muted)]'
                }`}
              >
                {item.label}
              </span>
            </button>
          )
        })}
      </div>
    </nav>
  )
}
