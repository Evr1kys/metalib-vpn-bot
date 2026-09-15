'use client'

import { useState } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { apiClient } from '@/lib/api'
import { FiPlus, FiEdit2, FiTrash2, FiStar, FiCheck, FiX, FiDollarSign, FiClock, FiServer, FiTag } from 'react-icons/fi'
import toast from 'react-hot-toast'

export default function PlansPage() {
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [editingPlan, setEditingPlan] = useState<any>(null)

  const { data: plans, isLoading, refetch } = useQuery({
    queryKey: ['plans'],
    queryFn: () => apiClient.getPlans()
  })

  const deleteMutation = useMutation({
    mutationFn: (planId: string) => apiClient.deletePlan(planId),
    onSuccess: () => {
      toast.success('Тариф удален')
      refetch()
    },
    onError: () => toast.error('Ошибка удаления'),
  })

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-500"></div>
      </div>
    )
  }

  const planList = Array.isArray(plans) ? plans : []

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold gradient-text">Тарифы</h1>
          <p className="mt-2 text-gray-400">Управление тарифными планами</p>
        </div>
        <button 
          onClick={() => { setEditingPlan(null); setIsModalOpen(true) }}
          className="btn-gradient px-4 py-2 rounded-xl flex items-center"
        >
          <FiPlus className="mr-2" />
          Добавить тариф
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-4">
        <div className="stat-gradient-purple p-4 rounded-xl">
          <p className="text-gray-400 text-sm">Всего тарифов</p>
          <p className="text-2xl font-bold text-white">{planList.length}</p>
        </div>
        <div className="stat-gradient-green p-4 rounded-xl">
          <p className="text-gray-400 text-sm">Активных</p>
          <p className="text-2xl font-bold text-white">{planList.filter((p: any) => p.is_active).length}</p>
        </div>
        <div className="stat-gradient-blue p-4 rounded-xl">
          <p className="text-gray-400 text-sm">Избранных</p>
          <p className="text-2xl font-bold text-white">{planList.filter((p: any) => p.is_featured).length}</p>
        </div>
      </div>

      {/* Plans Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {planList.length === 0 ? (
          <div className="col-span-full dark-card p-12 text-center">
            <FiTag className="w-16 h-16 text-gray-600 mx-auto mb-4" />
            <h3 className="text-xl font-semibold text-white mb-2">Нет тарифов</h3>
            <p className="text-gray-400 mb-4">Создайте первый тарифный план</p>
            <button 
              onClick={() => { setEditingPlan(null); setIsModalOpen(true) }}
              className="btn-gradient px-4 py-2 rounded-xl inline-flex items-center"
            >
              <FiPlus className="mr-2" /> Создать тариф
            </button>
          </div>
        ) : (
          planList.map((plan: any) => (
            <div 
              key={plan.id} 
              className={`dark-card p-6 relative ${plan.is_featured ? 'border-2 border-purple-500' : ''}`}
            >
              {plan.is_featured && (
                <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-1 bg-purple-500 rounded-full text-white text-xs font-medium flex items-center">
                  <FiStar className="mr-1" /> Популярный
                </div>
              )}

              <div className="flex items-start justify-between mb-4 pt-2">
                <div>
                  <h3 className="text-xl font-bold text-white">{plan.name}</h3>
                  <p className="text-sm text-gray-400">{plan.description || 'Без описания'}</p>
                </div>
                {plan.is_active ? (
                  <span className="px-2 py-1 rounded-full bg-green-500/20 text-green-400 text-xs">
                    <FiCheck className="inline mr-1" /> Активен
                  </span>
                ) : (
                  <span className="px-2 py-1 rounded-full bg-red-500/20 text-red-400 text-xs">
                    <FiX className="inline mr-1" /> Неактивен
                  </span>
                )}
              </div>

              <div className="text-3xl font-bold text-white mb-4">
                {plan.price.toLocaleString()} <span className="text-lg text-gray-400">{plan.currency}</span>
              </div>

              <div className="space-y-2 mb-6">
                <div className="flex items-center text-gray-300 text-sm">
                  <FiClock className="mr-2 text-purple-400" />
                  {plan.duration_days} дней
                </div>
                {plan.server_ids && plan.server_ids.length > 0 && (
                  <div className="flex items-center text-gray-300 text-sm">
                    <FiServer className="mr-2 text-purple-400" />
                    {plan.server_ids.length} сервер(ов)
                  </div>
                )}
              </div>

              <div className="flex space-x-2">
                <button
                  onClick={() => { setEditingPlan(plan); setIsModalOpen(true) }}
                  className="flex-1 px-3 py-2 rounded-lg bg-[#1a1a2e] border border-purple-500/20 text-gray-300 hover:text-white hover:bg-purple-500/10 transition-colors flex items-center justify-center"
                >
                  <FiEdit2 className="mr-2" /> Изменить
                </button>
                <button
                  onClick={() => {
                    if (confirm('Удалить тариф?')) deleteMutation.mutate(plan.id)
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
        <PlanModal
          plan={editingPlan}
          onClose={() => setIsModalOpen(false)}
          onComplete={() => { setIsModalOpen(false); refetch() }}
        />
      )}
    </div>
  )
}

function PlanModal({ plan, onClose, onComplete }: any) {
  const [formData, setFormData] = useState({
    name: plan?.name || '',
    description: plan?.description || '',
    price: plan?.price || 0,
    currency: plan?.currency || 'RUB',
    duration_days: plan?.duration_days || 30,
    server_ids: plan?.server_ids || [],
    is_active: plan?.is_active !== false,
    is_featured: plan?.is_featured || false,
    sort_order: plan?.sort_order || 0,
  })

  const { data: servers } = useQuery({
    queryKey: ['servers'],
    queryFn: () => apiClient.getServers()
  })
  const serverList = Array.isArray(servers) ? servers : []

  const toggleServer = (serverId: string) => {
    const current = formData.server_ids || []
    if (current.includes(serverId)) {
      setFormData({ ...formData, server_ids: current.filter((id: string) => id !== serverId) })
    } else {
      setFormData({ ...formData, server_ids: [...current, serverId] })
    }
  }

  const mutation = useMutation({
    mutationFn: (data: any) =>
      plan ? apiClient.updatePlan(plan.id, data) : apiClient.createPlan(data),
    onSuccess: () => {
      toast.success(plan ? 'Тариф обновлен' : 'Тариф создан')
      onComplete()
    },
    onError: (err: any) => toast.error(err.response?.data?.detail || 'Ошибка'),
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!formData.server_ids || formData.server_ids.length === 0) {
      toast.error('Выберите хотя бы один сервер')
      return
    }
    mutation.mutate(formData)
  }

  return (
    <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="dark-card max-w-lg w-full">
        <div className="p-6 border-b border-purple-500/20">
          <h2 className="text-2xl font-bold gradient-text">
            {plan ? 'Редактировать тариф' : 'Новый тариф'}
          </h2>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">Название</label>
            <input
              type="text"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              placeholder="Базовый / Стандарт / Премиум"
              required
              className="w-full h-11 px-4 bg-[#1a1a2e] border border-purple-500/20 rounded-xl text-white focus:outline-none focus:ring-2 focus:ring-purple-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">Описание</label>
            <input
              type="text"
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              placeholder="Краткое описание тарифа"
              className="w-full h-11 px-4 bg-[#1a1a2e] border border-purple-500/20 rounded-xl text-white focus:outline-none focus:ring-2 focus:ring-purple-500"
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">Цена</label>
              <input
                type="number"
                value={formData.price}
                onChange={(e) => setFormData({ ...formData, price: parseFloat(e.target.value) })}
                required
                className="w-full h-11 px-4 bg-[#1a1a2e] border border-purple-500/20 rounded-xl text-white focus:outline-none focus:ring-2 focus:ring-purple-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">Валюта</label>
              <select
                value={formData.currency}
                onChange={(e) => setFormData({ ...formData, currency: e.target.value })}
                className="w-full h-11 px-4 bg-[#1a1a2e] border border-purple-500/20 rounded-xl text-white focus:outline-none focus:ring-2 focus:ring-purple-500"
              >
                <option value="RUB">RUB (₽)</option>
                <option value="USD">USD ($)</option>
                <option value="EUR">EUR (€)</option>
              </select>
            </div>
          </div>

          <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">Длительность (дней)</label>
              <input
                type="number"
                value={formData.duration_days}
                onChange={(e) => setFormData({ ...formData, duration_days: parseInt(e.target.value) })}
                required
                className="w-full h-11 px-4 bg-[#1a1a2e] border border-purple-500/20 rounded-xl text-white focus:outline-none focus:ring-2 focus:ring-purple-500"
              />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Серверы <span className="text-red-400">*</span>
            </label>
            <div className="max-h-32 overflow-y-auto bg-[#1a1a2e] border border-purple-500/20 rounded-xl p-2 space-y-1">
              {serverList.length === 0 ? (
                <p className="text-gray-500 text-sm p-2">Нет доступных серверов</p>
              ) : (
                serverList.map((server: any) => (
                  <label key={server.id} className="flex items-center p-2 hover:bg-purple-500/10 rounded-lg cursor-pointer">
                    <input
                      type="checkbox"
                      checked={(formData.server_ids || []).includes(server.id)}
                      onChange={() => toggleServer(server.id)}
                      className="w-4 h-4 rounded border-purple-500/20 bg-[#0d0d1a] text-purple-500 focus:ring-purple-500"
                    />
                    <span className="ml-2 text-sm text-gray-300">{server.name}</span>
                    <span className="ml-auto text-xs text-gray-500">{server.region}</span>
                  </label>
                ))
              )}
            </div>
            {formData.server_ids.length === 0 && (
              <p className="text-xs text-yellow-400 mt-1">Выберите хотя бы один сервер</p>
            )}
          </div>

          <div className="flex space-x-6">
            <label className="flex items-center space-x-3 cursor-pointer">
              <div className="relative">
                <input
                  type="checkbox"
                  checked={formData.is_active}
                  onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
                  className="sr-only peer"
                />
                <div className="w-11 h-6 bg-[#1a1a2e] rounded-full peer peer-checked:bg-green-500 transition-colors"></div>
                <div className="absolute left-1 top-1 w-4 h-4 bg-gray-400 rounded-full peer-checked:translate-x-5 peer-checked:bg-white transition-transform"></div>
              </div>
              <span className="text-sm text-gray-300">Активен</span>
            </label>

            <label className="flex items-center space-x-3 cursor-pointer">
              <div className="relative">
                <input
                  type="checkbox"
                  checked={formData.is_featured}
                  onChange={(e) => setFormData({ ...formData, is_featured: e.target.checked })}
                  className="sr-only peer"
                />
                <div className="w-11 h-6 bg-[#1a1a2e] rounded-full peer peer-checked:bg-purple-500 transition-colors"></div>
                <div className="absolute left-1 top-1 w-4 h-4 bg-gray-400 rounded-full peer-checked:translate-x-5 peer-checked:bg-white transition-transform"></div>
              </div>
              <span className="text-sm text-gray-300">Популярный</span>
            </label>
          </div>

          <div className="flex space-x-3 pt-4">
            <button 
              type="submit" 
              className="flex-1 btn-gradient py-3 rounded-xl font-medium"
              disabled={mutation.isLoading}
            >
              {mutation.isLoading ? 'Сохранение...' : (plan ? 'Сохранить' : 'Создать')}
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
