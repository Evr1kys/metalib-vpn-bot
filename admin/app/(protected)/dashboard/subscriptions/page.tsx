'use client'

import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/lib/api'
import toast from 'react-hot-toast'
import { 
  FiUsers, FiSearch, FiPlus, FiClock, FiX, FiCalendar, 
  FiAlertCircle, FiCheckCircle, FiGift, FiTrash2, FiEdit2,
  FiChevronLeft, FiChevronRight, FiRefreshCw, FiMessageSquare
} from 'react-icons/fi'

interface User {
  id: string
  telegram_id: number
  username: string | null
  first_name: string | null
  last_name: string | null
  is_banned: boolean
  created_at: string
  has_subscription: boolean
  subscription: {
    id: string
    status: string
    expires_at: string | null
    plan_id: string | null
  } | null
}

interface Plan {
  id: string
  name: string
  duration_days: number
  price: number
}

export default function SubscriptionsManagementPage() {
  const queryClient = useQueryClient()
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(0)
  const [selectedUser, setSelectedUser] = useState<User | null>(null)
  const [showModal, setShowModal] = useState(false)
  const [modalAction, setModalAction] = useState<'give' | 'extend' | 'cancel' | 'notify'>('give')
  const [selectedPlanId, setSelectedPlanId] = useState('')
  const [extendDays, setExtendDays] = useState(30)
  const [notifyMessage, setNotifyMessage] = useState('')
  const limit = 20

  const { data: usersData, isLoading, refetch } = useQuery({
    queryKey: ['admin-users-subs', page, search],
    queryFn: async () => {
      const params: any = { skip: page * limit, limit }
      if (search) params.search = search
      return apiClient.getUsers(params)
    },
    placeholderData: (previousData) => previousData
  })

  const { data: plans } = useQuery({
    queryKey: ['admin-plans'],
    queryFn: () => apiClient.getPlans()
  })

  const users = usersData?.users || []
  const totalUsers = usersData?.total || 0

  // Mutations
  const giveSubscription = useMutation({
    mutationFn: async ({ userId, planId }: { userId: string, planId: string }) => {
      return apiClient.post(`/admin/users/${userId}/subscription`, { plan_id: planId })
    },
    onSuccess: () => {
      toast.success('✓ Подписка выдана')
      queryClient.invalidateQueries({ queryKey: ['admin-users-subs'] })
      closeModal()
    },
    onError: (e: any) => toast.error(e.response?.data?.detail || 'Ошибка')
  })

  const extendSubscription = useMutation({
    mutationFn: async ({ userId, days }: { userId: string, days: number }) => {
      return apiClient.post(`/admin/users/${userId}/extend`, { days })
    },
    onSuccess: (data) => {
      toast.success(`✓ Подписка продлена до ${new Date(data.expires_at).toLocaleDateString('ru-RU')}`)
      queryClient.invalidateQueries({ queryKey: ['admin-users-subs'] })
      closeModal()
    },
    onError: (e: any) => toast.error(e.response?.data?.detail || 'Ошибка')
  })

  const cancelSubscription = useMutation({
    mutationFn: async (userId: string) => {
      return apiClient.post(`/admin/users/${userId}/cancel-subscription`)
    },
    onSuccess: () => {
      toast.success('✓ Подписка отменена')
      queryClient.invalidateQueries({ queryKey: ['admin-users-subs'] })
      closeModal()
    },
    onError: (e: any) => toast.error(e.response?.data?.detail || 'Ошибка')
  })

  const sendNotification = useMutation({
    mutationFn: async ({ userId, message }: { userId: number, message: string }) => {
      return apiClient.post('/admin/notifications/send', { user_id: userId, message })
    },
    onSuccess: () => {
      toast.success('✓ Уведомление отправлено')
      closeModal()
    },
    onError: (e: any) => toast.error(e.response?.data?.detail || 'Ошибка отправки')
  })

  const openModal = (user: User, action: 'give' | 'extend' | 'cancel' | 'notify') => {
    setSelectedUser(user)
    setModalAction(action)
    setShowModal(true)
    setSelectedPlanId(plans?.[0]?.id || '')
    setExtendDays(30)
    setNotifyMessage('')
  }

  const closeModal = () => {
    setShowModal(false)
    setSelectedUser(null)
  }

  const handleSubmit = () => {
    if (!selectedUser) return

    switch (modalAction) {
      case 'give':
        if (!selectedPlanId) {
          toast.error('Выберите тариф')
          return
        }
        giveSubscription.mutate({ userId: selectedUser.id, planId: selectedPlanId })
        break
      case 'extend':
        if (extendDays <= 0) {
          toast.error('Укажите количество дней')
          return
        }
        extendSubscription.mutate({ userId: selectedUser.id, days: extendDays })
        break
      case 'cancel':
        cancelSubscription.mutate(selectedUser.id)
        break
      case 'notify':
        if (!notifyMessage.trim()) {
          toast.error('Введите сообщение')
          return
        }
        sendNotification.mutate({ userId: selectedUser.telegram_id, message: notifyMessage })
        break
    }
  }

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return '-'
    return new Date(dateStr).toLocaleDateString('ru-RU', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  const getDaysLeft = (expiresAt: string | null) => {
    if (!expiresAt) return null
    const diff = new Date(expiresAt).getTime() - Date.now()
    return Math.ceil(diff / (1000 * 60 * 60 * 24))
  }

  const totalPages = Math.ceil(totalUsers / limit)

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
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold gradient-text">Управление подписками</h1>
          <p className="text-gray-400 mt-1">Полный контроль над подписками пользователей</p>
        </div>
        <button onClick={() => refetch()} className="p-3 rounded-xl dark-card hover:bg-purple-500/10">
          <FiRefreshCw className="w-5 h-5 text-gray-400" />
        </button>
      </div>

      {/* Search */}
      <div className="dark-card p-4">
        <div className="relative">
          <FiSearch className="absolute left-4 top-1/2 transform -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(0) }}
            placeholder="Поиск по имени, username или Telegram ID..."
            className="w-full pl-12 pr-4 py-3 dark-input rounded-xl"
          />
        </div>
      </div>

      {/* Users Table */}
      <div className="dark-card overflow-hidden">
        {/* Desktop Table */}
        <div className="hidden lg:block overflow-x-auto">
          <table className="w-full">
            <thead className="bg-[#1a1a2e]">
              <tr>
                <th className="px-6 py-4 text-left text-xs font-semibold text-gray-400 uppercase">Пользователь</th>
                <th className="px-6 py-4 text-left text-xs font-semibold text-gray-400 uppercase">Telegram ID</th>
                <th className="px-6 py-4 text-left text-xs font-semibold text-gray-400 uppercase">Подписка</th>
                <th className="px-6 py-4 text-left text-xs font-semibold text-gray-400 uppercase">Истекает</th>
                <th className="px-6 py-4 text-left text-xs font-semibold text-gray-400 uppercase">Дней</th>
                <th className="px-6 py-4 text-center text-xs font-semibold text-gray-400 uppercase w-32">Действия</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-purple-500/10">
            {users.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-6 py-12 text-center text-gray-500">
                  <FiUsers className="w-12 h-12 mx-auto mb-3 opacity-50" />
                  <p>Пользователи не найдены</p>
                </td>
              </tr>
            ) : (
              users.map((user: User) => {
                const daysLeft = getDaysLeft(user.subscription?.expires_at || null)
                
                return (
                  <tr key={user.id} className="hover:bg-purple-500/5 transition">
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-full bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center">
                          <span className="text-white font-bold text-sm">
                            {(user.first_name || user.username || 'U')[0].toUpperCase()}
                          </span>
                        </div>
                        <div>
                          <p className="text-white font-medium">
                            {user.first_name || user.username || `User #${user.telegram_id}`}
                          </p>
                          {user.username && (
                            <p className="text-xs text-gray-500">@{user.username}</p>
                          )}
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <code className="text-purple-300">{user.telegram_id}</code>
                    </td>
                    <td className="px-6 py-4">
                      {user.has_subscription ? (
                        <span className="inline-flex items-center px-3 py-1 bg-green-500/20 text-green-400 rounded-full text-xs font-medium">
                          <FiCheckCircle className="mr-1" /> Активна
                        </span>
                      ) : (
                        <span className="inline-flex items-center px-3 py-1 bg-gray-500/20 text-gray-400 rounded-full text-xs font-medium">
                          <FiX className="mr-1" /> Нет
                        </span>
                      )}
                    </td>
                    <td className="px-6 py-4 text-gray-400">
                      {formatDate(user.subscription?.expires_at || null)}
                    </td>
                    <td className="px-6 py-4">
                      {daysLeft !== null ? (
                        <span className={`font-semibold ${
                          daysLeft <= 3 ? 'text-red-400' : 
                          daysLeft <= 7 ? 'text-yellow-400' : 'text-green-400'
                        }`}>
                          {daysLeft} дн.
                        </span>
                      ) : (
                        <span className="text-gray-500">-</span>
                      )}
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center justify-center gap-1">
                        <button
                          onClick={() => openModal(user, 'give')}
                          className="p-2 hover:bg-green-500/20 text-green-400 rounded-lg transition"
                          title="Выдать подписку"
                        >
                          <FiGift size={18} />
                        </button>
                        {user.has_subscription && (
                          <>
                            <button
                              onClick={() => openModal(user, 'extend')}
                              className="p-2 hover:bg-blue-500/20 text-blue-400 rounded-lg transition"
                              title="Продлить подписку"
                            >
                              <FiClock size={18} />
                            </button>
                            <button
                              onClick={() => openModal(user, 'cancel')}
                              className="p-2 hover:bg-red-500/20 text-red-400 rounded-lg transition"
                              title="Отменить подписку"
                            >
                              <FiTrash2 size={18} />
                            </button>
                          </>
                        )}
                        <button
                          onClick={() => openModal(user, 'notify')}
                          className="p-2 hover:bg-purple-500/20 text-purple-400 rounded-lg transition"
                          title="Отправить уведомление"
                        >
                          <FiMessageSquare size={18} />
                        </button>
                      </div>
                    </td>
                  </tr>
                )
              })
            )}
          </tbody>
        </table>
        </div>

        {/* Mobile Cards */}
        <div className="lg:hidden divide-y divide-purple-500/10">
          {users.length === 0 ? (
            <div className="p-8 text-center">
              <FiUsers size={40} className="text-gray-600 mx-auto mb-2" />
              <p className="text-gray-500 text-sm">Пользователи не найдены</p>
            </div>
          ) : (
            users.map((user: User) => {
              const daysLeft = getDaysLeft(user.subscription?.expires_at || null)
              return (
                <div key={user.id} className="p-3 hover:bg-purple-500/5">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <div className="w-8 h-8 rounded-full bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center text-white font-bold text-sm">
                        {(user.first_name || user.username || 'U')[0].toUpperCase()}
                      </div>
                      <div>
                        <p className="text-sm font-medium text-white truncate max-w-[140px]">
                          {user.first_name || user.username || `User #${user.telegram_id}`}
                        </p>
                        <p className="text-[10px] text-gray-500">ID: {user.telegram_id}</p>
                      </div>
                    </div>
                    <span className={`text-[10px] px-2 py-0.5 rounded-full ${
                      user.has_subscription 
                        ? 'bg-green-500/20 text-green-400' 
                        : 'bg-gray-500/20 text-gray-400'
                    }`}>
                      {user.has_subscription ? 'Активна' : 'Нет'}
                    </span>
                  </div>
                  <div className="flex items-center justify-between text-[10px] text-gray-400 mb-2">
                    <span>{user.has_subscription ? `до ${formatDate(user.subscription?.expires_at || null)}` : '-'}</span>
                    {daysLeft !== null && (
                      <span className={`font-semibold ${
                        daysLeft <= 3 ? 'text-red-400' : 
                        daysLeft <= 7 ? 'text-yellow-400' : 'text-green-400'
                      }`}>
                        {daysLeft} дн.
                      </span>
                    )}
                  </div>
                  <div className="flex items-center justify-end gap-1">
                    <button
                      onClick={() => openModal(user, 'give')}
                      className="p-1.5 hover:bg-green-500/20 text-green-400 rounded-lg transition"
                    >
                      <FiGift size={14} />
                    </button>
                    {user.has_subscription && (
                      <>
                        <button
                          onClick={() => openModal(user, 'extend')}
                          className="p-1.5 hover:bg-blue-500/20 text-blue-400 rounded-lg transition"
                        >
                          <FiClock size={14} />
                        </button>
                        <button
                          onClick={() => openModal(user, 'cancel')}
                          className="p-1.5 hover:bg-red-500/20 text-red-400 rounded-lg transition"
                        >
                          <FiTrash2 size={14} />
                        </button>
                      </>
                    )}
                    <button
                      onClick={() => openModal(user, 'notify')}
                      className="p-1.5 hover:bg-purple-500/20 text-purple-400 rounded-lg transition"
                    >
                      <FiMessageSquare size={14} />
                    </button>
                  </div>
                </div>
              )
            })
          )}
        </div>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex flex-col sm:flex-row items-center justify-between dark-card p-3 lg:p-4 gap-2">
          <p className="text-gray-400">
            Показано {page * limit + 1} - {Math.min((page + 1) * limit, totalUsers)} из {totalUsers}
          </p>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setPage(p => Math.max(0, p - 1))}
              disabled={page === 0}
              className="p-2 rounded-lg dark-input disabled:opacity-50"
            >
              <FiChevronLeft />
            </button>
            <span className="text-white px-3">
              {page + 1} / {totalPages}
            </span>
            <button
              onClick={() => setPage(p => Math.min(totalPages - 1, p + 1))}
              disabled={page >= totalPages - 1}
              className="p-2 rounded-lg dark-input disabled:opacity-50"
            >
              <FiChevronRight />
            </button>
          </div>
        </div>
      )}

      {/* Modal */}
      {showModal && selectedUser && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50 p-4" onClick={closeModal}>
          <div className="dark-card max-w-md w-full" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between p-6 border-b border-purple-500/20">
              <h2 className="text-xl font-bold text-white">
                {modalAction === 'give' && '🎁 Выдать подписку'}
                {modalAction === 'extend' && '⏰ Продлить подписку'}
                {modalAction === 'cancel' && '❌ Отменить подписку'}
                {modalAction === 'notify' && '💬 Отправить уведомление'}
              </h2>
              <button onClick={closeModal}>
                <FiX className="text-gray-400 hover:text-white" size={20} />
              </button>
            </div>

            <div className="p-6 space-y-4">
              {/* User Info */}
              <div className="p-4 rounded-xl bg-[#1a1a2e] flex items-center gap-3">
                <div className="w-12 h-12 rounded-full bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center">
                  <span className="text-white font-bold">
                    {(selectedUser.first_name || selectedUser.username || 'U')[0].toUpperCase()}
                  </span>
                </div>
                <div>
                  <p className="text-white font-medium">
                    {selectedUser.first_name || selectedUser.username || `User #${selectedUser.telegram_id}`}
                  </p>
                  <p className="text-xs text-gray-500">ID: {selectedUser.telegram_id}</p>
                </div>
              </div>

              {/* Action Content */}
              {modalAction === 'give' && (
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Выберите тариф
                  </label>
                  <select
                    value={selectedPlanId}
                    onChange={(e) => setSelectedPlanId(e.target.value)}
                    className="w-full dark-input rounded-xl px-4 py-3"
                  >
                    {plans?.map((plan: Plan) => (
                      <option key={plan.id} value={plan.id}>
                        {plan.name} ({plan.duration_days} дн.) - {plan.price} ₽
                      </option>
                    ))}
                  </select>
                  <p className="text-xs text-gray-500 mt-2">
                    {selectedUser.has_subscription 
                      ? 'У пользователя есть подписка - будет продлена' 
                      : 'Будет создана новая подписка'}
                  </p>
                </div>
              )}

              {modalAction === 'extend' && (
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Количество дней
                  </label>
                  <input
                    type="number"
                    value={extendDays}
                    onChange={(e) => setExtendDays(parseInt(e.target.value) || 0)}
                    className="w-full dark-input rounded-xl px-4 py-3"
                    min={1}
                    max={365}
                  />
                  <div className="flex gap-2 mt-2">
                    {[7, 14, 30, 90].map(d => (
                      <button
                        key={d}
                        type="button"
                        onClick={() => setExtendDays(d)}
                        className={`px-3 py-1 text-sm rounded-lg transition ${
                          extendDays === d 
                            ? 'bg-purple-500 text-white' 
                            : 'bg-purple-500/20 text-purple-300 hover:bg-purple-500/30'
                        }`}
                      >
                        {d} дн.
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {modalAction === 'cancel' && (
                <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/30">
                  <p className="text-red-400 flex items-center gap-2">
                    <FiAlertCircle />
                    Вы уверены, что хотите отменить подписку?
                  </p>
                  <p className="text-sm text-gray-400 mt-2">
                    Пользователь потеряет доступ к VPN. Это действие нельзя отменить.
                  </p>
                </div>
              )}

              {modalAction === 'notify' && (
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Текст уведомления
                  </label>
                  <textarea
                    value={notifyMessage}
                    onChange={(e) => setNotifyMessage(e.target.value)}
                    className="w-full dark-input rounded-xl px-4 py-3 h-32 resize-none"
                    placeholder="Введите сообщение для пользователя..."
                  />
                  <p className="text-xs text-gray-500 mt-2">
                    Сообщение будет отправлено в Telegram
                  </p>
                </div>
              )}
            </div>

            <div className="flex items-center justify-end gap-3 p-6 border-t border-purple-500/20">
              <button
                onClick={closeModal}
                className="px-4 py-2 text-gray-400 hover:text-white transition"
              >
                Отмена
              </button>
              <button
                onClick={handleSubmit}
                disabled={giveSubscription.isPending || extendSubscription.isPending || cancelSubscription.isPending || sendNotification.isPending}
                className={`px-6 py-2 rounded-xl font-medium transition ${
                  modalAction === 'cancel'
                    ? 'bg-red-500 hover:bg-red-600 text-white'
                    : 'bg-gradient-to-r from-purple-500 to-pink-500 hover:opacity-90 text-white'
                } disabled:opacity-50`}
              >
                {modalAction === 'give' && 'Выдать'}
                {modalAction === 'extend' && 'Продлить'}
                {modalAction === 'cancel' && 'Отменить подписку'}
                {modalAction === 'notify' && 'Отправить'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
