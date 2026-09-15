import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { 
  ChartBarIcon, 
  ArrowTrendingUpIcon,
  ClockIcon,
  GlobeAltIcon,
  SignalIcon
} from '@heroicons/react/24/outline'
import { api } from '../api'

interface DailyStats {
  date: string
  traffic_bytes: number
  connections: number
  duration_minutes: number
}

interface UsageStats {
  daily: DailyStats[]
  total_traffic: number
  avg_daily_traffic: number
  total_connections: number
  total_duration: number
  most_used_server: string
  peak_hour: number
}

export default function StatsPage() {
  const [stats, setStats] = useState<UsageStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [period, setPeriod] = useState<'7d' | '30d' | 'all'>('7d')

  useEffect(() => {
    loadStats()
  }, [period])

  const loadStats = async () => {
    setLoading(true)
    try {
      const response = await api.getUsageStats(period)
      if (response.success && response.data) {
        setStats(response.data)
      }
    } catch (error) {
      console.error('Failed to load stats:', error)
    } finally {
      setLoading(false)
    }
  }

  const formatBytes = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    if (bytes < 1024 * 1024 * 1024) return `${(bytes / 1024 / 1024).toFixed(1)} MB`
    return `${(bytes / 1024 / 1024 / 1024).toFixed(2)} GB`
  }

  const formatDuration = (minutes: number) => {
    if (minutes < 60) return `${minutes} мин`
    const hours = Math.floor(minutes / 60)
    const mins = minutes % 60
    if (hours < 24) return `${hours}ч ${mins}м`
    const days = Math.floor(hours / 24)
    const remainingHours = hours % 24
    return `${days}д ${remainingHours}ч`
  }

  const getMaxTraffic = () => {
    if (!stats?.daily.length) return 1
    return Math.max(...stats.daily.map(d => d.traffic_bytes))
  }

  const maxTraffic = getMaxTraffic()

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[var(--primary)]" />
      </div>
    )
  }

  return (
    <div className="p-4 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold">Статистика</h1>
        <div className="flex gap-1 p-1 glass rounded-lg">
          {(['7d', '30d', 'all'] as const).map((p) => (
            <button
              key={p}
              onClick={() => setPeriod(p)}
              className={`px-3 py-1.5 rounded-md text-sm font-medium transition-all ${
                period === p
                  ? 'bg-[var(--primary)] text-white'
                  : 'text-[var(--text-secondary)] hover:text-white'
              }`}
            >
              {p === '7d' ? '7 дней' : p === '30d' ? '30 дней' : 'Всё время'}
            </button>
          ))}
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-2 gap-3">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="glass rounded-xl p-4"
        >
          <div className="flex items-center gap-2 text-[var(--text-secondary)] text-sm mb-2">
            <ArrowTrendingUpIcon className="w-4 h-4" />
            <span>Всего трафика</span>
          </div>
          <p className="text-2xl font-bold bg-gradient-to-r from-[var(--primary)] to-[var(--secondary)] bg-clip-text text-transparent">
            {formatBytes(stats?.total_traffic || 0)}
          </p>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="glass rounded-xl p-4"
        >
          <div className="flex items-center gap-2 text-[var(--text-secondary)] text-sm mb-2">
            <ClockIcon className="w-4 h-4" />
            <span>Время онлайн</span>
          </div>
          <p className="text-2xl font-bold text-white">
            {formatDuration(stats?.total_duration || 0)}
          </p>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="glass rounded-xl p-4"
        >
          <div className="flex items-center gap-2 text-[var(--text-secondary)] text-sm mb-2">
            <SignalIcon className="w-4 h-4" />
            <span>Подключений</span>
          </div>
          <p className="text-2xl font-bold text-white">
            {stats?.total_connections || 0}
          </p>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="glass rounded-xl p-4"
        >
          <div className="flex items-center gap-2 text-[var(--text-secondary)] text-sm mb-2">
            <GlobeAltIcon className="w-4 h-4" />
            <span>Топ сервер</span>
          </div>
          <p className="text-lg font-bold text-white truncate">
            {stats?.most_used_server || '—'}
          </p>
        </motion.div>
      </div>

      {/* Traffic Chart */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.4 }}
        className="glass rounded-xl p-4"
      >
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-semibold flex items-center gap-2">
            <ChartBarIcon className="w-5 h-5 text-[var(--primary)]" />
            Трафик по дням
          </h2>
          <span className="text-sm text-[var(--text-secondary)]">
            Ср: {formatBytes(stats?.avg_daily_traffic || 0)}/день
          </span>
        </div>

        {/* Bar Chart */}
        <div className="h-40 flex items-end gap-1">
          {stats?.daily.map((day, index) => {
            const height = maxTraffic > 0 ? (day.traffic_bytes / maxTraffic) * 100 : 0
            const date = new Date(day.date)
            const dayName = date.toLocaleDateString('ru-RU', { weekday: 'short' })
            
            return (
              <div key={day.date} className="flex-1 flex flex-col items-center gap-1">
                <motion.div
                  initial={{ height: 0 }}
                  animate={{ height: `${Math.max(height, 2)}%` }}
                  transition={{ delay: index * 0.05, duration: 0.3 }}
                  className="w-full bg-gradient-to-t from-[var(--primary)] to-[var(--secondary)] rounded-t-md relative group cursor-pointer"
                >
                  {/* Tooltip */}
                  <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-2 py-1 bg-black/80 rounded text-xs whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none">
                    {formatBytes(day.traffic_bytes)}
                  </div>
                </motion.div>
                <span className="text-[10px] text-[var(--text-secondary)]">
                  {dayName}
                </span>
              </div>
            )
          })}
        </div>
      </motion.div>

      {/* Peak Hours */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.5 }}
        className="glass rounded-xl p-4"
      >
        <h2 className="font-semibold mb-3">⏰ Пиковое время</h2>
        <div className="flex items-center justify-between">
          <span className="text-[var(--text-secondary)]">Чаще всего вы онлайн в</span>
          <span className="text-xl font-bold text-[var(--primary)]">
            {stats?.peak_hour !== undefined ? `${stats.peak_hour}:00` : '—'}
          </span>
        </div>
      </motion.div>

      {/* Daily Breakdown */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.6 }}
        className="glass rounded-xl p-4"
      >
        <h2 className="font-semibold mb-3">По дням</h2>
        <div className="space-y-2 max-h-60 overflow-y-auto">
          {stats?.daily.slice().reverse().map((day) => {
            const date = new Date(day.date)
            const formatted = date.toLocaleDateString('ru-RU', { 
              day: 'numeric', 
              month: 'short' 
            })
            
            return (
              <div 
                key={day.date} 
                className="flex items-center justify-between py-2 border-b border-white/5 last:border-0"
              >
                <span className="text-[var(--text-secondary)]">{formatted}</span>
                <div className="flex items-center gap-4 text-sm">
                  <span className="text-white font-medium">
                    {formatBytes(day.traffic_bytes)}
                  </span>
                  <span className="text-[var(--text-secondary)]">
                    {formatDuration(day.duration_minutes)}
                  </span>
                </div>
              </div>
            )
          })}
        </div>
      </motion.div>
    </div>
  )
}
