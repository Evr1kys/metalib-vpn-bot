'use client'

import { usePathname, useRouter } from 'next/navigation'
import { useAuthStore } from '@/lib/store/auth'
import { 
  FiHome, FiUsers, FiServer, FiSettings, 
  FiLogOut, FiGift, FiUserPlus, FiMessageSquare,
  FiCreditCard, FiShield, FiPackage,
  FiActivity, FiFileText, FiChevronDown, FiChevronRight,
  FiCalendar, FiMenu, FiX, FiCpu, FiHeadphones, FiBell
} from 'react-icons/fi'
import { useState } from 'react'

const navigationSections = [
  {
    title: 'Основное',
    items: [
      { name: 'Главная', href: '/dashboard', icon: FiHome },
    ]
  },
  {
    title: 'Управление',
    items: [
      { name: 'Пользователи', href: '/dashboard/users', icon: FiUsers },
      { name: 'Подписки', href: '/dashboard/subscriptions', icon: FiCalendar },
      { name: 'Транзакции', href: '/dashboard/transactions', icon: FiCreditCard },
      { name: 'Серверы', href: '/dashboard/servers', icon: FiServer },
      { name: 'Тикеты', href: '/dashboard/support', icon: FiHeadphones },
    ]
  },
  {
    title: 'Маркетинг',
    items: [
      { name: 'Тарифы', href: '/dashboard/plans', icon: FiPackage },
      { name: 'Промокоды', href: '/dashboard/promocodes', icon: FiGift },
      { name: 'Реферралы', href: '/dashboard/referrals', icon: FiUserPlus },
      { name: 'Подарки', href: '/dashboard/gifts', icon: FiGift },
      { name: 'Триалы', href: '/dashboard/trials', icon: FiCalendar },
      { name: 'Партнёры', href: '/dashboard/partners', icon: FiUserPlus },
      { name: 'Рассылка', href: '/dashboard/broadcast', icon: FiMessageSquare },
    ]
  },
  {
    title: 'Аналитика',
    items: [
      { name: 'Алерты', href: '/dashboard/alerts', icon: FiBell },
      { name: 'Трафик', href: '/dashboard/traffic', icon: FiActivity },
      { name: 'Логи', href: '/dashboard/logs', icon: FiFileText },
    ]
  },
  {
    title: 'Настройки',
    items: [
      { name: 'Система', href: '/dashboard/system', icon: FiCpu },
      { name: 'Администраторы', href: '/dashboard/admins', icon: FiShield },
      { name: 'Настройки', href: '/dashboard/settings', icon: FiSettings },
    ]
  }
]

interface ModernSidebarProps {
  isOpen?: boolean
  onClose?: () => void
}

