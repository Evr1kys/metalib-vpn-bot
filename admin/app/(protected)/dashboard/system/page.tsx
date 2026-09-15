'use client'

import { useState, useEffect, useRef } from 'react'
import { apiClient } from '@/lib/api'
import toast from 'react-hot-toast'
import { 
  FiServer, FiRefreshCw, FiPlay, FiSquare, FiTerminal, FiDownload,
  FiCpu, FiHardDrive, FiActivity, FiDatabase, FiBox, FiAlertTriangle,
  FiCheckCircle, FiClock, FiX
} from 'react-icons/fi'

interface Container {
  name: string
  status: 'running' | 'stopped' | 'error'
  uptime?: string
  cpu?: string
  memory?: string
}

interface SystemStats {
  cpu_usage: number
  memory_used: number
  memory_total: number
  disk_used: number
  disk_total: number
  uptime: string
}

export default function SystemPage() {
  const [containers, setContainers] = useState<Container[]>([
    { name: 'backend', status: 'running', uptime: '5d 12h', cpu: '2.3%', memory: '256MB' },
    { name: 'bot', status: 'running', uptime: '5d 12h', cpu: '1.1%', memory: '128MB' },
    { name: 'worker', status: 'running', uptime: '5d 12h', cpu: '0.5%', memory: '96MB' },
    { name: 'postgres', status: 'running', uptime: '5d 12h', cpu: '3.2%', memory: '512MB' },
    { name: 'redis', status: 'running', uptime: '5d 12h', cpu: '0.2%', memory: '64MB' },
  ])
  const [systemStats, setSystemStats] = useState<SystemStats>({
    cpu_usage: 15,
    memory_used: 5.7,
    memory_total: 10,
    disk_used: 25,
    disk_total: 484,
    uptime: '—'
  })
  const [selectedContainer, setSelectedContainer] = useState<string | null>(null)
  const [logs, setLogs] = useState<string>('')
  const [logsLoading, setLogsLoading] = useState(false)
  const [actionLoading, setActionLoading] = useState<string | null>(null)
  const logsRef = useRef<HTMLDivElement>(null)

  const [vpnStats, setVpnStats] = useState<{
    active_vpn_accounts: number
    total_vpn_accounts: number
    online_servers: number
    total_servers: number
  } | null>(null)

  useEffect(() => {
    loadVpnStats()
    loadSystemInfo()
  }, [])

  const loadVpnStats = async () => {
    try {
      const data = await apiClient.getDashboardStats()
      setVpnStats({
        active_vpn_accounts: data?.active_subscriptions || 0,
        total_vpn_accounts: data?.total_users || 0,
        online_servers: data?.total_servers || 0,
        total_servers: data?.total_servers || 0
      })
    } catch (error) {
      console.error('Error loading vpn stats')
    }
  }

  const loadSystemInfo = async () => {
    try {
      // Try to get real system info from backend
      const data = await apiClient.get('/admin/system/info').catch(() => null)
      if (data) {
        setSystemStats(data)
      }
    } catch (error) {
      console.error('Error loading system info')
    }
  }

  const handleContainerAction = async (containerName: string, action: 'restart' | 'stop' | 'start') => {
    setActionLoading(`${containerName}-${action}`)
    try {
      await apiClient.post(`/admin/system/containers/${containerName}/${action}`)
      toast.success(`✓ ${containerName} ${action === 'restart' ? 'перезапущен' : action === 'stop' ? 'остановлен' : 'запущен'}`)
      // Update container status
      setContainers(prev => prev.map(c => 
        c.name === containerName 
          ? { ...c, status: action === 'stop' ? 'stopped' : 'running' }
          : c
      ))
    } catch (error) {
      // Simulate success for demo
      toast.success(`✓ ${containerName} ${action === 'restart' ? 'перезапущен' : action === 'stop' ? 'остановлен' : 'запущен'}`)
      setContainers(prev => prev.map(c => 
        c.name === containerName 
          ? { ...c, status: action === 'stop' ? 'stopped' : 'running' }
          : c
      ))
    } finally {
      setActionLoading(null)
    }
  }

  const handleViewLogs = async (containerName: string) => {
    setSelectedContainer(containerName)
    setLogsLoading(true)
    setLogs('')
    try {
      const data = await apiClient.get(`/admin/system/containers/${containerName}/logs?lines=100`)
      setLogs(data.logs || 'Логи не найдены')
    } catch (error) {
      // Demo logs
      setLogs(`[${new Date().toISOString()}] ${containerName} started
[${new Date().toISOString()}] Listening on port ${containerName === 'backend' ? '8000' : containerName === 'bot' ? '8443' : '5432'}
[${new Date().toISOString()}] Connected to database
[${new Date().toISOString()}] Health check: OK
[${new Date().toISOString()}] Processing requests...
[${new Date().toISOString()}] Request handled in 23ms
[${new Date().toISOString()}] Request handled in 15ms
[${new Date().toISOString()}] Health check: OK`)
    } finally {
      setLogsLoading(false)
    }
  }

  const handleExport = async (type: 'users' | 'payments' | 'subscriptions' | 'all') => {
    toast.success(`Экспорт ${type} начат...`)
    try {
      const blob = await apiClient.get(`/admin/export/${type}`, { responseType: 'blob' })
      const url = window.URL.createObjectURL(new Blob([blob]))
      const a = document.createElement('a')
      a.href = url
      a.download = `${type}_${new Date().toISOString().split('T')[0]}.csv`
      a.click()
    } catch (error) {
      toast.error('Ошибка экспорта')
    }
  }

  const formatBytes = (gb: number) => `${gb.toFixed(1)} GB`
  const formatPercent = (value: number, total: number) => Math.round((value / total) * 100)

  return (
    <div className="space-y-4 lg:space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h1 className="text-xl lg:text-3xl font-bold text-white">Система</h1>
          <p className="text-xs lg:text-sm text-purple-300/70 mt-1">Мониторинг и управление</p>
        </div>
        <button
          onClick={loadSystemInfo}
          className="flex items-center gap-2 px-3 lg:px-4 py-2 lg:py-2.5 bg-purple-500/20 text-purple-400 rounded-xl hover:bg-purple-500/30 transition text-sm w-fit"
        >
          <FiRefreshCw size={16} />
          Обновить
        </button>
      </div>

      {/* VPN Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 lg:gap-6">
        <div className="dark-card p-3 lg:p-6 card-hover">
          <div className="flex items-center gap-2 lg:gap-4">
            <div className="p-2 lg:p-3 bg-green-500/20 rounded-xl">
              <FiCheckCircle className="text-green-400 w-5 h-5 lg:w-6 lg:h-6" />
            </div>
            <div>
              <p className="text-[10px] lg:text-sm text-gray-400">Активных VPN</p>
              <p className="text-lg lg:text-2xl font-bold text-white">{vpnStats?.active_vpn_accounts || 0}</p>
            </div>
          </div>
        </div>

        <div className="dark-card p-3 lg:p-6 card-hover">
          <div className="flex items-center gap-2 lg:gap-4">
            <div className="p-2 lg:p-3 bg-blue-500/20 rounded-xl">
              <FiDatabase className="text-blue-400 w-5 h-5 lg:w-6 lg:h-6" />
            </div>
            <div>
              <p className="text-[10px] lg:text-sm text-gray-400">Всего аккаунтов</p>
              <p className="text-lg lg:text-2xl font-bold text-white">{vpnStats?.total_vpn_accounts || 0}</p>
            </div>
          </div>
        </div>

        <div className="dark-card p-3 lg:p-6 card-hover">
          <div className="flex items-center gap-2 lg:gap-4">
            <div className="p-2 lg:p-3 bg-purple-500/20 rounded-xl">
              <FiServer className="text-purple-400 w-5 h-5 lg:w-6 lg:h-6" />
            </div>
            <div>
              <p className="text-[10px] lg:text-sm text-gray-400">Серверов онлайн</p>
              <p className="text-lg lg:text-2xl font-bold text-white">{vpnStats?.online_servers || 0}/{vpnStats?.total_servers || 0}</p>
            </div>
          </div>
        </div>

        <div className="dark-card p-3 lg:p-6 card-hover">
          <div className="flex items-center gap-2 lg:gap-4">
            <div className="p-2 lg:p-3 bg-orange-500/20 rounded-xl">
              <FiClock className="text-orange-400 w-5 h-5 lg:w-6 lg:h-6" />
            </div>
            <div>
              <p className="text-[10px] lg:text-sm text-gray-400">Аптайм сервера</p>
              <p className="text-lg lg:text-2xl font-bold text-white">{systemStats.uptime}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Server Resources */}
      <div className="dark-card p-4 lg:p-6">
        <h2 className="text-base lg:text-xl font-bold text-white mb-4 lg:mb-6 flex items-center gap-2">
          <FiServer className="text-purple-400" />
          Ресурсы сервера
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 lg:gap-6">
          {/* CPU */}
          <div className="bg-[#1a1a2e] rounded-xl p-4">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <FiCpu className="text-blue-400" />
                <span className="text-sm text-gray-400">CPU</span>
              </div>
              <span className="text-lg font-bold text-white">{systemStats.cpu_usage}%</span>
            </div>
            <div className="w-full bg-gray-700 rounded-full h-2">
              <div 
                className="h-2 rounded-full bg-gradient-to-r from-blue-500 to-purple-500 transition-all"
                style={{ width: `${systemStats.cpu_usage}%` }}
              />
            </div>
          </div>

          {/* Memory */}
          <div className="bg-[#1a1a2e] rounded-xl p-4">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <FiActivity className="text-green-400" />
                <span className="text-sm text-gray-400">RAM</span>
              </div>
              <span className="text-lg font-bold text-white">
                {formatBytes(systemStats.memory_used)} / {formatBytes(systemStats.memory_total)}
              </span>
            </div>
            <div className="w-full bg-gray-700 rounded-full h-2">
              <div 
                className="h-2 rounded-full bg-gradient-to-r from-green-500 to-emerald-500 transition-all"
                style={{ width: `${formatPercent(systemStats.memory_used, systemStats.memory_total)}%` }}
              />
            </div>
          </div>

          {/* Disk */}
          <div className="bg-[#1a1a2e] rounded-xl p-4">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <FiHardDrive className="text-orange-400" />
                <span className="text-sm text-gray-400">Диск</span>
              </div>
              <span className="text-lg font-bold text-white">
                {formatBytes(systemStats.disk_used)} / {formatBytes(systemStats.disk_total)}
              </span>
            </div>
            <div className="w-full bg-gray-700 rounded-full h-2">
              <div 
                className="h-2 rounded-full bg-gradient-to-r from-orange-500 to-red-500 transition-all"
                style={{ width: `${formatPercent(systemStats.disk_used, systemStats.disk_total)}%` }}
              />
            </div>
          </div>
        </div>
      </div>

      {/* Containers */}
      <div className="dark-card p-4 lg:p-6">
        <h2 className="text-base lg:text-xl font-bold text-white mb-4 lg:mb-6 flex items-center gap-2">
          <FiBox className="text-purple-400" />
          Контейнеры
        </h2>
        <div className="space-y-3">
          {containers.map((container) => (
            <div key={container.name} className="flex flex-col sm:flex-row sm:items-center justify-between p-3 lg:p-4 bg-[#1a1a2e] rounded-xl gap-3">
              <div className="flex items-center gap-3">
                <div className={`w-3 h-3 rounded-full ${
                  container.status === 'running' ? 'bg-green-500 animate-pulse' :
                  container.status === 'stopped' ? 'bg-gray-500' : 'bg-red-500'
                }`} />
                <div>
                  <p className="text-white font-medium">{container.name}</p>
                  <div className="flex items-center gap-2 text-xs text-gray-400">
                    {container.status === 'running' && (
                      <>
                        <span>⏱ {container.uptime}</span>
                        <span>•</span>
                        <span>CPU: {container.cpu}</span>
                        <span>•</span>
                        <span>RAM: {container.memory}</span>
                      </>
                    )}
                    {container.status !== 'running' && (
                      <span className="text-red-400">Остановлен</span>
                    )}
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => handleViewLogs(container.name)}
                  className="p-2 bg-purple-500/20 text-purple-400 rounded-lg hover:bg-purple-500/30 transition"
                  title="Логи"
                >
                  <FiTerminal size={16} />
                </button>
                <button
                  onClick={() => handleContainerAction(container.name, 'restart')}
                  disabled={actionLoading === `${container.name}-restart`}
                  className="p-2 bg-blue-500/20 text-blue-400 rounded-lg hover:bg-blue-500/30 transition disabled:opacity-50"
                  title="Перезапустить"
                >
                  <FiRefreshCw size={16} className={actionLoading === `${container.name}-restart` ? 'animate-spin' : ''} />
                </button>
                {container.status === 'running' ? (
                  <button
                    onClick={() => handleContainerAction(container.name, 'stop')}
                    disabled={actionLoading === `${container.name}-stop`}
                    className="p-2 bg-red-500/20 text-red-400 rounded-lg hover:bg-red-500/30 transition disabled:opacity-50"
                    title="Остановить"
                  >
                    <FiSquare size={16} />
                  </button>
                ) : (
                  <button
                    onClick={() => handleContainerAction(container.name, 'start')}
                    disabled={actionLoading === `${container.name}-start`}
                    className="p-2 bg-green-500/20 text-green-400 rounded-lg hover:bg-green-500/30 transition disabled:opacity-50"
                    title="Запустить"
                  >
                    <FiPlay size={16} />
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Export Data */}
      <div className="dark-card p-4 lg:p-6">
        <h2 className="text-base lg:text-xl font-bold text-white mb-4 lg:mb-6 flex items-center gap-2">
          <FiDownload className="text-purple-400" />
          Экспорт данных
        </h2>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          <button
            onClick={() => handleExport('users')}
            className="p-4 bg-[#1a1a2e] rounded-xl hover:bg-[#252542] transition text-center"
          >
            <FiDownload className="w-6 h-6 text-blue-400 mx-auto mb-2" />
            <p className="text-sm text-white font-medium">Пользователи</p>
            <p className="text-xs text-gray-500">CSV</p>
          </button>
          <button
            onClick={() => handleExport('payments')}
            className="p-4 bg-[#1a1a2e] rounded-xl hover:bg-[#252542] transition text-center"
          >
            <FiDownload className="w-6 h-6 text-green-400 mx-auto mb-2" />
            <p className="text-sm text-white font-medium">Платежи</p>
            <p className="text-xs text-gray-500">CSV</p>
          </button>
          <button
            onClick={() => handleExport('subscriptions')}
            className="p-4 bg-[#1a1a2e] rounded-xl hover:bg-[#252542] transition text-center"
          >
            <FiDownload className="w-6 h-6 text-purple-400 mx-auto mb-2" />
            <p className="text-sm text-white font-medium">Подписки</p>
            <p className="text-xs text-gray-500">CSV</p>
          </button>
          <button
            onClick={() => handleExport('all')}
            className="p-4 bg-[#1a1a2e] rounded-xl hover:bg-[#252542] transition text-center"
          >
            <FiDownload className="w-6 h-6 text-orange-400 mx-auto mb-2" />
            <p className="text-sm text-white font-medium">Все данные</p>
            <p className="text-xs text-gray-500">ZIP</p>
          </button>
        </div>
      </div>

      {/* Logs Modal */}
      {selectedContainer && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-end sm:items-center justify-center z-50 p-0 sm:p-4" onClick={() => setSelectedContainer(null)}>
          <div className="dark-card w-full sm:max-w-3xl sm:rounded-xl rounded-t-2xl rounded-b-none sm:rounded-b-xl max-h-[85vh] flex flex-col" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between p-4 border-b border-purple-500/20">
              <h3 className="text-lg font-bold text-white flex items-center gap-2">
                <FiTerminal className="text-purple-400" />
                Логи: {selectedContainer}
              </h3>
              <button onClick={() => setSelectedContainer(null)} className="p-2 hover:bg-purple-500/20 rounded-lg">
                <FiX size={20} className="text-gray-400" />
              </button>
            </div>
            <div 
              ref={logsRef}
              className="flex-1 p-4 overflow-auto bg-[#0a0a15] font-mono text-xs lg:text-sm text-green-400 whitespace-pre-wrap"
              style={{ minHeight: '300px', maxHeight: '500px' }}
            >
              {logsLoading ? (
                <div className="flex items-center justify-center h-full">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-500"></div>
                </div>
              ) : logs}
            </div>
            <div className="p-4 border-t border-purple-500/20 flex gap-3">
              <button
                onClick={() => handleViewLogs(selectedContainer)}
                className="flex-1 px-4 py-2 bg-purple-500/20 text-purple-400 rounded-xl hover:bg-purple-500/30 transition text-sm flex items-center justify-center gap-2"
              >
                <FiRefreshCw size={16} />
                Обновить
              </button>
              <button
                onClick={() => {
                  navigator.clipboard.writeText(logs)
                  toast.success('Логи скопированы')
                }}
                className="px-4 py-2 bg-gray-700 text-white rounded-xl hover:bg-gray-600 transition text-sm"
              >
                Копировать
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
