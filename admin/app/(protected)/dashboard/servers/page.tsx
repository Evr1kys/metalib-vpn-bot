'use client'

import { useState } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { apiClient } from '@/lib/api'
import { FiPlus, FiEdit2, FiTrash2, FiActivity, FiServer, FiGlobe, FiCheck, FiX, FiCpu, FiMapPin } from 'react-icons/fi'
import toast from 'react-hot-toast'

function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

export default function ServersPage() {
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [editingServer, setEditingServer] = useState<any>(null)

  const { data: servers, isLoading, refetch } = useQuery({
    queryKey: ['servers'],
    queryFn: () => apiClient.getServers()
  })

  const deleteMutation = useMutation({
    mutationFn: (serverId: number) => apiClient.deleteServer(serverId),
    onSuccess: () => {
      toast.success('Сервер удален')
      refetch()
    },
    onError: () => toast.error('Ошибка удаления'),
  })

  const testConnectionMutation = useMutation({
    mutationFn: (serverId: number) => apiClient.testServerConnection(serverId),
    onSuccess: () => toast.success('Подключение успешно'),
    onError: () => toast.error('Ошибка подключения'),
  })

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-500"></div>
      </div>
    )
  }

  const serverList = Array.isArray(servers) ? servers : []

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold gradient-text">VPN Серверы</h1>
          <p className="mt-2 text-gray-400">Управление VPN серверами</p>
        </div>
        <button 
          onClick={() => { setEditingServer(null); setIsModalOpen(true) }}
          className="btn-gradient px-4 py-2 rounded-xl flex items-center"
        >
          <FiPlus className="mr-2" />
          Добавить сервер
        </button>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="stat-gradient-purple p-4 rounded-xl">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-gray-400 text-sm">Всего серверов</p>
              <p className="text-2xl font-bold text-white">{serverList.length}</p>
            </div>
            <FiServer className="w-8 h-8 text-purple-400" />
          </div>
        </div>
        
        <div className="stat-gradient-green p-4 rounded-xl">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-gray-400 text-sm">Активных</p>
              <p className="text-2xl font-bold text-white">
                {serverList.filter((s: any) => s.is_active).length}
              </p>
            </div>
            <FiActivity className="w-8 h-8 text-green-400" />
          </div>
        </div>

        <div className="stat-gradient-blue p-4 rounded-xl">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-gray-400 text-sm">Подключений</p>
              <p className="text-2xl font-bold text-white">
                {serverList.reduce((acc: number, s: any) => acc + (s.current_load || 0), 0)}
              </p>
            </div>
            <FiGlobe className="w-8 h-8 text-blue-400" />
          </div>
        </div>

        <div className="stat-gradient-orange p-4 rounded-xl">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-gray-400 text-sm">Макс. ёмкость</p>
              <p className="text-2xl font-bold text-white">
                {serverList.reduce((acc: number, s: any) => acc + (s.max_users || 0), 0)}
              </p>
            </div>
            <FiCpu className="w-8 h-8 text-orange-400" />
          </div>
        </div>
      </div>

      {/* Servers Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {serverList.length === 0 ? (
          <div className="lg:col-span-2 dark-card p-12 text-center">
            <FiServer className="w-16 h-16 text-gray-600 mx-auto mb-4" />
            <h3 className="text-xl font-semibold text-white mb-2">Нет серверов</h3>
            <p className="text-gray-400 mb-4">Добавьте первый VPN сервер</p>
            <button 
              onClick={() => { setEditingServer(null); setIsModalOpen(true) }}
              className="btn-gradient px-4 py-2 rounded-xl inline-flex items-center"
            >
              <FiPlus className="mr-2" />
              Добавить сервер
            </button>
          </div>
        ) : (
          serverList.map((server: any) => (
            <div key={server.id} className="dark-card p-6 hover:border-purple-500/50 transition-colors">
              <div className="flex items-start justify-between mb-4">
                <div className="flex items-center space-x-3">
                  <div className="p-3 rounded-xl bg-gradient-to-br from-purple-500 to-pink-500">
                    <FiServer className="w-6 h-6 text-white" />
                  </div>
                  <div>
                    <h3 className="text-xl font-bold text-white">{server.name}</h3>
                    <div className="flex items-center text-sm text-gray-400">
                      <FiMapPin className="w-3 h-3 mr-1" />
                      {server.location}
                    </div>
                  </div>
                </div>
                {server.is_active ? (
                  <span className="px-3 py-1 rounded-full bg-green-500/20 text-green-400 text-sm flex items-center">
                    <FiCheck className="mr-1" /> Активен
                  </span>
                ) : (
                  <span className="px-3 py-1 rounded-full bg-red-500/20 text-red-400 text-sm flex items-center">
                    <FiX className="mr-1" /> Неактивен
                  </span>
                )}
              </div>

              <div className="space-y-2 mb-4">
                <div className="flex justify-between text-sm">
                  <span className="text-gray-400">IP адрес:</span>
                  <span className="font-mono text-white">{server.host}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-400">Тип:</span>
                  <span className="px-2 py-0.5 rounded bg-purple-500/20 text-purple-300 text-xs">
                    {server.vpn_type?.toUpperCase() || 'VLESS'}
                  </span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-400">Загрузка:</span>
                  <span className="text-white">{server.current_load || 0} / {server.max_users || 0}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-400">Трафик (всего):</span>
                  <span className="text-white">{formatBytes(server.total_bandwidth || 0)}</span>
                </div>
              </div>

              {/* Progress bar */}
              <div className="mb-4">
                <div className="w-full bg-[#1a1a2e] rounded-full h-2">
                  <div
                    className="bg-gradient-to-r from-purple-500 to-pink-500 h-2 rounded-full transition-all"
                    style={{
                      width: `${Math.min(100, ((server.current_load || 0) / (server.max_users || 1)) * 100)}%`,
                    }}
                  />
                </div>
              </div>

              <div className="flex space-x-2">
                <button
                  onClick={() => testConnectionMutation.mutate(server.id)}
                  disabled={testConnectionMutation.isPending}
                  className="flex-1 px-3 py-2 rounded-lg bg-[#1a1a2e] border border-purple-500/20 text-gray-300 hover:text-white hover:bg-purple-500/10 transition-colors flex items-center justify-center"
                >
                  <FiActivity className="mr-2" /> Проверить
                </button>
                <button
                  onClick={() => { setEditingServer(server); setIsModalOpen(true) }}
                  className="p-2 rounded-lg bg-[#1a1a2e] border border-purple-500/20 text-gray-300 hover:text-white hover:bg-purple-500/10 transition-colors"
                >
                  <FiEdit2 />
                </button>
                <button
                  onClick={() => {
                    if (confirm('Удалить сервер?')) deleteMutation.mutate(server.id)
                  }}
                  className="p-2 rounded-lg bg-[#1a1a2e] border border-red-500/20 text-red-400 hover:bg-red-500/10 transition-colors"
                >
                  <FiTrash2 />
                </button>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Modal */}
      {isModalOpen && (
        <ServerModal
          server={editingServer}
          onClose={() => setIsModalOpen(false)}
          onComplete={() => { setIsModalOpen(false); refetch() }}
        />
      )}
    </div>
  )
}

