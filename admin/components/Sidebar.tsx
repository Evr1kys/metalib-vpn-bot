'use client'

import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'
import { useAuthStore } from '@/lib/store/auth'
import {
  FiHome,
  FiUsers,
  FiDollarSign,
  FiServer,
  FiSettings,
  FiSend,
  FiImage,
  FiLogOut,
  FiMenu,
  FiX,
  FiCreditCard,
  FiActivity,
  FiTrendingUp,
  FiGift,
  FiFileText,
  FiChevronDown,
  FiChevronRight,
  FiShield,
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
      { name: 'Транзакции', href: '/dashboard/transactions', icon: FiCreditCard },
      { name: 'Серверы', href: '/dashboard/servers', icon: FiServer },
    ]
  },
  {
    title: 'Маркетинг',
    items: [
      { name: 'Планы', href: '/dashboard/plans', icon: FiDollarSign },
      { name: 'Промокоды', href: '/dashboard/promocodes', icon: FiGift },
      { name: 'Реферралы', href: '/dashboard/referrals', icon: FiTrendingUp },
      { name: 'Рассылка', href: '/dashboard/broadcast', icon: FiSend },
    ]
  },
  {
    title: 'Аналитика',
    items: [
      { name: 'Трафик', href: '/dashboard/traffic', icon: FiActivity },
      { name: 'Логи', href: '/dashboard/logs', icon: FiFileText },
    ]
  },
  {
    title: 'Настройки',
    items: [
      { name: 'Контент', href: '/dashboard/content', icon: FiImage },
      { name: 'Администраторы', href: '/dashboard/admins', icon: FiShield },
      { name: 'Система', href: '/dashboard/settings', icon: FiSettings },
    ]
  }
]

export function Sidebar() {
  const pathname = usePathname()
  const router = useRouter()
  const logout = useAuthStore((state) => state.logout)
  const admin = useAuthStore((state) => state.admin)
  const [isOpen, setIsOpen] = useState(false)
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

  return (
    <>
      {/* Mobile menu button */}
      <button
        className="lg:hidden fixed top-4 left-4 z-50 p-2 bg-white rounded-lg shadow-lg"
        onClick={() => setIsOpen(!isOpen)}
      >
        {isOpen ? <FiX size={24} /> : <FiMenu size={24} />}
      </button>

      {/* Overlay */}
      {isOpen && (
        <div
          className="lg:hidden fixed inset-0 bg-black bg-opacity-50 z-30"
          onClick={() => setIsOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`fixed lg:sticky top-0 left-0 z-40 h-screen w-64 bg-white border-r border-gray-200 transition-transform duration-300 ${
          isOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'
        }`}
      >
        <div className="flex flex-col h-full">
          {/* Header */}
          <div className="p-6 border-b border-gray-200">
            <h1 className="text-2xl font-bold text-primary-600">MetaLib VPN</h1>
            <p className="text-sm text-gray-600 mt-1">Панель управления</p>
          </div>

          {/* Navigation */}
          <nav className="flex-1 overflow-y-auto p-4 space-y-1">
            {navigationSections.map((section) => (
              <div key={section.title} className="mb-2">
                <button
                  onClick={() => toggleSection(section.title)}
                  className="w-full flex items-center justify-between px-3 py-2 text-xs font-semibold text-gray-500 uppercase tracking-wider hover:bg-gray-50 rounded-lg transition-colors"
                >
                  <span>{section.title}</span>
                  {expandedSections[section.title] ? (
                    <FiChevronDown size={14} />
                  ) : (
                    <FiChevronRight size={14} />
                  )}
                </button>
                {expandedSections[section.title] && (
                  <div className="mt-1 space-y-1">
                    {section.items.map((item) => {
                      const isActive = pathname === item.href
                      const Icon = item.icon
                      return (
                        <Link
                          key={item.href}
                          href={item.href}
                          onClick={() => setIsOpen(false)}
                          className={`flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all ${
                            isActive
                              ? 'bg-primary-50 text-primary-700 font-semibold'
                              : 'text-gray-700 hover:bg-gray-50'
                          }`}
                        >
                          <Icon size={18} />
                          <span className="text-sm">{item.name}</span>
                        </Link>
                      )
                    })}
                  </div>
                )}
              </div>
            ))}
          </nav>

          {/* Footer */}
          <div className="p-4 border-t border-gray-200">
            <div className="px-4 py-3 mb-2 bg-gray-50 rounded-lg">
              <p className="text-sm font-medium text-gray-900">{admin?.username}</p>
              <p className="text-xs text-gray-500">{admin?.role}</p>
            </div>
            <button
              onClick={handleLogout}
              className="w-full flex items-center px-4 py-3 text-red-600 hover:bg-red-50 rounded-lg transition"
            >
              <FiLogOut className="mr-3" size={20} />
              Выйти
            </button>
          </div>
        </div>
      </aside>
    </>
  )
}
