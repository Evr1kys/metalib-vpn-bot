'use client'

import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/lib/api'
import toast from 'react-hot-toast'
import { FiTrendingUp, FiUsers, FiDollarSign, FiAward, FiToggleLeft, FiToggleRight, FiPercent, FiSettings, FiSave } from 'react-icons/fi'

export default function ReferralsPage() {
  const queryClient = useQueryClient()
  const [showSettings, setShowSettings] = useState(false)
  const [bonusDays, setBonusDays] = useState(3)
  
  const { data: stats, isLoading } = useQuery({
    queryKey: ['referral-stats'],
    queryFn: () => apiClient.getReferralStats()
  })
  const { data: status, refetch: refetchStatus } = useQuery({
    queryKey: ['referral-status'],
    queryFn: () => apiClient.getReferralsStatus()
  })

  useEffect(() => {
    if (status?.bonus_days) {
      setBonusDays(status.bonus_days)
    }
  }, [status])

  const toggleMutation = useMutation({
    mutationFn: () => apiClient.toggleReferrals(),
    onSuccess: (result) => {
      toast.success(result.enabled ? 'Реферальная система включена' : 'Реферальная система отключена')
      refetchStatus()
    },
    onError: () => toast.error('Ошибка'),
  })

  const updateSettingsMutation = useMutation({
    mutationFn: (data: { enabled?: boolean; bonus_days?: number }) => 
      apiClient.put('/referrals/settings', data),
    onSuccess: () => {
      toast.success('Настройки сохранены')
      refetchStatus()
      queryClient.invalidateQueries({ queryKey: ['referral-stats'] })
    },
    onError: () => toast.error('Ошибка сохранения'),
  })

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-500"></div>
      </div>
    )
  }

  const topReferrers = stats?.top_referrers || []
  const isEnabled = status?.enabled !== false

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold gradient-text">Реферальная программа</h1>
          <p className="mt-2 text-gray-400">Статистика и управление рефералами</p>
        </div>
        <div className="flex space-x-2">
          <button
            onClick={() => setShowSettings(!showSettings)}
            className="px-4 py-3 rounded-xl bg-[#1a1a2e] border border-purple-500/20 text-gray-300 hover:text-white transition-colors flex items-center"
          >
            <FiSettings className="mr-2" />
            Настройки
          </button>
          <button
            onClick={() => toggleMutation.mutate()}
            disabled={toggleMutation.isLoading}
            className={`px-6 py-3 rounded-xl flex items-center font-medium transition-colors ${
              isEnabled
                ? 'bg-green-500/20 text-green-400 hover:bg-green-500/30'
                : 'bg-red-500/20 text-red-400 hover:bg-red-500/30'
            }`}
          >
            {isEnabled ? (
              <>
                <FiToggleRight className="mr-2 w-5 h-5" />
                Включена
              </>
            ) : (
              <>
                <FiToggleLeft className="mr-2 w-5 h-5" />
                Отключена
              </>
            )}
          </button>
        </div>
      </div>

      {/* Settings Panel */}
      {showSettings && (
        <div className="dark-card p-6">
          <h3 className="text-lg font-bold text-white mb-4">Настройки реферальной программы</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm text-gray-400 mb-2">Бонус дней за реферала</label>
              <div className="flex space-x-2">
                <input
                  type="number"
                  min="1"
                  max="30"
                  value={bonusDays}
                  onChange={(e) => setBonusDays(parseInt(e.target.value) || 3)}
                  className="flex-1 h-11 px-4 bg-[#1a1a2e] border border-purple-500/20 rounded-xl text-white focus:outline-none focus:ring-2 focus:ring-purple-500"
                />
                <button
                  onClick={() => updateSettingsMutation.mutate({ bonus_days: bonusDays })}
                  disabled={updateSettingsMutation.isLoading}
                  className="btn-gradient px-4 py-2 rounded-xl flex items-center"
                >
                  <FiSave className="mr-2" />
                  Сохранить
                </button>
              </div>
              <p className="text-xs text-gray-500 mt-1">Сколько дней добавляется к подписке реферера</p>
            </div>
          </div>
        </div>
      )}

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="stat-gradient-blue p-5 rounded-xl">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-gray-400 text-sm">Всего рефералов</p>
              <p className="text-2xl font-bold text-white">{stats?.total_referrals || 0}</p>
            </div>
            <FiUsers className="w-8 h-8 text-blue-400" />
          </div>
        </div>

        <div className="stat-gradient-green p-5 rounded-xl">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-gray-400 text-sm">Активировано</p>
              <p className="text-2xl font-bold text-white">{stats?.completed_referrals || 0}</p>
            </div>
            <FiAward className="w-8 h-8 text-green-400" />
          </div>
        </div>

        <div className="stat-gradient-orange p-5 rounded-xl">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-gray-400 text-sm">Начислено дней</p>
              <p className="text-2xl font-bold text-white">+{(stats?.total_bonus_days || 0).toLocaleString()}</p>
            </div>
            <FiAward className="w-8 h-8 text-orange-400" />
          </div>
        </div>

        <div className="stat-gradient-purple p-5 rounded-xl">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-gray-400 text-sm">Бонус</p>
              <p className="text-2xl font-bold text-white">+{status?.bonus_days || 3} дней</p>
            </div>
            <FiPercent className="w-8 h-8 text-purple-400" />
          </div>
        </div>
      </div>

      {/* Status Banner */}
      {!isEnabled && (
        <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/30 flex items-center">
          <FiToggleLeft className="w-6 h-6 text-red-400 mr-3" />
          <div>
            <p className="text-white font-medium">Реферальная система отключена</p>
            <p className="text-gray-400 text-sm">Пользователи не могут приглашать друзей и получать бонусы</p>
          </div>
        </div>
      )}

      {/* Top Referrers Table */}
      <div className="dark-card overflow-hidden">
        <div className="p-6 border-b border-purple-500/20">
          <h2 className="text-xl font-bold text-white flex items-center">
            <FiTrendingUp className="mr-2 text-purple-400" />
            Топ рефереров
          </h2>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-purple-500/20">
                <th className="text-left p-4 text-gray-400 font-medium">#</th>
                <th className="text-left p-4 text-gray-400 font-medium">Пользователь</th>
                <th className="text-left p-4 text-gray-400 font-medium">Рефералов</th>
                <th className="text-left p-4 text-gray-400 font-medium">Оплатили</th>
                <th className="text-left p-4 text-gray-400 font-medium">Бонус дней</th>
                <th className="text-left p-4 text-gray-400 font-medium">Конверсия</th>
              </tr>
            </thead>
            <tbody>
              {topReferrers.length === 0 ? (
                <tr>
                  <td colSpan={6} className="p-8 text-center text-gray-500">
                    <FiUsers className="w-12 h-12 mx-auto mb-3 opacity-50" />
                    <p>Нет данных о рефералах</p>
                  </td>
                </tr>
              ) : (
                topReferrers.map((referrer: any, index: number) => (
                  <tr key={referrer.user_id} className="border-b border-purple-500/10 hover:bg-purple-500/5 transition-colors">
                    <td className="p-4">
                      <span className={`w-8 h-8 rounded-full flex items-center justify-center font-bold text-sm ${
                        index === 0 ? 'bg-yellow-500/20 text-yellow-400' :
                        index === 1 ? 'bg-gray-400/20 text-gray-300' :
                        index === 2 ? 'bg-orange-500/20 text-orange-400' :
                        'bg-purple-500/10 text-gray-400'
                      }`}>
                        {index + 1}
                      </span>
                    </td>
                    <td className="p-4">
                      <div className="flex items-center space-x-3">
                        <div className="w-10 h-10 rounded-full bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center">
                          <span className="text-white font-bold">
                            {(referrer.first_name || referrer.username || 'U')[0].toUpperCase()}
                          </span>
                        </div>
                        <div>
                          <p className="text-white font-medium">{referrer.first_name || referrer.username || 'Пользователь'}</p>
                          <p className="text-xs text-gray-500">ID: {referrer.telegram_id}</p>
                        </div>
                      </div>
                    </td>
                    <td className="p-4 text-white font-medium">{referrer.referrals_count}</td>
                    <td className="p-4 text-green-400">{referrer.completed_referrals}</td>
                    <td className="p-4 text-white">+{referrer.total_bonus_days || 0}</td>
                    <td className="p-4">
                      <span className={`px-2 py-1 rounded-full text-xs ${
                        referrer.conversion_rate > 50 
                          ? 'bg-green-500/20 text-green-400' 
                          : referrer.conversion_rate > 20 
                          ? 'bg-yellow-500/20 text-yellow-400'
                          : 'bg-gray-500/20 text-gray-400'
                      }`}>
                        {Math.round(referrer.conversion_rate)}%
                      </span>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
