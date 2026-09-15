'use client'

import { useEffect, useState } from 'react'
import { apiClient } from '@/lib/api'
import toast from 'react-hot-toast'
import { 
  FiActivity, FiServer, FiUsers, FiArrowUp, FiArrowDown, 
  FiRefreshCw, FiGlobe, FiDatabase, FiClock, FiX, FiEye
} from 'react-icons/fi'

interface UserTraffic {
  uplink: number
  downlink: number
}

interface DomainEntry {
  domain: string
  count: number
}

interface UserInfo {
  telegram_id?: number
  username?: string
  first_name?: string
  uuid?: string
}

interface UserLogData {
  total_requests: number
  last_seen: string | null
  unique_ips: string[]
  top_domains: DomainEntry[]
  unique_domains_count: number
  servers?: { name: string; ip: string }[]
  user_info?: UserInfo
}

interface ServerStats {
  server_id: string
  server_name: string
  server_ip: string
  inbound?: { uplink: number; downlink: number }
  outbound?: { uplink: number; downlink: number }
  users?: Record<string, UserTraffic>
  status: 'online' | 'offline' | 'error'
  error?: string
}

interface TrafficData {
  servers: ServerStats[]
  totals: {
    inbound_uplink: number
    inbound_downlink: number
    outbound_uplink: number
    outbound_downlink: number
    total_traffic: number
  }
}

interface AccessLogsData {
  logs: any[]
  users: Record<string, UserLogData>
  total_entries: number
}

interface UserDetailData {
  user_email: string
  user_info: UserInfo | null
  total_requests: number
  unique_ips: string[]
  servers: { name: string; ip: string; requests: number }[]
  top_domains: DomainEntry[]
  all_domains: DomainEntry[]
  logs: any[]
}

function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

