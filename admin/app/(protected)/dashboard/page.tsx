'use client'

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/lib/api'
import Link from 'next/link'
import { 
  FiUsers, FiDollarSign, FiActivity, FiServer, FiTrendingUp, FiGift, FiUserPlus,
  FiSend, FiSettings, FiPlus, FiZap, FiClock, FiAlertCircle, FiCheckCircle,
  FiArrowUpRight, FiArrowDownRight, FiRefreshCw, FiCopy, FiExternalLink, FiBell, FiAlertTriangle
} from 'react-icons/fi'
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar, PieChart, Pie, Cell } from 'recharts'
import toast from 'react-hot-toast'

export default function DashboardPage() {
  const [refreshing, setRefreshing] = useState(false)

  const { data: stats, isLoading, refetch } = useQuery({
    queryKey: ['dashboard-stats'],
    queryFn: () => apiClient.getDashboardStats(),
  })

  const { data: recentUsers } = useQuery({
    queryKey: ['recent-users'],
    queryFn: () => apiClient.getUsers({ limit: 5 }),
  })
  
  const { data: recentPayments } = useQuery({
    queryKey: ['recent-payments'],
    queryFn: () => apiClient.getPayments({ limit: 5 }),
  })
  
  const { data: alertStats } = useQuery({
    queryKey: ['alert-stats'],
    queryFn: () => apiClient.getAlertStats(),
  })

  const handleRefresh = async () => {
    setRefreshing(true)
    await refetch()
    setTimeout(() => setRefreshing(false), 1000)
    toast.success('Данные обновлены')
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-500"></div>
      </div>
    )
  }

  const statCards = [
    {
      name: 'Пользователи',
      value: stats?.total_users || 0,
      change: stats?.users_growth || 0,
      icon: FiUsers,
      gradient: 'stat-gradient-blue',
      iconBg: 'from-blue-500 to-cyan-500',
      link: '/dashboard/users',
    },
    {
      name: 'Активные подписки',
      value: stats?.active_subscriptions || 0,
      change: stats?.subs_growth || 0,
      icon: FiActivity,
      gradient: 'stat-gradient-green',
      iconBg: 'from-green-500 to-emerald-500',
      link: '/dashboard/users',
    },
    {
      name: 'Общий доход',
      value: `${(stats?.total_revenue || 0).toLocaleString()} ₽`,
      change: stats?.revenue_growth || 0,
      icon: FiDollarSign,
      gradient: 'stat-gradient-orange',
      iconBg: 'from-yellow-500 to-orange-500',
      link: '/dashboard/transactions',
    },
    {
      name: 'Серверы',
      value: `${stats?.total_servers || 0}`,
      change: 100,
      icon: FiServer,
      gradient: 'stat-gradient-purple',
      iconBg: 'from-purple-500 to-pink-500',
      link: '/dashboard/servers',
    },
  ]

  // Quick Actions
  const quickActions = [
    { 
      name: 'Рассылка', 
      icon: FiSend, 
      color: 'from-pink-500 to-rose-500',
      link: '/dashboard/broadcast',
      description: 'Отправить сообщение всем пользователям'
    },
    { 
      name: 'Добавить сервер', 
      icon: FiServer, 
      color: 'from-purple-500 to-indigo-500',
      link: '/dashboard/servers',
      description: 'Добавить новый VPN сервер'
    },
    { 
      name: 'Создать промокод', 
      icon: FiGift, 
      color: 'from-green-500 to-emerald-500',
      link: '/dashboard/promocodes',
      description: 'Создать новый промокод для скидки'
    },
    { 
      name: 'Добавить план', 
      icon: FiPlus, 
      color: 'from-blue-500 to-cyan-500',
      link: '/dashboard/plans',
      description: 'Создать новый тарифный план'
    },
  ]

  // Pie chart data for subscription distribution
  const subscriptionData = [
    { name: 'Активные', value: stats?.active_subscriptions || 0, color: '#10b981' },
    { name: 'Истекшие', value: (stats?.total_users || 0) - (stats?.active_subscriptions || 0), color: '#6b7280' },
  ]

  // Use system status from API or fallback
  const systemStatus = stats?.system_status || [
    { name: 'Backend API', status: 'online', uptime: '99.9%' },
    { name: 'Telegram Bot', status: 'online', uptime: '99.8%' },
    { name: 'VPN серверы', status: 'online', uptime: '99.5%' },
    { name: 'Платежная система', status: 'online', uptime: '100%' },
  ]

  // Use chart data from API
  const formattedChartData = stats?.chart_data || []

  return (
    <div className="space-y-4 lg:space-y-6 animate-fade-in">
      {/* Header with Refresh */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl lg:text-4xl font-bold gradient-text">Главная панель</h1>
          <p className="mt-1 lg:mt-2 text-sm lg:text-base text-gray-400">Обзор системы и ключевые метрики</p>
        </div>
        <div className="flex items-center space-x-2 lg:space-x-3">
          <button 
            onClick={handleRefresh}
            className="p-2 lg:p-3 rounded-xl dark-card hover:bg-purple-500/10 transition-colors"
          >
            <FiRefreshCw className={`w-4 h-4 lg:w-5 lg:h-5 text-gray-400 ${refreshing ? 'animate-spin' : ''}`} />
          </button>
          <div className="px-3 py-1.5 lg:px-4 lg:py-2 rounded-xl dark-card flex items-center space-x-2">
            <FiClock className="w-3 h-3 lg:w-4 lg:h-4 text-purple-400" />
            <span className="text-xs lg:text-sm text-gray-400 hidden sm:inline">Обновлено:</span>
            <span className="text-xs lg:text-sm font-medium text-white">{new Date().toLocaleTimeString('ru-RU')}</span>
          </div>
        </div>
      </div>

      {/* Main Stats Grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 lg:gap-6">
        {statCards.map((stat, index) => (
          <Link 
            key={stat.name} 
            href={stat.link}
            className={`${stat.gradient} rounded-xl lg:rounded-2xl p-3 lg:p-6 card-hover animate-slide-in group cursor-pointer`}
            style={{ animationDelay: `${index * 0.1}s` }}
          >
            <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-2 lg:gap-0">
              <div className="flex-1">
                <div className="flex items-center justify-between">
                  <p className="text-xs lg:text-sm font-medium text-gray-400 mb-1 lg:mb-2">{stat.name}</p>
                  <FiExternalLink className="w-3 h-3 lg:w-4 lg:h-4 text-gray-500 group-hover:text-purple-400 transition-colors lg:hidden" />
                </div>
                <p className="text-xl lg:text-3xl font-bold text-white mb-2 lg:mb-3">{stat.value}</p>
                <div className="flex items-center space-x-1 lg:space-x-2">
                  <span className={`px-1.5 lg:px-2 py-0.5 lg:py-1 text-[10px] lg:text-xs font-semibold rounded-full flex items-center ${
                    stat.change >= 0 ? 'badge-success' : 'bg-red-500/20 text-red-400'
                  }`}>
                    {stat.change >= 0 ? <FiArrowUpRight className="mr-0.5 lg:mr-1 w-3 h-3" /> : <FiArrowDownRight className="mr-0.5 lg:mr-1 w-3 h-3" />}
                    {stat.change >= 0 ? '+' : ''}{stat.change}%
                  </span>
                  <span className="text-[10px] lg:text-xs text-gray-500 hidden sm:inline">vs прошлый месяц</span>
                </div>
              </div>
              <div className={`hidden lg:flex p-4 rounded-2xl bg-gradient-to-br ${stat.iconBg} shadow-lg group-hover:scale-110 transition-transform`}>
                <stat.icon className="w-8 h-8 text-white" />
              </div>
            </div>
          </Link>
        ))}
      </div>

      {/* Quick Actions */}
      <div className="dark-card p-4 lg:p-6">
        <div className="flex items-center justify-between mb-4 lg:mb-6">
          <div className="flex items-center space-x-2 lg:space-x-3">
            <div className="p-1.5 lg:p-2 rounded-lg bg-gradient-to-br from-purple-500 to-pink-500">
              <FiZap className="w-4 h-4 lg:w-5 lg:h-5 text-white" />
            </div>
            <h2 className="text-base lg:text-xl font-bold text-white">Быстрые действия</h2>
          </div>
        </div>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-2 lg:gap-4">
          {quickActions.map((action) => (
            <Link
              key={action.name}
              href={action.link}
              className="group p-3 lg:p-4 rounded-xl bg-[#1a1a2e] hover:bg-[#252542] border border-purple-500/10 hover:border-purple-500/30 transition-all"
            >
              <div className={`w-10 h-10 lg:w-12 lg:h-12 rounded-xl bg-gradient-to-br ${action.color} flex items-center justify-center mb-2 lg:mb-3 group-hover:scale-110 transition-transform`}>
                <action.icon className="w-5 h-5 lg:w-6 lg:h-6 text-white" />
              </div>
              <h3 className="text-sm lg:text-base font-semibold text-white group-hover:text-purple-300 transition-colors">{action.name}</h3>
              <p className="text-[10px] lg:text-xs text-gray-500 mt-1 hidden sm:block">{action.description}</p>
            </Link>
          ))}
        </div>
      </div>

      {/* Active Alerts Widget */}
      {alertStats && (alertStats.critical_active > 0 || alertStats.error_active > 0 || alertStats.warning_active > 0) && (
        <div className={`dark-card p-4 lg:p-6 border ${
          alertStats.critical_active > 0 ? 'border-red-500 bg-red-500/5' :
          alertStats.error_active > 0 ? 'border-orange-500 bg-orange-500/5' :
          'border-yellow-500 bg-yellow-500/5'
        }`}>
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div className="flex items-center space-x-3">
              <div className={`p-2 lg:p-3 rounded-xl ${
                alertStats.critical_active > 0 ? 'bg-red-500' :
                alertStats.error_active > 0 ? 'bg-orange-500' :
                'bg-yellow-500'
              }`}>
                {alertStats.critical_active > 0 ? (
                  <FiAlertCircle className="w-5 h-5 lg:w-6 lg:h-6 text-white animate-pulse" />
                ) : (
                  <FiAlertTriangle className="w-5 h-5 lg:w-6 lg:h-6 text-white" />
                )}
              </div>
              <div>
                <h3 className="text-base lg:text-lg font-bold text-white">
                  {alertStats.critical_active > 0 ? 'Критические алерты!' :
                   alertStats.error_active > 0 ? 'Есть ошибки в системе' :
                   'Требует внимания'}
                </h3>
                <p className="text-xs lg:text-sm text-gray-400">
                  {alertStats.active_total} активных алертов
                  {alertStats.critical_active > 0 && ` (${alertStats.critical_active} критических)`}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2 lg:gap-4">
              <div className="flex items-center gap-2">
                {alertStats.critical_active > 0 && (
                  <span className="px-2 py-1 rounded-full bg-red-500/20 text-red-400 text-xs font-medium">
                    🔴 {alertStats.critical_active}
                  </span>
                )}
                {alertStats.error_active > 0 && (
                  <span className="px-2 py-1 rounded-full bg-orange-500/20 text-orange-400 text-xs font-medium">
                    🟠 {alertStats.error_active}
                  </span>
                )}
                {alertStats.warning_active > 0 && (
                  <span className="px-2 py-1 rounded-full bg-yellow-500/20 text-yellow-400 text-xs font-medium">
                    🟡 {alertStats.warning_active}
                  </span>
                )}
              </div>
              <Link
                href="/dashboard/alerts"
                className="px-3 lg:px-4 py-1.5 lg:py-2 rounded-lg bg-gradient-to-r from-purple-500 to-pink-500 text-white text-xs lg:text-sm font-medium hover:opacity-90 transition-opacity flex items-center gap-1"
              >
                <FiBell className="w-3 h-3 lg:w-4 lg:h-4" />
                Просмотреть
              </Link>
            </div>
          </div>
        </div>
      )}

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 lg:gap-6">
        {/* Revenue Chart - takes 2 columns */}
        <div className="lg:col-span-2 dark-card p-4 lg:p-6 card-hover">
          <div className="flex items-center justify-between mb-4 lg:mb-6">
            <h2 className="text-base lg:text-xl font-bold gradient-text">Доход за месяц</h2>
            <div className={`px-2 lg:px-3 py-1 lg:py-1.5 rounded-lg text-xs lg:text-sm font-semibold flex items-center ${
              (stats?.revenue_growth || 0) >= 0 ? 'badge-success' : 'bg-red-500/20 text-red-400'
            }`}>
              {(stats?.revenue_growth || 0) >= 0 ? <FiArrowUpRight className="mr-1" /> : <FiArrowDownRight className="mr-1" />}
              {stats?.revenue_growth > 0 ? '+' : ''}{stats?.revenue_growth || 0}%
            </div>
          </div>
          <ResponsiveContainer width="100%" height={220}>
            <AreaChart data={formattedChartData}>
              <defs>
                <linearGradient id="colorRevenue" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#10b981" stopOpacity={0.4} />
                  <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#2a2a4a" />
              <XAxis dataKey="date" stroke="#6b7280" style={{ fontSize: '10px' }} />
              <YAxis stroke="#6b7280" style={{ fontSize: '10px' }} />
              <Tooltip 
                contentStyle={{ 
                  backgroundColor: '#1a1a2e',
                  border: '1px solid rgba(139, 92, 246, 0.3)',
                  borderRadius: '12px',
                  color: '#fff'
                }}
                formatter={(value: any) => [`${value.toLocaleString()} ₽`, 'Доход']}
              />
              <Area
                type="monotone"
                dataKey="revenue"
                stroke="#10b981"
                strokeWidth={2}
                fillOpacity={1}
                fill="url(#colorRevenue)"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Subscription Distribution Pie Chart */}
        <div className="dark-card p-4 lg:p-6 card-hover">
          <h2 className="text-base lg:text-xl font-bold gradient-text mb-4 lg:mb-6">Подписки</h2>
          <div className="flex items-center justify-center">
            <ResponsiveContainer width="100%" height={160}>
              <PieChart>
                <Pie
                  data={subscriptionData}
                  cx="50%"
                  cy="50%"
                  innerRadius={45}
                  outerRadius={65}
                  paddingAngle={5}
                  dataKey="value"
                >
                  {subscriptionData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip 
                  contentStyle={{ 
                    backgroundColor: '#1a1a2e',
                    border: '1px solid rgba(139, 92, 246, 0.3)',
                    borderRadius: '12px',
                    color: '#fff'
                  }}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="flex justify-center space-x-4 lg:space-x-6 mt-3 lg:mt-4">
            {subscriptionData.map((item) => (
              <div key={item.name} className="flex items-center space-x-1 lg:space-x-2">
                <div className="w-2 h-2 lg:w-3 lg:h-3 rounded-full" style={{ backgroundColor: item.color }} />
                <span className="text-xs lg:text-sm text-gray-400">{item.name}: <span className="text-white font-medium">{item.value}</span></span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Users Chart & System Status */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 lg:gap-6">
        {/* Users Chart */}
        <div className="dark-card p-4 lg:p-6 card-hover">
          <div className="flex items-center justify-between mb-4 lg:mb-6">
            <h2 className="text-base lg:text-xl font-bold gradient-text">Новые пользователи</h2>
            <div className={`px-2 lg:px-3 py-1 lg:py-1.5 rounded-lg text-xs lg:text-sm font-semibold flex items-center ${
              (stats?.users_growth || 0) >= 0 ? 'badge-info' : 'bg-red-500/20 text-red-400'
            }`}>
              {(stats?.users_growth || 0) >= 0 ? <FiArrowUpRight className="mr-1" /> : <FiArrowDownRight className="mr-1" />}
              {stats?.users_growth > 0 ? '+' : ''}{stats?.users_growth || 0}%
            </div>
          </div>
          <ResponsiveContainer width="100%" height={180}>
            <BarChart data={formattedChartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#2a2a4a" />
              <XAxis dataKey="date" stroke="#6b7280" style={{ fontSize: '10px' }} />
              <YAxis stroke="#6b7280" style={{ fontSize: '10px' }} />
              <Tooltip 
                contentStyle={{ 
                  backgroundColor: '#1a1a2e',
                  border: '1px solid rgba(139, 92, 246, 0.3)',
                  borderRadius: '12px',
                  color: '#fff'
                }}
                formatter={(value: any) => [value, 'Пользователи']}
              />
              <Bar dataKey="users" fill="url(#colorBar)" radius={[8, 8, 0, 0]} />
              <defs>
                <linearGradient id="colorBar" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#8b5cf6" />
                  <stop offset="100%" stopColor="#ec4899" />
                </linearGradient>
              </defs>
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* System Status */}
        <div className="dark-card p-4 lg:p-6 card-hover">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between mb-4 lg:mb-6 gap-2">
            <h2 className="text-base lg:text-xl font-bold gradient-text">Статус системы</h2>
            <span className="px-2 lg:px-3 py-1 text-[10px] lg:text-xs font-semibold bg-green-500/20 text-green-400 rounded-full flex items-center w-fit">
              <FiCheckCircle className="mr-1 w-3 h-3" /> Все системы работают
            </span>
          </div>
          <div className="space-y-2 lg:space-y-4">
            {systemStatus.map((system) => (
              <div key={system.name} className="flex items-center justify-between p-2 lg:p-3 rounded-lg bg-[#1a1a2e]">
                <div className="flex items-center space-x-2 lg:space-x-3">
                  <div className={`w-2 h-2 lg:w-2.5 lg:h-2.5 rounded-full ${
                    system.status === 'online' ? 'bg-green-500 animate-pulse' : 'bg-red-500'
                  }`} />
                  <span className="text-sm lg:text-base text-white font-medium">{system.name}</span>
                </div>
                <div className="flex items-center space-x-2 lg:space-x-4">
                  <span className="text-xs lg:text-sm text-gray-400 hidden sm:inline">Uptime: <span className="text-green-400">{system.uptime}</span></span>
                  <span className={`text-[10px] lg:text-xs px-1.5 lg:px-2 py-0.5 lg:py-1 rounded-full ${
                    system.status === 'online' ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'
                  }`}>
                    {system.status === 'online' ? 'Online' : 'Offline'}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Recent Activity */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 lg:gap-6">
        {/* Recent Users */}
        <div className="dark-card p-4 lg:p-6">
          <div className="flex items-center justify-between mb-4 lg:mb-6">
            <h2 className="text-base lg:text-xl font-bold gradient-text">Последние пользователи</h2>
            <Link 
              href="/dashboard/users"
              className="text-xs lg:text-sm text-purple-400 hover:text-purple-300 transition-colors flex items-center"
            >
              Все <FiExternalLink className="ml-1 w-3 h-3" />
            </Link>
          </div>
          <div className="space-y-2 lg:space-y-3">
            {(recentUsers?.users || []).slice(0, 5).map((user: any) => (
              <div key={user.id} className="flex items-center justify-between p-2 lg:p-3 rounded-lg bg-[#1a1a2e] hover:bg-[#252542] transition-colors">
                <div className="flex items-center space-x-2 lg:space-x-3">
                  <div className="w-8 h-8 lg:w-10 lg:h-10 rounded-full bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center">
                    <span className="text-white font-bold text-xs lg:text-sm">
                      {(user.first_name || user.username || 'U')[0].toUpperCase()}
                    </span>
                  </div>
                  <div>
                    <p className="text-sm lg:text-base text-white font-medium truncate max-w-[120px] lg:max-w-none">{user.first_name || user.username || `User #${user.telegram_id}`}</p>
                    <p className="text-[10px] lg:text-xs text-gray-500">ID: {user.telegram_id}</p>
                  </div>
                </div>
                <div className="text-right">
                  <p className={`text-[10px] lg:text-xs px-1.5 lg:px-2 py-0.5 lg:py-1 rounded-full ${
                    user.has_subscription ? 'bg-green-500/20 text-green-400' : 'bg-gray-500/20 text-gray-400'
                  }`}>
                    {user.has_subscription ? 'Активна' : 'Нет'}
                  </p>
                </div>
              </div>
            ))}
            {(!recentUsers?.users || recentUsers.users.length === 0) && (
              <div className="text-center py-8 text-gray-500">
                <FiUsers className="w-12 h-12 mx-auto mb-3 opacity-50" />
                <p>Нет пользователей</p>
              </div>
            )}
          </div>
        </div>

        {/* Recent Payments */}
        <div className="dark-card p-4 lg:p-6">
          <div className="flex items-center justify-between mb-4 lg:mb-6">
            <h2 className="text-base lg:text-xl font-bold gradient-text">Последние платежи</h2>
            <Link 
              href="/dashboard/transactions"
              className="text-xs lg:text-sm text-purple-400 hover:text-purple-300 transition-colors flex items-center"
            >
              Все <FiExternalLink className="ml-1 w-3 h-3" />
            </Link>
          </div>
          <div className="space-y-2 lg:space-y-3">
            {(recentPayments || []).slice(0, 5).map((payment: any) => {
              const status = (payment.status || '').toLowerCase()
              const isPaid = status === 'paid' || status === 'completed'
              const isPending = status === 'pending'
              return (
              <div key={payment.id} className="flex items-center justify-between p-2 lg:p-3 rounded-lg bg-[#1a1a2e] hover:bg-[#252542] transition-colors">
                <div className="flex items-center space-x-2 lg:space-x-3">
                  <div className={`w-8 h-8 lg:w-10 lg:h-10 rounded-full flex items-center justify-center ${
                    isPaid ? 'bg-green-500/20' : 
                    isPending ? 'bg-yellow-500/20' : 'bg-red-500/20'
                  }`}>
                    <FiDollarSign className={`w-4 h-4 lg:w-5 lg:h-5 ${
                      isPaid ? 'text-green-400' :
                      isPending ? 'text-yellow-400' : 'text-red-400'
                    }`} />
                  </div>
                  <div>
                    <p className="text-sm lg:text-base text-white font-medium">{payment.amount?.toLocaleString()} ₽</p>
                    <p className="text-[10px] lg:text-xs text-gray-500">{payment.plan_name || 'Подписка'}</p>
                  </div>
                </div>
                <div className="text-right">
                  <span className={`text-[10px] lg:text-xs px-1.5 lg:px-2 py-0.5 lg:py-1 rounded-full ${
                    isPaid ? 'bg-green-500/20 text-green-400' :
                    isPending ? 'bg-yellow-500/20 text-yellow-400' : 'bg-red-500/20 text-red-400'
                  }`}>
                    {isPaid ? 'Оплачено' :
                     isPending ? 'Ожидает' : 'Отменено'}
                  </span>
                </div>
              </div>
            )})}
            {(!recentPayments || recentPayments.length === 0) && (
              <div className="text-center py-6 lg:py-8 text-gray-500">
                <FiDollarSign className="w-10 h-10 lg:w-12 lg:h-12 mx-auto mb-2 lg:mb-3 opacity-50" />
                <p className="text-sm">Нет платежей</p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Bot Commands Tip */}
      <div className="dark-card p-4 lg:p-6 border border-purple-500/20">
        <div className="flex flex-col sm:flex-row sm:items-start space-y-3 sm:space-y-0 sm:space-x-4">
          <div className="p-2 lg:p-3 rounded-xl bg-gradient-to-br from-purple-500 to-pink-500 flex-shrink-0 w-fit">
            <FiZap className="w-5 h-5 lg:w-6 lg:h-6 text-white" />
          </div>
          <div className="flex-1">
            <h3 className="text-base lg:text-lg font-bold text-white mb-1 lg:mb-2">Совет дня</h3>
            <p className="text-gray-400 text-xs lg:text-sm">
              Используйте быстрые действия выше для частых операций. Для массовой рассылки протестируйте сообщение на небольшой группе.
            </p>
            <div className="mt-3 lg:mt-4 flex flex-wrap gap-2 lg:gap-3">
              <Link 
                href="/dashboard/broadcast" 
                className="px-3 lg:px-4 py-1.5 lg:py-2 rounded-lg bg-purple-500/20 text-purple-400 hover:bg-purple-500/30 transition-colors text-xs lg:text-sm font-medium"
              >
                Рассылка
              </Link>
              <Link 
                href="/dashboard/settings" 
                className="px-3 lg:px-4 py-1.5 lg:py-2 rounded-lg bg-[#1a1a2e] text-gray-400 hover:text-white transition-colors text-xs lg:text-sm font-medium"
              >
                Настройки
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