function ServerModal({ server, onClose, onComplete }: any) {
  const [formData, setFormData] = useState({
    name: server?.name || '',
    location: server?.location || '',
    host: server?.host || '',
    port: server?.port || 443,
    vpn_type: server?.vpn_type || 'xray',
    max_users: server?.max_users || 100,
    priority: server?.priority || 0,
    is_active: server?.is_active !== false,
  })

  const mutation = useMutation({
    mutationFn: (data: any) =>
      server ? apiClient.updateServer(server.id, data) : apiClient.createServer(data),
    onSuccess: () => {
      toast.success(server ? 'Сервер обновлен' : 'Сервер создан')
      onComplete()
    },
    onError: (err: any) => toast.error(err.response?.data?.detail || 'Ошибка'),
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    mutation.mutate(formData)
  }

  return (
    <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="dark-card max-w-lg w-full">
        <div className="p-6 border-b border-purple-500/20">
          <h2 className="text-2xl font-bold gradient-text">
            {server ? 'Редактировать сервер' : 'Добавить сервер'}
          </h2>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">Название</label>
              <input
                type="text"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                placeholder="Germany #1"
                required
                className="w-full h-11 px-4 bg-[#1a1a2e] border border-purple-500/20 rounded-xl text-white focus:outline-none focus:ring-2 focus:ring-purple-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">Локация</label>
              <input
                type="text"
                value={formData.location}
                onChange={(e) => setFormData({ ...formData, location: e.target.value })}
                placeholder="Frankfurt, DE"
                required
                className="w-full h-11 px-4 bg-[#1a1a2e] border border-purple-500/20 rounded-xl text-white focus:outline-none focus:ring-2 focus:ring-purple-500"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">IP адрес</label>
              <input
                type="text"
                value={formData.host}
                onChange={(e) => setFormData({ ...formData, host: e.target.value })}
                placeholder="85.208.186.231"
                required
                className="w-full h-11 px-4 bg-[#1a1a2e] border border-purple-500/20 rounded-xl text-white focus:outline-none focus:ring-2 focus:ring-purple-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">Макс. юзеров</label>
              <input
                type="number"
                value={formData.max_users}
                onChange={(e) => setFormData({ ...formData, max_users: parseInt(e.target.value) })}
                className="w-full h-11 px-4 bg-[#1a1a2e] border border-purple-500/20 rounded-xl text-white focus:outline-none focus:ring-2 focus:ring-purple-500"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">Тип VPN</label>
              <select
                value={formData.vpn_type}
                onChange={(e) => setFormData({ ...formData, vpn_type: e.target.value })}
                className="w-full h-11 px-4 bg-[#1a1a2e] border border-purple-500/20 rounded-xl text-white focus:outline-none focus:ring-2 focus:ring-purple-500"
              >
                <option value="xray">XRay (VLESS)</option>
                <option value="wireguard">WireGuard</option>
                <option value="amnezia">AmneziaWG</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">Приоритет</label>
              <input
                type="number"
                value={formData.priority}
                onChange={(e) => setFormData({ ...formData, priority: parseInt(e.target.value) })}
                className="w-full h-11 px-4 bg-[#1a1a2e] border border-purple-500/20 rounded-xl text-white focus:outline-none focus:ring-2 focus:ring-purple-500"
              />
            </div>
          </div>

          <label className="flex items-center space-x-3 cursor-pointer py-2">
            <div className="relative">
              <input
                type="checkbox"
                checked={formData.is_active}
                onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
                className="sr-only peer"
              />
              <div className="w-11 h-6 bg-[#1a1a2e] rounded-full peer peer-checked:bg-purple-500 transition-colors"></div>
              <div className="absolute left-1 top-1 w-4 h-4 bg-gray-400 rounded-full peer-checked:translate-x-5 peer-checked:bg-white transition-transform"></div>
            </div>
            <span className="text-sm text-gray-300">Сервер активен</span>
          </label>

          <div className="flex space-x-3 pt-4">
            <button 
              type="submit" 
              className="flex-1 btn-gradient py-3 rounded-xl font-medium"
              disabled={mutation.isPending}
            >
              {mutation.isPending ? 'Сохранение...' : (server ? 'Сохранить' : 'Создать')}
            </button>
            <button 
              type="button" 
              onClick={onClose}
              className="px-6 py-3 rounded-xl bg-[#1a1a2e] border border-purple-500/20 text-gray-300 hover:text-white transition-colors"
            >
              Отмена
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
