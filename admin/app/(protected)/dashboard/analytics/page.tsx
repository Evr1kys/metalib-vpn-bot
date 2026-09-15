'use client'

import { useState, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/lib/api'
import { 
  FiDollarSign, FiTrendingUp, FiTrendingDown, FiUsers, FiRepeat,
  FiCalendar, FiDownload, FiRefreshCw, FiBarChart2, FiPieChart
} from 'react-icons/fi'
import { 
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  BarChart, Bar, PieChart, Pie, Cell, LineChart, Line, Legend, ComposedChart
} from 'recharts'
import toast from 'react-hot-toast'

interface AnalyticsData {
  revenue: {
    total: number
    monthly: { month: string; amount: number; count: number }[]
    by_plan: { plan: string; amount: number; count: number }[]
    growth: number
  }
  mrr: {
    current: number
    previous: number
    growth: number
    history: { month: string; mrr: number }[]
  }
  churn: {
    rate: number
    history: { month: string; rate: number; churned: number }[]
    reasons: { reason: string; count: number }[]
  }
  ltv: {
    average: number
    by_plan: { plan: string; ltv: number }[]
    by_cohort: { cohort: string; ltv: number; users: number }[]
  }
  conversions: {
    trial_to_paid: number
    free_to_paid: number
    renewal_rate: number
  }
  arpu: number
  arppu: number
}

const COLORS = ['#8b5cf6', '#06b6d4', '#10b981', '#f59e0b', '#ef4444', '#ec4899']

export default function AnalyticsPage() {
  const [period, setPeriod] = useState<'7d' | '30d' | '90d' | '1y'>('30d')
  const [refreshing, setRefreshing] = useState(false)

  const { data: analytics, isLoading, refetch } = useQuery<AnalyticsData>({
    queryKey: ['analytics', period],
    queryFn: () => apiClient.getAnalytics(period),
    refetchInterval: 60000
  })

  const handleRefresh = async () => {
    setRefreshing(true)
    await refetch()
    setTimeout(() => setRefreshing(false), 1000)
    toast.success('Данные обновлены')
  }

  const handleExport = async () => {
    try {
      const blob = await apiClient.exportAnalytics(period)
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `analytics-${period}-${new Date().toISOString().split('T')[0]}.csv`
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      a.remove()
      toast.success('Отчёт скачан')
    } catch (error) {
      toast.error('Ошибка экспорта')
    }
  }

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('ru-RU', {
      style: 'currency',
      currency: 'RUB',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    }).format(value)
  }

  const formatPercent = (value: number) => {
    return `${value >= 0 ? '+' : ''}${value.toFixed(1)}%`
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-500"></div>
      </div>
    )
  }

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl lg:text-4xl font-bold gradient-text">📊 Аналитика</h1>
          <p className="mt-2 text-gray-400">Revenue, MRR, Churn Rate, LTV и другие метрики</p>
        </div>
        <div className="flex items-center gap-3">
          {/* Period Selector */}
          <div className="flex bg-[#1a1a2e] rounded-xl p-1">
            {(['7d', '30d', '90d', '1y'] as const).map((p) => (
              <button
                key={p}
                onClick={() => setPeriod(p)}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                  period === p
                    ? 'bg-purple-500 text-white'
                    : 'text-gray-400 hover:text-white'
                }`}
              >
                {p === '7d' ? '7 дней' : p === '30d' ? '30 дней' : p === '90d' ? '90 дней' : '1 год'}
              </button>
            ))}
          </div>
          <button 
            onClick={handleRefresh}
            className="p-3 rounded-xl dark-card hover:bg-purple-500/10 transition-colors"
          >
            <FiRefreshCw className={`w-5 h-5 text-gray-400 ${refreshing ? 'animate-spin' : ''}`} />
          </button>
          <button 
            onClick={handleExport}
            className="flex items-center gap-2 px-4 py-3 rounded-xl bg-purple-500/20 text-purple-400 hover:bg-purple-500/30 transition-colors"
          >
            <FiDownload className="w-5 h-5" />
            <span className="hidden sm:inline">Экспорт</span>
          </button>
        </div>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Total Revenue */}
        <div className="dark-card rounded-2xl p-6">
          <div className="flex items-center justify-between">
            <div className="p-3 rounded-xl bg-gradient-to-br from-green-500 to-emerald-500">
              <FiDollarSign className="w-6 h-6 text-white" />
            </div>
            <span className={`flex items-center gap-1 text-sm ${
              (analytics?.revenue.growth || 0) >= 0 ? 'text-green-400' : 'text-red-400'
            }`}>
              {(analytics?.revenue.growth || 0) >= 0 ? <FiTrendingUp /> : <FiTrendingDown />}
              {formatPercent(analytics?.revenue.growth || 0)}
            </span>
          </div>
          <div className="mt-4">
            <p className="text-gray-400 text-sm">Общий доход</p>
            <p className="text-2xl font-bold text-white mt-1">
              {formatCurrency(analytics?.revenue.total || 0)}
            </p>
          </div>
        </div>

        {/* MRR */}
        <div className="dark-card rounded-2xl p-6">
          <div className="flex items-center justify-between">
            <div className="p-3 rounded-xl bg-gradient-to-br from-blue-500 to-cyan-500">
              <FiRepeat className="w-6 h-6 text-white" />
            </div>
            <span className={`flex items-center gap-1 text-sm ${
              (analytics?.mrr.growth || 0) >= 0 ? 'text-green-400' : 'text-red-400'
            }`}>
              {(analytics?.mrr.growth || 0) >= 0 ? <FiTrendingUp /> : <FiTrendingDown />}
              {formatPercent(analytics?.mrr.growth || 0)}
            </span>
          </div>
          <div className="mt-4">
            <p className="text-gray-400 text-sm">MRR (ежемесячный доход)</p>
            <p className="text-2xl font-bold text-white mt-1">
              {formatCurrency(analytics?.mrr.current || 0)}
            </p>
          </div>
        </div>

        {/* Churn Rate */}
        <div className="dark-card rounded-2xl p-6">
          <div className="flex items-center justify-between">
            <div className="p-3 rounded-xl bg-gradient-to-br from-red-500 to-orange-500">
              <FiTrendingDown className="w-6 h-6 text-white" />
            </div>
            <span className={`text-sm ${
              (analytics?.churn.rate || 0) <= 5 ? 'text-green-400' : 'text-red-400'
            }`}>
              {(analytics?.churn.rate || 0) <= 5 ? '✓ Норма' : '⚠ Высокий'}
            </span>
          </div>
          <div className="mt-4">
            <p className="text-gray-400 text-sm">Churn Rate</p>
            <p className="text-2xl font-bold text-white mt-1">
              {(analytics?.churn.rate || 0).toFixed(1)}%
            </p>
          </div>
        </div>

        {/* LTV */}
        <div className="dark-card rounded-2xl p-6">
          <div className="flex items-center justify-between">
            <div className="p-3 rounded-xl bg-gradient-to-br from-purple-500 to-pink-500">
              <FiUsers className="w-6 h-6 text-white" />
            </div>
          </div>
          <div className="mt-4">
            <p className="text-gray-400 text-sm">LTV (lifetime value)</p>
            <p className="text-2xl font-bold text-white mt-1">
              {formatCurrency(analytics?.ltv.average || 0)}
            </p>
          </div>
        </div>
      </div>

      {/* Secondary Metrics */}
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
        <div className="dark-card rounded-xl p-4 text-center">
          <p className="text-gray-400 text-sm">ARPU</p>
          <p className="text-xl font-bold text-white mt-1">{formatCurrency(analytics?.arpu || 0)}</p>
        </div>
        <div className="dark-card rounded-xl p-4 text-center">
          <p className="text-gray-400 text-sm">ARPPU</p>
          <p className="text-xl font-bold text-white mt-1">{formatCurrency(analytics?.arppu || 0)}</p>
        </div>
        <div className="dark-card rounded-xl p-4 text-center">
          <p className="text-gray-400 text-sm">Trial → Paid</p>
          <p className="text-xl font-bold text-green-400 mt-1">{(analytics?.conversions.trial_to_paid || 0).toFixed(1)}%</p>
        </div>
        <div className="dark-card rounded-xl p-4 text-center">
          <p className="text-gray-400 text-sm">Free → Paid</p>
          <p className="text-xl font-bold text-blue-400 mt-1">{(analytics?.conversions.free_to_paid || 0).toFixed(1)}%</p>
        </div>
        <div className="dark-card rounded-xl p-4 text-center">
          <p className="text-gray-400 text-sm">Retention</p>
          <p className="text-xl font-bold text-purple-400 mt-1">{(analytics?.conversions.renewal_rate || 0).toFixed(1)}%</p>
        </div>
      </div>

      {/* Charts Row 1 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Revenue Chart */}
        <div className="dark-card rounded-2xl p-6">
          <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <FiBarChart2 className="text-green-400" />
            Доход по месяцам
          </h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={analytics?.revenue.monthly || []}>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                <XAxis dataKey="month" stroke="#9ca3af" fontSize={12} />
                <YAxis yAxisId="left" stroke="#9ca3af" fontSize={12} tickFormatter={(v) => `${(v / 1000).toFixed(0)}k`} />
                <YAxis yAxisId="right" orientation="right" stroke="#9ca3af" fontSize={12} />
                <Tooltip 
                  contentStyle={{ backgroundColor: '#1f2937', border: 'none', borderRadius: '8px' }}
                  formatter={(value: number, name: string) => [
                    name === 'amount' ? formatCurrency(value) : value,
                    name === 'amount' ? 'Доход' : 'Кол-во'
                  ]}
                />
                <Bar yAxisId="left" dataKey="amount" fill="#10b981" radius={[4, 4, 0, 0]} />
                <Line yAxisId="right" type="monotone" dataKey="count" stroke="#8b5cf6" strokeWidth={2} dot={{ fill: '#8b5cf6' }} />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* MRR Trend */}
        <div className="dark-card rounded-2xl p-6">
          <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <FiTrendingUp className="text-blue-400" />
            Динамика MRR
          </h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={analytics?.mrr.history || []}>
                <defs>
                  <linearGradient id="mrrGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3}/>
                    <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                <XAxis dataKey="month" stroke="#9ca3af" fontSize={12} />
                <YAxis stroke="#9ca3af" fontSize={12} tickFormatter={(v) => `${(v / 1000).toFixed(0)}k`} />
                <Tooltip 
                  contentStyle={{ backgroundColor: '#1f2937', border: 'none', borderRadius: '8px' }}
                  formatter={(value: number) => [formatCurrency(value), 'MRR']}
                />
                <Area type="monotone" dataKey="mrr" stroke="#3b82f6" fill="url(#mrrGradient)" strokeWidth={2} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Charts Row 2 */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Revenue by Plan */}
        <div className="dark-card rounded-2xl p-6">
          <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <FiPieChart className="text-purple-400" />
            Доход по планам
          </h3>
          <div className="h-48">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={analytics?.revenue.by_plan || []}
                  cx="50%"
                  cy="50%"
                  innerRadius={40}
                  outerRadius={70}
                  paddingAngle={2}
                  dataKey="amount"
                  nameKey="plan"
                >
                  {(analytics?.revenue.by_plan || []).map((_, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip 
                  contentStyle={{ backgroundColor: '#1f2937', border: 'none', borderRadius: '8px' }}
                  formatter={(value: number) => formatCurrency(value)}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="mt-4 space-y-2">
            {(analytics?.revenue.by_plan || []).map((item, index) => (
              <div key={item.plan} className="flex items-center justify-between text-sm">
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full" style={{ backgroundColor: COLORS[index % COLORS.length] }} />
                  <span className="text-gray-400">{item.plan}</span>
                </div>
                <span className="text-white font-medium">{formatCurrency(item.amount)}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Churn History */}
        <div className="dark-card rounded-2xl p-6">
          <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <FiTrendingDown className="text-red-400" />
            Динамика Churn
          </h3>
          <div className="h-48">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={analytics?.churn.history || []}>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                <XAxis dataKey="month" stroke="#9ca3af" fontSize={11} />
                <YAxis stroke="#9ca3af" fontSize={11} tickFormatter={(v) => `${v}%`} />
                <Tooltip 
                  contentStyle={{ backgroundColor: '#1f2937', border: 'none', borderRadius: '8px' }}
                  formatter={(value: number, name: string) => [
                    name === 'rate' ? `${value.toFixed(1)}%` : value,
                    name === 'rate' ? 'Churn Rate' : 'Отменено'
                  ]}
                />
                <Line type="monotone" dataKey="rate" stroke="#ef4444" strokeWidth={2} dot={{ fill: '#ef4444' }} />
              </LineChart>
            </ResponsiveContainer>
          </div>
          <div className="mt-4">
            <p className="text-gray-400 text-sm">Причины отмены:</p>
            <div className="mt-2 space-y-1">
              {(analytics?.churn.reasons || []).slice(0, 3).map((reason) => (
                <div key={reason.reason} className="flex justify-between text-sm">
                  <span className="text-gray-500">{reason.reason}</span>
                  <span className="text-white">{reason.count}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* LTV by Plan */}
        <div className="dark-card rounded-2xl p-6">
          <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <FiUsers className="text-cyan-400" />
            LTV по планам
          </h3>
          <div className="h-48">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={analytics?.ltv.by_plan || []} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                <XAxis type="number" stroke="#9ca3af" fontSize={11} tickFormatter={(v) => `${(v / 1000).toFixed(0)}k`} />
                <YAxis type="category" dataKey="plan" stroke="#9ca3af" fontSize={11} width={80} />
                <Tooltip 
                  contentStyle={{ backgroundColor: '#1f2937', border: 'none', borderRadius: '8px' }}
                  formatter={(value: number) => [formatCurrency(value), 'LTV']}
                />
                <Bar dataKey="ltv" fill="#06b6d4" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div className="mt-4">
            <p className="text-gray-400 text-sm">LTV по когортам:</p>
            <div className="mt-2 space-y-1">
              {(analytics?.ltv.by_cohort || []).slice(0, 3).map((cohort) => (
                <div key={cohort.cohort} className="flex justify-between text-sm">
                  <span className="text-gray-500">{cohort.cohort}</span>
                  <span className="text-white">{formatCurrency(cohort.ltv)}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
