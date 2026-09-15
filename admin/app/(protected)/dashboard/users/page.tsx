'use client'

import { useState, useEffect } from 'react'
import { apiClient } from '@/lib/api'
import toast from 'react-hot-toast'
import { 
  FiSearch, FiDownload, FiUserCheck, FiUserX, FiEdit2, FiTrash2, FiClock, 
  FiCalendar, FiGift, FiBell, FiX, FiUser, FiMail, FiShield, FiZap,
  FiChevronLeft, FiChevronRight, FiMoreVertical, FiRefreshCw
} from 'react-icons/fi'

interface User {
  id: string
  telegram_id: number
  username?: string
  first_name: string
  last_name?: string
  is_banned: boolean
  is_blocked: boolean
  created_at: string
  has_subscription: boolean
  subscription?: {
    id: string
    status: string
    expires_at: string
    plan_id: string
  }
  balance?: number
}

interface Plan {
  id: string
  name: string
  duration_days: number
}

export default function UsersPage() {
  const [users, setUsers] = useState<User[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(0)
  const [totalUsers, setTotalUsers] = useState(0)
  const [selectedUser, setSelectedUser] = useState<User | null>(null)
  const [showUserModal, setShowUserModal] = useState(false)
  const [showSubscriptionModal, setShowSubscriptionModal] = useState(false)
  const [showNotificationModal, setShowNotificationModal] = useState(false)
  const [plans, setPlans] = useState<Plan[]>([])
  const [selectedPlan, setSelectedPlan] = useState('')
  const [notificationText, setNotificationText] = useState('')
  const [actionLoading, setActionLoading] = useState(false)
  const limit = 20

  useEffect(() => {
    loadUsers()
    loadPlans()
  }, [page])

  const loadUsers = async () => {
    try {
      setLoading(true)
      const data = await apiClient.getUsers({ skip: page * limit, limit, search })
      // API returns {users: [...], total: N} or just array
      const usersList = Array.isArray(data) ? data : (data?.users || [])
      setUsers(usersList)
      setTotalUsers(data?.total || usersList.length)
    } catch (error) {
      console.error('Error loading users')
    } finally {
      setLoading(false)
    }
  }

  const loadPlans = async () => {
    try {
      const data = await apiClient.get('/plans/admin/all')
      setPlans(data || [])
    } catch (error) {
      console.error('Error loading plans')
    }
  }

  const handleSearch = () => {
    setPage(0)
    loadUsers()
  }

  const handleBanUser = async (user: User) => {
    try {
      if (user.is_banned) {
        await apiClient.unbanUser(user.telegram_id)
        toast.success('✓ Пользователь разблокирован')
      } else {
        await apiClient.banUser(user.telegram_id)
        toast.success('✓ Пользователь заблокирован')
      }
      loadUsers()
    } catch (error) {
      toast.error('Ошибка при изменении статуса')
    }
  }

  const handleViewUser = (user: User) => {
    setSelectedUser(user)
    setShowUserModal(true)
  }

  const handleGiveSubscription = async () => {
    if (!selectedUser || !selectedPlan) {
      toast.error('Выберите тариф')
      return
    }

    try {
      setActionLoading(true)
      await apiClient.post(`/admin/users/${selectedUser.id}/subscription`, {
        plan_id: selectedPlan
      })
      toast.success('✓ Подписка выдана')
      setShowSubscriptionModal(false)
      setSelectedPlan('')
      loadUsers()
    } catch (error) {
      toast.error('Ошибка выдачи подписки')
    } finally {
      setActionLoading(false)
    }
  }

  const handleExtendSubscription = async (days: number) => {
    if (!selectedUser) return

    try {
      setActionLoading(true)
      await apiClient.post(`/admin/users/${selectedUser.id}/extend`, { days })
      toast.success(`✓ Подписка продлена на ${days} дней`)
      setShowUserModal(false)
      loadUsers()
    } catch (error) {
      toast.error('Ошибка продления')
    } finally {
      setActionLoading(false)
    }
  }

  const handleCancelSubscription = async () => {
    if (!selectedUser || !confirm('Отменить подписку?')) return

    try {
      setActionLoading(true)
      await apiClient.post(`/admin/users/${selectedUser.id}/cancel-subscription`)
      toast.success('✓ Подписка отменена')
      setShowUserModal(false)
      loadUsers()
    } catch (error) {
      toast.error('Ошибка отмены')
    } finally {
      setActionLoading(false)
    }
  }

  const handleSendNotification = async () => {
    if (!selectedUser || !notificationText.trim()) {
      toast.error('Введите текст уведомления')
      return
    }

    try {
      setActionLoading(true)
      await apiClient.post('/admin/notifications/send', {
        user_id: selectedUser.telegram_id,
        message: notificationText
      })
      toast.success('✓ Уведомление отправлено')
      setShowNotificationModal(false)
      setNotificationText('')
    } catch (error) {
      toast.error('Ошибка отправки')
    } finally {
      setActionLoading(false)
    }
  }

  const handleExport = async () => {
    try {
      const blob = await apiClient.exportUsersCSV()
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `users_${new Date().toISOString().split('T')[0]}.csv`
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
      toast.success('✓ Экспорт завершён')
    } catch (error) {
      toast.error('Ошибка экспорта')
    }
  }

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('ru-RU', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric'
    })
  }

  const bannedUsers = users.filter(u => u.is_banned).length
  const activeSubscriptions = users.filter(u => u.has_subscription).length

  if (loading && users.length === 0) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-500"></div>
      </div>
    )
  }

  return (
    <div className="space-y-4 lg:space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h1 className="text-xl lg:text-3xl font-bold text-white">Пользователи</h1>
          <p className="text-xs lg:text-sm text-purple-300/70 mt-1">Управление пользователями</p>
        </div>
        <div className="flex items-center gap-2 lg:gap-3">
          <button
            onClick={loadUsers}
            className="flex items-center gap-2 px-3 lg:px-4 py-2 lg:py-2.5 bg-gray-700 text-gray-300 rounded-xl hover:bg-gray-600 transition"
          >
            <FiRefreshCw size={16} />
          </button>
          <button
            onClick={handleExport}
            className="flex items-center gap-2 px-3 lg:px-4 py-2 lg:py-2.5 bg-green-500/20 text-green-400 border border-green-500/30 rounded-xl hover:bg-green-500/30 transition text-sm"
          >
            <FiDownload size={16} />
            <span className="hidden sm:inline">Экспорт</span>
          </button>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 lg:gap-6">
        <div className="dark-card p-3 lg:p-6 card-hover stat-gradient-blue">
          <div className="flex items-center gap-2 lg:gap-4">
            <div className="p-2 lg:p-3 bg-blue-500/20 rounded-xl">
              <FiUser className="text-blue-400 w-5 h-5 lg:w-6 lg:h-6" />
            </div>
            <div>
              <p className="text-[10px] lg:text-sm text-gray-400">Всего</p>
              <p className="text-lg lg:text-2xl font-bold text-white">{users.length}</p>
            </div>
          </div>
        </div>

        <div className="dark-card p-3 lg:p-6 card-hover stat-gradient-green">
          <div className="flex items-center gap-2 lg:gap-4">
            <div className="p-2 lg:p-3 bg-green-500/20 rounded-xl">
              <FiUserCheck className="text-green-400 w-5 h-5 lg:w-6 lg:h-6" />
            </div>
            <div>
              <p className="text-[10px] lg:text-sm text-gray-400">С подпиской</p>
              <p className="text-lg lg:text-2xl font-bold text-white">{activeSubscriptions}</p>
            </div>
          </div>
        </div>

        <div className="dark-card p-3 lg:p-6 card-hover stat-gradient-orange">
          <div className="flex items-center gap-2 lg:gap-4">
            <div className="p-2 lg:p-3 bg-red-500/20 rounded-xl">
              <FiUserX className="text-red-400 w-5 h-5 lg:w-6 lg:h-6" />
            </div>
            <div>
              <p className="text-[10px] lg:text-sm text-gray-400">Забанено</p>
              <p className="text-lg lg:text-2xl font-bold text-white">{bannedUsers}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Search */}
      <div className="dark-card p-3 lg:p-4">
        <div className="flex gap-2 lg:gap-4">
          <div className="flex-1 relative">
            <FiSearch className="absolute left-3 lg:left-4 top-1/2 -translate-y-1/2 text-gray-400" size={18} />
            <input
              type="text"
              placeholder="Поиск..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
              className="w-full dark-input rounded-xl pl-10 lg:pl-12 pr-3 lg:pr-4 py-2.5 lg:py-3 text-sm"
            />
          </div>
          <button
            onClick={handleSearch}
            className="px-4 lg:px-6 py-2.5 lg:py-3 btn-gradient rounded-xl font-medium text-sm"
          >
            Найти
          </button>
        </div>
      </div>

      {/* Users - Mobile Cards / Desktop Table */}
      <div className="dark-card overflow-hidden">
        {/* Desktop Table */}
        <div className="hidden lg:block overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-purple-500/20 bg-purple-500/5">
                <th className="px-6 py-4 text-left text-xs font-semibold text-purple-300 uppercase">Пользователь</th>
                <th className="px-6 py-4 text-left text-xs font-semibold text-purple-300 uppercase">Telegram ID</th>
                <th className="px-6 py-4 text-left text-xs font-semibold text-purple-300 uppercase">Подписка</th>
                <th className="px-6 py-4 text-left text-xs font-semibold text-purple-300 uppercase">Статус</th>
                <th className="px-6 py-4 text-left text-xs font-semibold text-purple-300 uppercase">Регистрация</th>
                <th className="px-6 py-4 text-center text-xs font-semibold text-purple-300 uppercase">Действия</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-purple-500/10">
              {users.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-6 py-12 text-center">
                    <div className="flex flex-col items-center gap-3">
                      <FiUser size={48} className="text-gray-600" />
                      <p className="text-gray-500">Пользователи не найдены</p>
                    </div>
                  </td>
                </tr>
              ) : (
                users.map((user) => (
                  <tr key={user.id} className="hover:bg-purple-500/5 transition-colors">
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-full bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center text-white font-bold">
                          {user.first_name?.charAt(0) || 'U'}
                        </div>
                        <div>
                          <p className="font-medium text-white">
                            {user.first_name} {user.last_name || ''}
                          </p>
                          {user.username && (
                            <p className="text-sm text-gray-400">@{user.username}</p>
                          )}
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <span className="font-mono text-gray-300">{user.telegram_id}</span>
                    </td>
                    <td className="px-6 py-4">
                      {user.has_subscription && user.subscription ? (
                        <div>
                          <span className="text-green-400 font-medium">Активна</span>
                          <p className="text-xs text-gray-500">
                            до {formatDate(user.subscription.expires_at)}
                          </p>
                        </div>
                      ) : (
                        <span className="text-gray-500">Нет</span>
                      )}
                    </td>
                    <td className="px-6 py-4">
                      {user.is_banned ? (
                        <span className="inline-flex items-center px-3 py-1 bg-red-500/20 text-red-400 rounded-full text-xs font-medium">
                          Заблокирован
                        </span>
                      ) : (
                        <span className="inline-flex items-center px-3 py-1 bg-green-500/20 text-green-400 rounded-full text-xs font-medium">
                          Активен
                        </span>
                      )}
                    </td>
                    <td className="px-6 py-4">
                      <span className="text-gray-400">{formatDate(user.created_at)}</span>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center justify-center gap-1">
                        <button
                          onClick={() => handleViewUser(user)}
                          className="p-2 hover:bg-purple-500/20 text-purple-400 rounded-lg transition"
                          title="Подробнее"
                        >
                          <FiEdit2 size={18} />
                        </button>
                        <button
                          onClick={() => {
                            setSelectedUser(user)
                            setShowSubscriptionModal(true)
                          }}
                          className="p-2 hover:bg-green-500/20 text-green-400 rounded-lg transition"
                          title="Выдать подписку"
                        >
                          <FiGift size={18} />
                        </button>
                        <button
                          onClick={() => {
                            setSelectedUser(user)
                            setShowNotificationModal(true)
                          }}
                          className="p-2 hover:bg-blue-500/20 text-blue-400 rounded-lg transition"
                          title="Отправить уведомление"
                        >
                          <FiBell size={18} />
                        </button>
                        <button
                          onClick={() => handleBanUser(user)}
                          className={`p-2 rounded-lg transition ${
                            user.is_banned 
                              ? 'hover:bg-green-500/20 text-green-400' 
                              : 'hover:bg-red-500/20 text-red-400'
                          }`}
                          title={user.is_banned ? 'Разблокировать' : 'Заблокировать'}
                        >
                          {user.is_banned ? <FiUserCheck size={18} /> : <FiUserX size={18} />}
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Mobile Cards */}
        <div className="lg:hidden divide-y divide-purple-500/10">
          {users.length === 0 ? (
            <div className="p-8 text-center">
              <FiUser size={40} className="text-gray-600 mx-auto mb-2" />
              <p className="text-gray-500 text-sm">Пользователи не найдены</p>
            </div>
          ) : (
            users.map((user) => (
              <div key={user.id} className="p-3 hover:bg-purple-500/5">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <div className="w-8 h-8 rounded-full bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center text-white font-bold text-sm">
                      {user.first_name?.charAt(0) || 'U'}
                    </div>
                    <div>
                      <p className="text-sm font-medium text-white truncate max-w-[150px]">
                        {user.first_name} {user.last_name || ''}
                      </p>
                      {user.username && (
                        <p className="text-[10px] text-gray-400">@{user.username}</p>
                      )}
                    </div>
                  </div>
                  <span className={`text-[10px] px-2 py-0.5 rounded-full ${
                    user.is_banned 
                      ? 'bg-red-500/20 text-red-400' 
                      : 'bg-green-500/20 text-green-400'
                  }`}>
                    {user.is_banned ? 'Бан' : 'Актив'}
                  </span>
                </div>
                <div className="flex items-center justify-between text-[10px] text-gray-400 mb-2">
                  <span>ID: {user.telegram_id}</span>
                  <span>{formatDate(user.created_at)}</span>
                </div>
                <div className="flex items-center justify-between">
                  <div>
                    {user.has_subscription && user.subscription ? (
                      <span className="text-xs text-green-400">до {formatDate(user.subscription.expires_at)}</span>
                    ) : (
                      <span className="text-xs text-gray-500">Нет подписки</span>
                    )}
                  </div>
                  <div className="flex items-center gap-1">
                    <button
                      onClick={() => handleViewUser(user)}
                      className="p-1.5 hover:bg-purple-500/20 text-purple-400 rounded-lg transition"
                    >
                      <FiEdit2 size={14} />
                    </button>
                    <button
                      onClick={() => {
                        setSelectedUser(user)
                        setShowSubscriptionModal(true)
                      }}
                      className="p-1.5 hover:bg-green-500/20 text-green-400 rounded-lg transition"
                    >
                      <FiGift size={14} />
                    </button>
                    <button
                      onClick={() => handleBanUser(user)}
                      className={`p-1.5 rounded-lg transition ${
                        user.is_banned 
                          ? 'hover:bg-green-500/20 text-green-400' 
                          : 'hover:bg-red-500/20 text-red-400'
                      }`}
                    >
                      {user.is_banned ? <FiUserCheck size={14} /> : <FiUserX size={14} />}
                    </button>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>

        {/* Pagination */}
        {users.length >= limit && (
          <div className="px-3 lg:px-6 py-3 lg:py-4 border-t border-purple-500/20 flex items-center justify-between">
            <button
              onClick={() => setPage(Math.max(0, page - 1))}
              disabled={page === 0}
              className="flex items-center gap-1 lg:gap-2 px-2 lg:px-4 py-1.5 lg:py-2 bg-gray-700 text-gray-300 rounded-lg hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed transition text-sm"
            >
              <FiChevronLeft size={16} />
              <span className="hidden sm:inline">Назад</span>
            </button>
            <span className="text-xs lg:text-sm text-gray-400">Стр. {page + 1}</span>
            <button
              onClick={() => setPage(page + 1)}
              className="flex items-center gap-1 lg:gap-2 px-2 lg:px-4 py-1.5 lg:py-2 bg-gray-700 text-gray-300 rounded-lg hover:bg-gray-600 transition text-sm"
            >
              Вперёд
              <FiChevronRight size={18} />
            </button>
          </div>
        )}
      </div>

      {/* User Details Modal */}
      {showUserModal && selectedUser && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-end sm:items-center justify-center z-50 p-0 sm:p-4" onClick={() => setShowUserModal(false)}>
          <div className="dark-card w-full sm:max-w-lg sm:rounded-xl rounded-t-2xl rounded-b-none sm:rounded-b-xl max-h-[85vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between p-4 lg:p-6 border-b border-purple-500/20 sticky top-0 bg-[#0f0f1a] z-10">
              <h3 className="text-base lg:text-xl font-bold text-white">Пользователь</h3>
              <button onClick={() => setShowUserModal(false)} className="p-2 hover:bg-purple-500/20 rounded-lg">
                <FiX size={20} className="text-gray-400" />
              </button>
            </div>
            
            <div className="p-4 lg:p-6 space-y-4">
              <div className="flex items-center gap-3 lg:gap-4">
                <div className="w-12 h-12 lg:w-16 lg:h-16 rounded-full bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center text-white text-xl lg:text-2xl font-bold">
                  {selectedUser.first_name?.charAt(0) || 'U'}
                </div>
                <div>
                  <h4 className="text-base lg:text-xl font-bold text-white">
                    {selectedUser.first_name} {selectedUser.last_name || ''}
                  </h4>
                  {selectedUser.username && (
                    <p className="text-sm text-purple-400">@{selectedUser.username}</p>
                  )}
                  <p className="text-xs lg:text-sm text-gray-500">ID: {selectedUser.telegram_id}</p>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3 lg:gap-4 pt-4">
                <div className="bg-purple-500/10 rounded-xl p-3 lg:p-4">
                  <p className="text-xs lg:text-sm text-gray-400">Статус</p>
                  <p className={`text-sm lg:text-base font-semibold ${selectedUser.is_banned ? 'text-red-400' : 'text-green-400'}`}>
                    {selectedUser.is_banned ? 'Заблокирован' : 'Активен'}
                  </p>
                </div>
                <div className="bg-purple-500/10 rounded-xl p-3 lg:p-4">
                  <p className="text-xs lg:text-sm text-gray-400">Регистрация</p>
                  <p className="text-sm lg:text-base font-semibold text-white">{formatDate(selectedUser.created_at)}</p>
                </div>
              </div>

              {selectedUser.has_subscription && selectedUser.subscription && (
                <div className="bg-green-500/10 border border-green-500/20 rounded-xl p-3 lg:p-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-xs lg:text-sm text-gray-400">Подписка</p>
                      <p className="text-sm lg:text-base font-semibold text-green-400">Активна</p>
                      <p className="text-[10px] lg:text-xs text-gray-500">до {formatDate(selectedUser.subscription.expires_at)}</p>
                    </div>
                    <button
                      onClick={handleCancelSubscription}
                      disabled={actionLoading}
                      className="px-2 lg:px-3 py-1 lg:py-1.5 bg-red-500/20 text-red-400 rounded-lg text-xs lg:text-sm hover:bg-red-500/30 transition"
                    >
                      Отменить
                    </button>
                  </div>
                </div>
              )}

              <div className="pt-4 border-t border-purple-500/20">
                <p className="text-xs lg:text-sm text-gray-400 mb-3">Быстрые действия</p>
                <div className="grid grid-cols-2 gap-2 lg:gap-3">
                  <button
                    onClick={() => handleExtendSubscription(7)}
                    disabled={actionLoading}
                    className="px-3 lg:px-4 py-2 lg:py-2.5 bg-blue-500/20 text-blue-400 rounded-xl hover:bg-blue-500/30 transition text-xs lg:text-sm"
                  >
                    +7 дней
                  </button>
                  <button
                    onClick={() => handleExtendSubscription(30)}
                    disabled={actionLoading}
                    className="px-3 lg:px-4 py-2 lg:py-2.5 bg-blue-500/20 text-blue-400 rounded-xl hover:bg-blue-500/30 transition text-xs lg:text-sm"
                  >
                    +30 дней
                  </button>
                  <button
                    onClick={() => {
                      setShowUserModal(false)
                      setShowSubscriptionModal(true)
                    }}
                    className="px-3 lg:px-4 py-2 lg:py-2.5 bg-green-500/20 text-green-400 rounded-xl hover:bg-green-500/30 transition text-xs lg:text-sm flex items-center justify-center gap-1 lg:gap-2"
                  >
                    <FiGift size={14} />
                    Тариф
                  </button>
                  <button
                    onClick={() => {
                      setShowUserModal(false)
                      setShowNotificationModal(true)
                    }}
                    className="px-3 lg:px-4 py-2 lg:py-2.5 bg-purple-500/20 text-purple-400 rounded-xl hover:bg-purple-500/30 transition text-xs lg:text-sm flex items-center justify-center gap-1 lg:gap-2"
                  >
                    <FiBell size={14} />
                    Сообщение
                  </button>
                </div>
              </div>

              <div className="flex gap-3 pt-4">
                <button
                  onClick={() => handleBanUser(selectedUser)}
                  className={`flex-1 px-4 py-2.5 lg:py-3 rounded-xl font-medium transition text-sm ${
                    selectedUser.is_banned
                      ? 'bg-green-500/20 text-green-400 hover:bg-green-500/30'
                      : 'bg-red-500/20 text-red-400 hover:bg-red-500/30'
                  }`}
                >
                  {selectedUser.is_banned ? 'Разблокировать' : 'Заблокировать'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Give Subscription Modal */}
      {showSubscriptionModal && selectedUser && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-end sm:items-center justify-center z-50 p-0 sm:p-4" onClick={() => setShowSubscriptionModal(false)}>
          <div className="dark-card w-full sm:max-w-md sm:rounded-xl rounded-t-2xl rounded-b-none sm:rounded-b-xl" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between p-4 lg:p-6 border-b border-purple-500/20">
              <h3 className="text-base lg:text-xl font-bold text-white">Выдать подписку</h3>
              <button onClick={() => setShowSubscriptionModal(false)} className="p-2 hover:bg-purple-500/20 rounded-lg">
                <FiX size={20} className="text-gray-400" />
              </button>
            </div>
            
            <div className="p-4 lg:p-6 space-y-4">
              <p className="text-sm text-gray-400">
                Выдать подписку: <span className="text-white font-medium">{selectedUser.first_name}</span>
              </p>
              
              <div>
                <label className="block text-xs lg:text-sm font-medium text-gray-300 mb-2">Тариф</label>
                <select
                  value={selectedPlan}
                  onChange={(e) => setSelectedPlan(e.target.value)}
                  className="w-full dark-input rounded-xl px-4 py-2.5 lg:py-3 text-sm"
                >
                  <option value="">-- Выберите --</option>
                  {plans.map(plan => (
                    <option key={plan.id} value={plan.id}>
                      {plan.name} ({plan.duration_days} дней)
                    </option>
                  ))}
                </select>
              </div>

              <div className="flex gap-3 pt-4">
                <button
                  onClick={() => setShowSubscriptionModal(false)}
                  className="flex-1 px-4 py-2.5 lg:py-3 bg-gray-700 text-white rounded-xl hover:bg-gray-600 transition text-sm"
                >
                  Отмена
                </button>
                <button
                  onClick={handleGiveSubscription}
                  disabled={!selectedPlan || actionLoading}
                  className="flex-1 px-4 py-2.5 lg:py-3 btn-gradient rounded-xl font-medium disabled:opacity-50 text-sm"
                >
                  {actionLoading ? 'Выдаём...' : 'Выдать'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Send Notification Modal */}
      {showNotificationModal && selectedUser && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-end sm:items-center justify-center z-50 p-0 sm:p-4" onClick={() => setShowNotificationModal(false)}>
          <div className="dark-card w-full sm:max-w-md sm:rounded-xl rounded-t-2xl rounded-b-none sm:rounded-b-xl" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between p-4 lg:p-6 border-b border-purple-500/20">
              <h3 className="text-base lg:text-xl font-bold text-white">Уведомление</h3>
              <button onClick={() => setShowNotificationModal(false)} className="p-2 hover:bg-purple-500/20 rounded-lg">
                <FiX size={20} className="text-gray-400" />
              </button>
            </div>
            
            <div className="p-4 lg:p-6 space-y-4">
              <p className="text-sm text-gray-400">
                Отправить: <span className="text-white font-medium">{selectedUser.first_name}</span>
              </p>
              
              <div>
                <label className="block text-xs lg:text-sm font-medium text-gray-300 mb-2">Текст</label>
                <textarea
                  value={notificationText}
                  onChange={(e) => setNotificationText(e.target.value)}
                  className="w-full dark-input rounded-xl px-4 py-2.5 lg:py-3 resize-none text-sm"
                  rows={4}
                  placeholder="Введите текст..."
                />
              </div>

              <div className="flex gap-3 pt-4">
                <button
                  onClick={() => setShowNotificationModal(false)}
                  className="flex-1 px-4 py-2.5 lg:py-3 bg-gray-700 text-white rounded-xl hover:bg-gray-600 transition text-sm"
                >
                  Отмена
                </button>
                <button
                  onClick={handleSendNotification}
                  disabled={!notificationText.trim() || actionLoading}
                  className="flex-1 px-4 py-2.5 lg:py-3 btn-gradient rounded-xl font-medium disabled:opacity-50 text-sm"
                >
                  {actionLoading ? 'Отправка...' : 'Отправить'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