export default function ModernSidebar({ isOpen = true, onClose }: ModernSidebarProps) {
  const pathname = usePathname()
  const router = useRouter()
  const { logout } = useAuthStore()
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({
    'Основное': true,
    'Управление': true,
    'Маркетинг': true,
    'Аналитика': true,
    'Настройки': true,
  })

  const toggleSection = (title: string) => {
    setExpandedSections(prev => ({
      ...prev,
      [title]: !prev[title]
    }))
  }

  const handleLogout = () => {
    logout()
    localStorage.removeItem('admin_token')
    router.push('/login')
  }

  const handleNavigation = (href: string) => {
    router.push(href)
    if (onClose) onClose()
  }

  return (
    <>
      {/* Mobile overlay */}
      {isOpen && (
        <div 
          className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40 lg:hidden"
          onClick={onClose}
        />
      )}
      
      {/* Sidebar */}
      <aside className={`
        fixed inset-y-0 left-0 z-50 w-72 lg:w-64 bg-[#0d0d1a] border-r border-purple-500/20
        transform transition-transform duration-300 ease-in-out
        ${isOpen ? 'translate-x-0' : '-translate-x-full'}
        lg:translate-x-0
      `}>
        <div className="flex flex-col h-full">
          {/* Logo */}
          <div className="flex items-center justify-between h-16 lg:h-20 px-4 lg:px-6 border-b border-purple-500/20">
            <div className="flex items-center">
              <FiShield className="w-8 h-8 lg:w-10 lg:h-10 text-purple-500" />
              <span className="ml-2 lg:ml-3 text-xl lg:text-2xl font-bold gradient-text">MetaLib</span>
            </div>
            {/* Close button for mobile */}
            <button 
              onClick={onClose}
              className="lg:hidden p-2 rounded-lg hover:bg-purple-500/20 text-purple-300"
            >
              <FiX className="w-6 h-6" />
            </button>
          </div>

          {/* Navigation */}
          <nav className="flex-1 px-3 lg:px-4 py-4 lg:py-6 space-y-2 lg:space-y-3 overflow-y-auto">
            {navigationSections.map((section) => (
              <div key={section.title}>
                <button
                  onClick={() => toggleSection(section.title)}
                  className="w-full flex items-center justify-between px-3 py-2 text-xs font-semibold text-purple-300/70 uppercase tracking-wider hover:text-purple-300 transition-colors"
                >
                  <span>{section.title}</span>
                  {expandedSections[section.title] ? (
                    <FiChevronDown className="w-4 h-4" />
                  ) : (
                    <FiChevronRight className="w-4 h-4" />
                  )}
                </button>
                {expandedSections[section.title] && (
                  <div className="mt-1 space-y-1">
                    {section.items.map((item) => {
                      const isActive = pathname === item.href
                      return (
                        <button
                          key={item.name}
                          onClick={() => handleNavigation(item.href)}
                          className={`
                            w-full flex items-center px-4 py-2.5 lg:py-3 text-sm font-medium rounded-xl
                            transition-all duration-200 group
                            ${isActive 
                              ? 'bg-gradient-to-r from-purple-600 to-pink-600 text-white shadow-lg shadow-purple-500/30' 
                              : 'text-gray-300 hover:bg-purple-500/10 hover:text-white'
                            }
                          `}
                        >
                          <item.icon className={`w-5 h-5 mr-3 transition-colors ${isActive ? 'text-white' : 'text-purple-400 group-hover:text-purple-300'}`} />
                          <span>{item.name}</span>
                        </button>
                      )
                    })}
                  </div>
                )}
              </div>
            ))}
          </nav>

          {/* User info & logout */}
          <div className="p-3 lg:p-4 border-t border-purple-500/20">
            <div className="flex items-center justify-between p-3 lg:p-4 rounded-xl bg-gradient-to-r from-purple-500/10 to-pink-500/10 border border-purple-500/20">
              <div className="flex items-center space-x-2 lg:space-x-3">
                <div className="w-9 h-9 lg:w-11 lg:h-11 rounded-full bg-gradient-to-r from-purple-600 to-pink-600 flex items-center justify-center text-white font-bold text-base lg:text-lg shadow-lg">
                  A
                </div>
                <div>
                  <p className="text-sm font-semibold text-white">Admin</p>
                  <p className="text-xs text-purple-300/70">Администратор</p>
                </div>
              </div>
              <button
                onClick={handleLogout}
                className="p-2 lg:p-2.5 rounded-lg hover:bg-red-500/20 text-red-400 transition-all hover:scale-110"
                title="Выйти"
              >
                <FiLogOut className="w-5 h-5" />
              </button>
            </div>
          </div>
        </div>
      </aside>
    </>
  )
}

// Mobile header component
export function MobileHeader({ onMenuClick }: { onMenuClick: () => void }) {
  return (
    <header className="fixed top-0 left-0 right-0 z-30 lg:hidden bg-[#0d0d1a] border-b border-purple-500/20">
      <div className="flex items-center justify-between h-14 px-4">
        <button 
          onClick={onMenuClick}
          className="p-2 rounded-lg hover:bg-purple-500/20 text-purple-300"
        >
          <FiMenu className="w-6 h-6" />
        </button>
        <div className="flex items-center">
          <FiShield className="w-6 h-6 text-purple-500" />
          <span className="ml-2 text-lg font-bold gradient-text">MetaLib</span>
        </div>
        <div className="w-10" /> {/* Spacer for centering */}
      </div>
    </header>
  )
}
