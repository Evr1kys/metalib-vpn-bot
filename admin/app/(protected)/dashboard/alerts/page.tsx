'use client'

import { useState, useEffect } from 'react'
import { useAuthStore } from '@/lib/store/auth'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { 
  AlertCircle, 
  AlertTriangle, 
  Info, 
  CheckCircle, 
  Clock,
  Server,
  CreditCard,
  Shield,
  Settings,
  RefreshCw,
  Bell,
  BellOff,
  Trash2,
  Eye,
  Check
} from 'lucide-react'

interface Alert {
  id: string
  title: string
  message: string
  severity: 'info' | 'warning' | 'error' | 'critical'
  category: 'server' | 'payment' | 'subscription' | 'security' | 'system' | 'vpn'
  status: 'active' | 'acknowledged' | 'resolved'
  source: string | null
  source_id: string | null
  telegram_sent: boolean
  acknowledged_at: string | null
  acknowledged_by: string | null
  resolved_at: string | null
  resolved_by: string | null
  resolution_note: string | null
  created_at: string
  duration_minutes: number
}

interface AlertStats {
  active_total: number
  critical_active: number
  error_active: number
  warning_active: number
  last_24h: number
  active_by_category: Record<string, number>
}

const severityConfig = {
  critical: { color: 'bg-red-600', icon: AlertCircle, label: 'Критический' },
  error: { color: 'bg-red-500', icon: AlertTriangle, label: 'Ошибка' },
  warning: { color: 'bg-yellow-500', icon: AlertTriangle, label: 'Внимание' },
  info: { color: 'bg-blue-500', icon: Info, label: 'Инфо' }
}

const categoryConfig = {
  server: { icon: Server, label: 'Сервер' },
  payment: { icon: CreditCard, label: 'Платеж' },
  subscription: { icon: Clock, label: 'Подписка' },
  security: { icon: Shield, label: 'Безопасность' },
  system: { icon: Settings, label: 'Система' },
  vpn: { icon: Shield, label: 'VPN' }
}

const statusColors = {
  active: 'bg-red-100 text-red-800',
  acknowledged: 'bg-yellow-100 text-yellow-800',
  resolved: 'bg-green-100 text-green-800'
}