export default function TrafficPage() {
  const [data, setData] = useState<TrafficData | null>(null)
  const [accessLogs, setAccessLogs] = useState<AccessLogsData | null>(null)
  const [loading, setLoading] = useState(true)
  const [loadingLogs, setLoadingLogs] = useState(false)
  const [selectedServer, setSelectedServer] = useState<ServerStats | null>(null)
  const [selectedUser, setSelectedUser] = useState<string | null>(null)
  const [userDetail, setUserDetail] = useState<UserDetailData | null>(null)
  const [loadingUserDetail, setLoadingUserDetail] = useState(false)
  const [activeTab, setActiveTab] = useState<'stats' | 'logs'>('stats')

  useEffect(() => {
    loadTraffic()
    const interval = setInterval(loadTraffic, 30000)
    return () => clearInterval(interval)
  }, [])

  const loadTraffic = async () => {
    try {
      setLoading(true)
      const result = await apiClient.get('/stats/traffic')
      setData(result)
    } catch (error: any) {
      console.error('Error loading traffic stats')
    } finally {
      setLoading(false)
    }
  }

  const loadAccessLogs = async () => {
    try {
      setLoadingLogs(true)
      const result = await apiClient.get('/stats/access-logs')
      setAccessLogs(result)
    } catch (error: any) {
      console.error('Error loading access logs')
    } finally {
      setLoadingLogs(false)
    }
  }

  const loadUserDetail = async (email: string) => {
    try {
      setLoadingUserDetail(true)
      setSelectedUser(email)
      const result = await apiClient.get(`/stats/user-traffic/${encodeURIComponent(email)}`)
      setUserDetail(result)
    } catch (error: any) {
      toast.error('Ошибка загрузки данных пользователя')
    } finally {
      setLoadingUserDetail(false)
    }
  }

  useEffect(() => {
    if (activeTab === 'logs' && !accessLogs) {
      loadAccessLogs()
    }
  }, [activeTab])

  const servers = data?.servers || []
  const totals = data?.totals || { inbound_uplink: 0, inbound_downlink: 0, outbound_uplink: 0, outbound_downlink: 0, total_traffic: 0 }
  const onlineServers = servers.filter(s => s.status === 'online').length

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white">Мониторинг трафика</h1>
          <p className="text-purple-300/70 mt-1">Статистика VPN серверов и пользователей</p>
        </div>
        <button
          onClick={activeTab === 'stats' ? loadTraffic : loadAccessLogs}
          disabled={loading || loadingLogs}
          className="flex items-center gap-2 px-4 py-2.5 btn-gradient rounded-xl font-medium disabled:opacity-50"
        >
          <FiRefreshCw className={loading || loadingLogs ? 'animate-spin' : ''} size={18} />
          Обновить
        </button>
      </div>

      {/* Tabs */}
      <div className="flex gap-2">
        <button
          onClick={() => setActiveTab('stats')}
          className={`px-5 py-2.5 rounded-xl font-medium transition ${
            activeTab === 'stats'
              ? 'btn-gradient'
              : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
          }`}
        >
          <div className="flex items-center gap-2">
            <FiActivity size={18} />
            Статистика серверов
          </div>
        </button>
        <button
          onClick={() => setActiveTab('logs')}
          className={`px-5 py-2.5 rounded-xl font-medium transition ${
            activeTab === 'logs'
              ? 'btn-gradient'
              : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
          }`}
        >
          <div className="flex items-center gap-2">
            <FiEye size={18} />
            Логи пользователей
          </div>
        </button>
      </div>

      {/* Stats Tab */}
      {activeTab === 'stats' && (
        <>
          {/* Stats Cards */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
            <div className="dark-card p-6 card-hover stat-gradient-blue">
              <div className="flex items-center gap-4">
                <div className="p-3 bg-blue-500/20 rounded-xl">
                  <FiServer className="text-blue-400" size={24} />
                </div>
                <div>
                  <p className="text-sm text-gray-400">Серверов онлайн</p>
                  <p className="text-2xl font-bold text-white">{onlineServers}/{servers.length}</p>
                </div>
              </div>
            </div>

            <div className="dark-card p-6 card-hover stat-gradient-green">
              <div className="flex items-center gap-4">
                <div className="p-3 bg-green-500/20 rounded-xl">
                  <FiArrowUp className="text-green-400" size={24} />
                </div>
                <div>
                  <p className="text-sm text-gray-400">Исходящий</p>
                  <p className="text-2xl font-bold text-white">{formatBytes(totals.outbound_uplink)}</p>
                </div>
              </div>
            </div>

            <div className="dark-card p-6 card-hover stat-gradient-purple">
              <div className="flex items-center gap-4">
                <div className="p-3 bg-purple-500/20 rounded-xl">
                  <FiArrowDown className="text-purple-400" size={24} />
                </div>
                <div>
                  <p className="text-sm text-gray-400">Входящий</p>
                  <p className="text-2xl font-bold text-white">{formatBytes(totals.inbound_downlink)}</p>
                </div>
              </div>
            </div>

            <div className="dark-card p-6 card-hover stat-gradient-orange">
              <div className="flex items-center gap-4">
                <div className="p-3 bg-orange-500/20 rounded-xl">
                  <FiDatabase className="text-orange-400" size={24} />
                </div>
                <div>
                  <p className="text-sm text-gray-400">Всего трафика</p>
                  <p className="text-2xl font-bold text-white">{formatBytes(totals.total_traffic)}</p>
                </div>
              </div>
            </div>
          </div>

          {/* Servers Grid */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {loading ? (
              <div className="lg:col-span-2 flex items-center justify-center h-64">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-500"></div>
              </div>
            ) : servers.length === 0 ? (
              <div className="lg:col-span-2 dark-card p-12 text-center">
                <FiServer size={48} className="text-gray-600 mx-auto mb-4" />
                <p className="text-gray-500">Нет данных о серверах</p>
              </div>
            ) : (
              servers.map((server) => (
                <div key={server.server_id} className="dark-card p-6 card-hover">
                  <div className="flex items-start justify-between mb-4">
                    <div className="flex items-center gap-3">
                      <div className="p-3 rounded-xl bg-gradient-to-br from-purple-500 to-pink-500">
                        <FiServer className="text-white" size={24} />
                      </div>
                      <div>
                        <h3 className="text-xl font-bold text-white">{server.server_name}</h3>
                        <p className="text-sm text-gray-400 font-mono">{server.server_ip}</p>
                      </div>
                    </div>
                    <span className={`px-3 py-1 rounded-full text-xs font-medium ${
                      server.status === 'online' 
                        ? 'bg-green-500/20 text-green-400' 
                        : 'bg-red-500/20 text-red-400'
                    }`}>
                      {server.status === 'online' ? 'Онлайн' : 'Офлайн'}
                    </span>
                  </div>

                  {server.status === 'online' ? (
                    <div className="space-y-4">
                      <div className="grid grid-cols-2 gap-4">
                        <div className="bg-purple-500/10 rounded-xl p-4">
                          <div className="flex items-center gap-2 text-gray-400 text-sm mb-1">
                            <FiArrowUp size={14} />
                            Отправлено
                          </div>
                          <p className="text-xl font-bold text-white">
                            {formatBytes(server.inbound?.uplink || 0)}
                          </p>
                        </div>
                        <div className="bg-purple-500/10 rounded-xl p-4">
                          <div className="flex items-center gap-2 text-gray-400 text-sm mb-1">
                            <FiArrowDown size={14} />
                            Получено
                          </div>
                          <p className="text-xl font-bold text-white">
                            {formatBytes(server.inbound?.downlink || 0)}
                          </p>
                        </div>
                      </div>

                      {server.users && Object.keys(server.users).length > 0 && (
                        <div>
                          <p className="text-sm text-gray-400 mb-2">
                            <FiUsers className="inline mr-1" />
                            Активных пользователей: {Object.keys(server.users).length}
                          </p>
                          <button
                            onClick={() => setSelectedServer(server)}
                            className="w-full px-4 py-2 bg-purple-500/20 text-purple-400 rounded-xl hover:bg-purple-500/30 transition text-sm"
                          >
                            Показать пользователей
                          </button>
                        </div>
                      )}
                    </div>
                  ) : (
                    <p className="text-red-400 text-sm">{server.error || 'Сервер недоступен'}</p>
                  )}
                </div>
              ))
            )}
          </div>
        </>
      )}

      {/* Logs Tab */}
      {activeTab === 'logs' && (
        <div className="dark-card overflow-hidden">
          <div className="px-6 py-4 border-b border-purple-500/20">
            <h2 className="text-lg font-semibold text-white">Активность пользователей</h2>
            <p className="text-sm text-gray-400">Данные из access.log VPN серверов</p>
          </div>

          {loadingLogs ? (
            <div className="flex items-center justify-center h-64">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-500"></div>
            </div>
          ) : !accessLogs || Object.keys(accessLogs.users || {}).length === 0 ? (
            <div className="p-12 text-center">
              <FiEye size={48} className="text-gray-600 mx-auto mb-4" />
              <p className="text-gray-500">Нет данных о активности</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-purple-500/20 bg-purple-500/5">
                    <th className="px-6 py-4 text-left text-xs font-semibold text-purple-300 uppercase">Пользователь</th>
                    <th className="px-6 py-4 text-center text-xs font-semibold text-purple-300 uppercase">Запросов</th>
                    <th className="px-6 py-4 text-center text-xs font-semibold text-purple-300 uppercase">IP адресов</th>
                    <th className="px-6 py-4 text-center text-xs font-semibold text-purple-300 uppercase">Доменов</th>
                    <th className="px-6 py-4 text-left text-xs font-semibold text-purple-300 uppercase">Топ домены</th>
                    <th className="px-6 py-4 text-center text-xs font-semibold text-purple-300 uppercase">Действия</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-purple-500/10">
                  {Object.entries(accessLogs.users).map(([email, userData]) => (
                    <tr key={email} className="hover:bg-purple-500/5 transition-colors">
                      <td className="px-6 py-4">
                        <div>
                          <p className="font-medium text-white">{email}</p>
                          {userData.user_info && (
                            <p className="text-xs text-gray-500">
                              {userData.user_info.first_name} 
                              {userData.user_info.username && ` (@${userData.user_info.username})`}
                            </p>
                          )}
                        </div>
                      </td>
                      <td className="px-6 py-4 text-center">
                        <span className="font-semibold text-blue-400">{userData.total_requests}</span>
                      </td>
                      <td className="px-6 py-4 text-center">
                        <span className="text-gray-300">{userData.unique_ips.length}</span>
                      </td>
                      <td className="px-6 py-4 text-center">
                        <span className="text-gray-300">{userData.unique_domains_count}</span>
                      </td>
                      <td className="px-6 py-4">
                        <div className="flex flex-wrap gap-1">
                          {userData.top_domains.slice(0, 3).map((d, i) => (
                            <span key={i} className="px-2 py-0.5 bg-purple-500/20 text-purple-300 rounded text-xs">
                              {d.domain}
                            </span>
                          ))}
                        </div>
                      </td>
                      <td className="px-6 py-4 text-center">
                        <button
                          onClick={() => loadUserDetail(email)}
                          className="p-2 hover:bg-purple-500/20 text-purple-400 rounded-lg transition"
                          title="Подробнее"
                        >
                          <FiEye size={18} />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Server Users Modal */}
      {selectedServer && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50 p-4" onClick={() => setSelectedServer(null)}>
          <div className="dark-card max-w-2xl w-full max-h-[80vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between p-6 border-b border-purple-500/20">
              <h3 className="text-xl font-bold text-white">
                Пользователи: {selectedServer.server_name}
              </h3>
              <button onClick={() => setSelectedServer(null)} className="p-2 hover:bg-purple-500/20 rounded-lg">
                <FiX size={20} className="text-gray-400" />
              </button>
            </div>
            
            <div className="p-6">
              {selectedServer.users && Object.entries(selectedServer.users).length > 0 ? (
                <div className="space-y-3">
                  {Object.entries(selectedServer.users).map(([email, traffic]) => (
                    <div key={email} className="flex items-center justify-between p-4 bg-purple-500/10 rounded-xl">
                      <span className="font-mono text-white">{email}</span>
                      <div className="flex items-center gap-4 text-sm">
                        <span className="text-green-400">
                          <FiArrowUp className="inline mr-1" size={14} />
                          {formatBytes(traffic.uplink)}
                        </span>
                        <span className="text-blue-400">
                          <FiArrowDown className="inline mr-1" size={14} />
                          {formatBytes(traffic.downlink)}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-gray-500 text-center py-8">Нет активных пользователей</p>
              )}
            </div>
          </div>
        </div>
      )}

      {/* User Detail Modal */}
      {selectedUser && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50 p-4" onClick={() => { setSelectedUser(null); setUserDetail(null) }}>
          <div className="dark-card max-w-3xl w-full max-h-[80vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between p-6 border-b border-purple-500/20">
              <h3 className="text-xl font-bold text-white">
                Активность: {selectedUser}
              </h3>
              <button onClick={() => { setSelectedUser(null); setUserDetail(null) }} className="p-2 hover:bg-purple-500/20 rounded-lg">
                <FiX size={20} className="text-gray-400" />
              </button>
            </div>
            
            <div className="p-6">
              {loadingUserDetail ? (
                <div className="flex items-center justify-center h-32">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-500"></div>
                </div>
              ) : userDetail ? (
                <div className="space-y-6">
                  {/* User info */}
                  {userDetail.user_info && (
                    <div className="bg-purple-500/10 rounded-xl p-4">
                      <h4 className="font-semibold text-white mb-2">Пользователь</h4>
                      <p className="text-gray-300">
                        {userDetail.user_info.first_name}
                        {userDetail.user_info.username && ` (@${userDetail.user_info.username})`}
                      </p>
                      {userDetail.user_info.telegram_id && (
                        <p className="text-sm text-gray-500">ID: {userDetail.user_info.telegram_id}</p>
                      )}
                    </div>
                  )}

                  {/* Stats */}
                  <div className="grid grid-cols-3 gap-4">
                    <div className="bg-blue-500/10 rounded-xl p-4 text-center">
                      <p className="text-2xl font-bold text-blue-400">{userDetail.total_requests}</p>
                      <p className="text-sm text-gray-400">Запросов</p>
                    </div>
                    <div className="bg-green-500/10 rounded-xl p-4 text-center">
                      <p className="text-2xl font-bold text-green-400">{userDetail.unique_ips.length}</p>
                      <p className="text-sm text-gray-400">IP адресов</p>
                    </div>
                    <div className="bg-purple-500/10 rounded-xl p-4 text-center">
                      <p className="text-2xl font-bold text-purple-400">{userDetail.all_domains.length}</p>
                      <p className="text-sm text-gray-400">Доменов</p>
                    </div>
                  </div>

                  {/* Top domains */}
                  <div>
                    <h4 className="font-semibold text-white mb-3">Топ посещаемых доменов</h4>
                    <div className="space-y-2">
                      {userDetail.top_domains.slice(0, 10).map((d, i) => (
                        <div key={i} className="flex items-center justify-between p-3 bg-purple-500/10 rounded-lg">
                          <span className="text-gray-300">{d.domain}</span>
                          <span className="text-purple-400 font-medium">{d.count}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              ) : (
                <p className="text-gray-500 text-center py-8">Нет данных</p>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