export default function AlertsPage() {
  const { token } = useAuthStore()
  const [alerts, setAlerts] = useState<Alert[]>([])
  const [stats, setStats] = useState<AlertStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState<'all' | 'active' | 'resolved'>('active')
  const [categoryFilter, setCategoryFilter] = useState<string>('all')

  const fetchAlerts = async () => {
    try {
      const params = new URLSearchParams()
      if (filter === 'active') params.append('status_filter', 'active')
      if (filter === 'resolved') params.append('status_filter', 'resolved')
      if (categoryFilter !== 'all') params.append('category', categoryFilter)
      
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/admin/alerts/?${params}`,
        { headers: { Authorization: `Bearer ${token}` } }
      )
      if (response.ok) {
        const data = await response.json()
        setAlerts(data)
      }
    } catch (error) {
      console.error('Failed to fetch alerts:', error)
    }
  }

  const fetchStats = async () => {
    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/admin/alerts/stats`,
        { headers: { Authorization: `Bearer ${token}` } }
      )
      if (response.ok) {
        setStats(await response.json())
      }
    } catch (error) {
      console.error('Failed to fetch stats:', error)
    }
  }

  useEffect(() => {
    const load = async () => {
      setLoading(true)
      await Promise.all([fetchAlerts(), fetchStats()])
      setLoading(false)
    }
    load()
    
    // Auto-refresh every 30 seconds
    const interval = setInterval(load, 30000)
    return () => clearInterval(interval)
  }, [token, filter, categoryFilter])

  const acknowledgeAlert = async (alertId: string) => {
    try {
      await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/admin/alerts/${alertId}/acknowledge`,
        { 
          method: 'POST',
          headers: { Authorization: `Bearer ${token}` }
        }
      )
      fetchAlerts()
      fetchStats()
    } catch (error) {
      console.error('Failed to acknowledge:', error)
    }
  }

  const resolveAlert = async (alertId: string) => {
    try {
      await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/admin/alerts/${alertId}/resolve`,
        { 
          method: 'POST',
          headers: { 
            Authorization: `Bearer ${token}`,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({ note: 'Resolved via admin panel' })
        }
      )
      fetchAlerts()
      fetchStats()
    } catch (error) {
      console.error('Failed to resolve:', error)
    }
  }

  const resolveAll = async () => {
    if (!confirm('Отметить все активные алерты как решённые?')) return
    try {
      await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/admin/alerts/resolve-all`,
        { 
          method: 'POST',
          headers: { Authorization: `Bearer ${token}` }
        }
      )
      fetchAlerts()
      fetchStats()
    } catch (error) {
      console.error('Failed to resolve all:', error)
    }
  }

  const formatDate = (date: string) => {
    return new Date(date).toLocaleString('ru-RU', {
      day: '2-digit',
      month: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  const formatDuration = (minutes: number) => {
    if (minutes < 60) return `${minutes} мин`
    if (minutes < 1440) return `${Math.floor(minutes / 60)} ч`
    return `${Math.floor(minutes / 1440)} д`
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <Bell className="h-6 w-6" />
            Системные алерты
          </h1>
          <p className="text-gray-500 mt-1">
            Мониторинг и управление уведомлениями о проблемах
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => { fetchAlerts(); fetchStats() }}>
            <RefreshCw className="h-4 w-4 mr-2" />
            Обновить
          </Button>
          {stats && stats.active_total > 0 && (
            <Button variant="destructive" onClick={resolveAll}>
              <Check className="h-4 w-4 mr-2" />
              Решить все ({stats.active_total})
            </Button>
          )}
        </div>
      </div>

      {/* Stats Cards */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          <Card className={stats.critical_active > 0 ? 'border-red-500 bg-red-50' : ''}>
            <CardContent className="pt-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-500">Критические</p>
                  <p className="text-2xl font-bold text-red-600">{stats.critical_active}</p>
                </div>
                <AlertCircle className={`h-8 w-8 ${stats.critical_active > 0 ? 'text-red-600 animate-pulse' : 'text-gray-300'}`} />
              </div>
            </CardContent>
          </Card>
          
          <Card className={stats.error_active > 0 ? 'border-orange-500 bg-orange-50' : ''}>
            <CardContent className="pt-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-500">Ошибки</p>
                  <p className="text-2xl font-bold text-orange-600">{stats.error_active}</p>
                </div>
                <AlertTriangle className={`h-8 w-8 ${stats.error_active > 0 ? 'text-orange-600' : 'text-gray-300'}`} />
              </div>
            </CardContent>
          </Card>
          
          <Card>
            <CardContent className="pt-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-500">Внимание</p>
                  <p className="text-2xl font-bold text-yellow-600">{stats.warning_active}</p>
                </div>
                <AlertTriangle className="h-8 w-8 text-yellow-500" />
              </div>
            </CardContent>
          </Card>
          
          <Card>
            <CardContent className="pt-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-500">Всего активных</p>
                  <p className="text-2xl font-bold">{stats.active_total}</p>
                </div>
                <Bell className="h-8 w-8 text-gray-400" />
              </div>
            </CardContent>
          </Card>
          
          <Card>
            <CardContent className="pt-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-500">За 24 часа</p>
                  <p className="text-2xl font-bold">{stats.last_24h}</p>
                </div>
                <Clock className="h-8 w-8 text-gray-400" />
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Filters */}
      <div className="flex flex-wrap gap-2">
        <div className="flex bg-gray-100 rounded-lg p-1">
          {(['active', 'all', 'resolved'] as const).map(f => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                filter === f 
                  ? 'bg-white shadow text-gray-900' 
                  : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              {f === 'active' ? 'Активные' : f === 'all' ? 'Все' : 'Решённые'}
            </button>
          ))}
        </div>
        
        <select
          value={categoryFilter}
          onChange={(e) => setCategoryFilter(e.target.value)}
          className="px-3 py-2 border rounded-lg text-sm"
        >
          <option value="all">Все категории</option>
          {Object.entries(categoryConfig).map(([key, { label }]) => (
            <option key={key} value={key}>{label}</option>
          ))}
        </select>
      </div>

      {/* Alerts List */}
      <Card>
        <CardContent className="p-0">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <RefreshCw className="h-8 w-8 animate-spin text-gray-400" />
            </div>
          ) : alerts.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-gray-500">
              <BellOff className="h-12 w-12 mb-4" />
              <p>Нет алертов</p>
            </div>
          ) : (
            <div className="divide-y">
              {alerts.map((alert) => {
                const severity = severityConfig[alert.severity]
                const category = categoryConfig[alert.category]
                const SeverityIcon = severity.icon
                const CategoryIcon = category?.icon || Settings
                
                return (
                  <div 
                    key={alert.id} 
                    className={`p-4 hover:bg-gray-50 ${
                      alert.status === 'active' && alert.severity === 'critical' 
                        ? 'bg-red-50' 
                        : ''
                    }`}
                  >
                    <div className="flex items-start gap-4">
                      {/* Severity indicator */}
                      <div className={`p-2 rounded-lg ${severity.color}`}>
                        <SeverityIcon className="h-5 w-5 text-white" />
                      </div>
                      
                      {/* Content */}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-start justify-between gap-4">
                          <div>
                            <h3 className="font-semibold text-gray-900">{alert.title}</h3>
                            <p className="text-sm text-gray-600 mt-1 whitespace-pre-wrap">
                              {alert.message}
                            </p>
                          </div>
                          
                          {/* Actions */}
                          {alert.status === 'active' && (
                            <div className="flex gap-2 shrink-0">
                              <Button 
                                size="sm" 
                                variant="outline"
                                onClick={() => acknowledgeAlert(alert.id)}
                              >
                                <Eye className="h-4 w-4" />
                              </Button>
                              <Button 
                                size="sm"
                                onClick={() => resolveAlert(alert.id)}
                              >
                                <Check className="h-4 w-4" />
                              </Button>
                            </div>
                          )}
                        </div>
                        
                        {/* Meta */}
                        <div className="flex flex-wrap items-center gap-3 mt-3 text-xs text-gray-500">
                          <Badge variant="outline" className={statusColors[alert.status]}>
                            {alert.status === 'active' ? 'Активен' : 
                             alert.status === 'acknowledged' ? 'Просмотрен' : 'Решён'}
                          </Badge>
                          
                          <span className="flex items-center gap-1">
                            <CategoryIcon className="h-3 w-3" />
                            {category?.label || alert.category}
                          </span>
                          
                          <span>{formatDate(alert.created_at)}</span>
                          
                          <span className="flex items-center gap-1">
                            <Clock className="h-3 w-3" />
                            {formatDuration(alert.duration_minutes)}
                          </span>
                          
                          {alert.telegram_sent && (
                            <span className="text-blue-500">📱 Telegram</span>
                          )}
                          
                          {alert.resolved_by && (
                            <span className="text-green-600">
                              ✓ {alert.resolved_by}
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
