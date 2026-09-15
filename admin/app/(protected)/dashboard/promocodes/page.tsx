'use client'

import { useState, useEffect } from 'react'
import { apiClient } from '@/lib/api'
import toast from 'react-hot-toast'
import { FiGift, FiPlus, FiTrash2, FiCopy, FiEdit2, FiX, FiPercent, FiDollarSign, FiCheck, FiClock, FiPackage } from 'react-icons/fi'

interface Plan {
  id: string
  name: string
  price: number
}

interface PromoCode {
  id: string
  code: string
  discount_type: 'percentage' | 'fixed' | 'free_plan'
  discount_value: number
  plan_ids: string[]
  max_uses: number | null
  max_uses_per_user: number
  used_count: number
  expires_at: string | null
  is_active: boolean
  is_valid: boolean
  created_at: string
}

export default function PromoCodesPage() {
  const [promoCodes, setPromoCodes] = useState<PromoCode[]>([])
  const [plans, setPlans] = useState<Plan[]>([])
  const [loading, setLoading] = useState(true)
  const [showModal, setShowModal] = useState(false)
  const [editingCode, setEditingCode] = useState<PromoCode | null>(null)
  const [formData, setFormData] = useState({
    code: '',
    discount_type: 'percentage' as 'percentage' | 'fixed' | 'free_plan',
    discount_value: 0,
    plan_id: '',
    max_uses: 100,
    max_uses_per_user: 1,
    expires_at: '',
  })

  useEffect(() => {
    loadPromoCodes()
    loadPlans()
  }, [])

  const loadPlans = async () => {
    try {
      const response = await apiClient.getPlans()
      setPlans(response || [])
    } catch (error) {
      console.error('Ошибка загрузки планов')
    }
  }

  const loadPromoCodes = async () => {
    try {
      setLoading(true)
      const response = await apiClient.get('/admin/promocodes')
      setPromoCodes(response || [])
    } catch (error) {
      console.error('Ошибка загрузки промокодов')
    } finally {
      setLoading(false)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!formData.code.trim()) {
      toast.error('Введите код промокода')
      return
    }

    if (formData.discount_type !== 'free_plan' && formData.discount_value <= 0) {
      toast.error('Скидка должна быть больше 0')
      return
    }

    if (formData.discount_type === 'percentage' && formData.discount_value > 100) {
      toast.error('Процент скидки не может быть больше 100')
      return
    }

    if (formData.discount_type === 'free_plan' && !formData.plan_id) {
      toast.error('Выберите тариф для бесплатной выдачи')
      return
    }

    try {
      const payload: any = {
        code: formData.code.toUpperCase(),
        discount_type: formData.discount_type,
        discount_value: formData.discount_type === 'free_plan' ? 100 : formData.discount_value,
        max_uses: formData.max_uses || null,
        max_uses_per_user: formData.max_uses_per_user,
        expires_at: formData.expires_at || null,
        is_active: true
      }

      // Backend expects plan_id, not plan_ids
      if (formData.plan_id) {
        payload.plan_id = formData.plan_id
      }

      if (editingCode) {
        await apiClient.put(`/admin/promocodes/${editingCode.id}`, payload)
        toast.success('✓ Промокод обновлен')
      } else {
        await apiClient.post('/admin/promocodes', payload)
        toast.success('✓ Промокод создан')
      }

      setShowModal(false)
      setEditingCode(null)
      resetForm()
      loadPromoCodes()
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Ошибка сохранения')
    }
  }

  const handleDelete = async (id: string) => {
    if (!confirm('Удалить этот промокод?')) return

    try {
      await apiClient.delete(`/admin/promocodes/${id}`)
      toast.success('✓ Промокод удален')
      loadPromoCodes()
    } catch (error) {
      toast.error('Ошибка удаления')
    }
  }

  const handleToggle = async (code: PromoCode) => {
    try {
      await apiClient.put(`/admin/promocodes/${code.id}`, { is_active: !code.is_active })
      toast.success(code.is_active ? '✓ Промокод отключен' : '✓ Промокод активирован')
      loadPromoCodes()
    } catch (error) {
      toast.error('Ошибка изменения статуса')
    }
  }

  const handleEdit = (code: PromoCode) => {
    setEditingCode(code)
    setFormData({
      code: code.code,
      discount_type: code.discount_type,
      discount_value: code.discount_value,
      plan_id: code.plan_ids?.[0] || '',
      max_uses: code.max_uses || 100,
      max_uses_per_user: code.max_uses_per_user,
      expires_at: code.expires_at ? code.expires_at.split('T')[0] : '',
    })
    setShowModal(true)
  }

  const handleCopy = (code: string) => {
    navigator.clipboard.writeText(code)
    toast.success('✓ Код скопирован')
  }

  const generateCode = () => {
    const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
    let code = ''
    for (let i = 0; i < 8; i++) {
      code += chars.charAt(Math.floor(Math.random() * chars.length))
    }
    setFormData({ ...formData, code })
  }

  const resetForm = () => {
    setFormData({
      code: '',
      discount_type: 'percentage',
      discount_value: 0,
      plan_id: '',
      max_uses: 100,
      max_uses_per_user: 1,
      expires_at: '',
    })
  }

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr)
    return date.toLocaleDateString('ru-RU')
  }

  const getDiscountTypeLabel = (type: string) => {
    switch (type) {
      case 'percentage': return 'Процент'
      case 'fixed': return 'Фикс. сумма'
      case 'free_plan': return 'Бесплатный тариф'
      default: return type
    }
  }

  const getDiscountDisplay = (code: PromoCode) => {
    switch (code.discount_type) {
      case 'percentage': return `${code.discount_value}%`
      case 'fixed': return `${code.discount_value} ₽`
      case 'free_plan': 
        const plan = plans.find(p => code.plan_ids?.includes(p.id))
        return plan ? `Бесплатно: ${plan.name}` : 'Бесплатный тариф'
      default: return `${code.discount_value}`
    }
  }

  const totalUsed = promoCodes.reduce((sum, p) => sum + p.used_count, 0)
  const activePromoCodes = promoCodes.filter(p => p.is_active && p.is_valid).length

  if (loading) {
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
          <h1 className="text-3xl font-bold text-white">Промокоды</h1>
          <p className="text-purple-300/70 mt-1">Управление промокодами и скидками</p>
        </div>
        <button
          onClick={() => {
            setEditingCode(null)
            resetForm()
            setShowModal(true)
          }}
          className="flex items-center gap-2 px-5 py-2.5 btn-gradient rounded-xl font-medium shadow-lg shadow-purple-500/25 hover:shadow-purple-500/40 transition-all"
        >
          <FiPlus size={18} />
          Создать промокод
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="dark-card p-6 card-hover stat-gradient-purple">
          <div className="flex items-center gap-4">
            <div className="p-3 bg-purple-500/20 rounded-xl">
              <FiGift className="text-purple-400" size={24} />
            </div>
            <div>
              <p className="text-sm text-gray-400">Всего промокодов</p>
              <p className="text-2xl font-bold text-white">{promoCodes.length}</p>
            </div>
          </div>
        </div>

        <div className="dark-card p-6 card-hover stat-gradient-green">
          <div className="flex items-center gap-4">
            <div className="p-3 bg-green-500/20 rounded-xl">
              <FiCheck className="text-green-400" size={24} />
            </div>
            <div>
              <p className="text-sm text-gray-400">Активных</p>
              <p className="text-2xl font-bold text-white">{activePromoCodes}</p>
            </div>
          </div>
        </div>

        <div className="dark-card p-6 card-hover stat-gradient-blue">
          <div className="flex items-center gap-4">
            <div className="p-3 bg-blue-500/20 rounded-xl">
              <FiClock className="text-blue-400" size={24} />
            </div>
            <div>
              <p className="text-sm text-gray-400">Использований</p>
              <p className="text-2xl font-bold text-white">{totalUsed}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Promo Codes Table */}
      <div className="dark-card overflow-hidden">
        <div className="px-6 py-4 border-b border-purple-500/20">
          <h2 className="text-lg font-semibold text-white">Список промокодов</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-purple-500/20 bg-purple-500/5">
                <th className="px-6 py-4 text-left text-xs font-semibold text-purple-300 uppercase">Код</th>
                <th className="px-6 py-4 text-left text-xs font-semibold text-purple-300 uppercase">Скидка</th>
                <th className="px-6 py-4 text-left text-xs font-semibold text-purple-300 uppercase">Использовано</th>
                <th className="px-6 py-4 text-left text-xs font-semibold text-purple-300 uppercase">Срок действия</th>
                <th className="px-6 py-4 text-left text-xs font-semibold text-purple-300 uppercase">Статус</th>
                <th className="px-6 py-4 text-center text-xs font-semibold text-purple-300 uppercase">Действия</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-purple-500/10">
              {promoCodes.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-6 py-12 text-center">
                    <div className="flex flex-col items-center gap-3">
                      <FiGift size={48} className="text-gray-600" />
                      <p className="text-gray-500">Промокоды не найдены</p>
                      <button
                        onClick={() => setShowModal(true)}
                        className="mt-2 px-4 py-2 btn-gradient rounded-lg text-sm"
                      >
                        Создать первый
                      </button>
                    </div>
                  </td>
                </tr>
              ) : (
                promoCodes.map((code) => (
                  <tr key={code.id} className="hover:bg-purple-500/5 transition-colors">
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-2">
                        <span className="font-mono font-bold text-purple-400">{code.code}</span>
                        <button
                          onClick={() => handleCopy(code.code)}
                          className="p-1.5 hover:bg-purple-500/20 rounded-lg transition"
                          title="Копировать"
                        >
                          <FiCopy size={14} className="text-gray-400 hover:text-purple-400" />
                        </button>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-2">
                        {code.discount_type === 'percentage' ? (
                          <>
                            <FiPercent className="text-green-400" size={16} />
                            <span className="font-semibold text-green-400">{code.discount_value}%</span>
                          </>
                        ) : code.discount_type === 'fixed' ? (
                          <>
                            <FiDollarSign className="text-blue-400" size={16} />
                            <span className="font-semibold text-blue-400">{code.discount_value} ₽</span>
                          </>
                        ) : (
                          <>
                            <FiPackage className="text-purple-400" size={16} />
                            <span className="font-semibold text-purple-400">{getDiscountDisplay(code)}</span>
                          </>
                        )}
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <span className="text-white font-medium">
                        {code.used_count} / {code.max_uses || '∞'}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <span className="text-gray-400">
                        {code.expires_at ? formatDate(code.expires_at) : 'Бессрочно'}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <button onClick={() => handleToggle(code)}>
                        {code.is_valid && code.is_active ? (
                          <span className="inline-flex items-center px-3 py-1 bg-green-500/20 text-green-400 rounded-full text-xs font-medium hover:bg-green-500/30 transition">
                            Активен
                          </span>
                        ) : !code.is_active ? (
                          <span className="inline-flex items-center px-3 py-1 bg-gray-500/20 text-gray-400 rounded-full text-xs font-medium hover:bg-gray-500/30 transition">
                            Отключен
                          </span>
                        ) : (
                          <span className="inline-flex items-center px-3 py-1 bg-red-500/20 text-red-400 rounded-full text-xs font-medium">
                            Истёк
                          </span>
                        )}
                      </button>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center justify-center gap-2">
                        <button
                          onClick={() => handleEdit(code)}
                          className="p-2 hover:bg-blue-500/20 text-blue-400 rounded-lg transition"
                          title="Редактировать"
                        >
                          <FiEdit2 size={18} />
                        </button>
                        <button
                          onClick={() => handleDelete(code.id)}
                          className="p-2 hover:bg-red-500/20 text-red-400 rounded-lg transition"
                          title="Удалить"
                        >
                          <FiTrash2 size={18} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50 p-4" onClick={() => setShowModal(false)}>
          <div className="dark-card max-w-lg w-full max-h-[90vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between p-6 border-b border-purple-500/20">
              <h3 className="text-xl font-bold text-white">
                {editingCode ? 'Редактировать промокод' : 'Создать промокод'}
              </h3>
              <button
                onClick={() => {
                  setShowModal(false)
                  setEditingCode(null)
                  resetForm()
                }}
                className="p-2 hover:bg-purple-500/20 rounded-lg transition"
              >
                <FiX size={20} className="text-gray-400" />
              </button>
            </div>

            <form onSubmit={handleSubmit} className="p-6 space-y-5">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Код промокода
                </label>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={formData.code}
                    onChange={(e) => setFormData({ ...formData, code: e.target.value.toUpperCase() })}
                    className="flex-1 dark-input rounded-xl px-4 py-3"
                    placeholder="SALE2025"
                    required
                  />
                  <button
                    type="button"
                    onClick={generateCode}
                    className="px-4 py-2 bg-purple-500/20 text-purple-300 rounded-xl hover:bg-purple-500/30 transition"
                  >
                    Сгенерировать
                  </button>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Тип промокода
                </label>
                <select
                  value={formData.discount_type}
                  onChange={(e) => setFormData({ ...formData, discount_type: e.target.value as 'percentage' | 'fixed' | 'free_plan' })}
                  className="w-full dark-input rounded-xl px-4 py-3"
                >
                  <option value="percentage">Скидка в процентах (%)</option>
                  <option value="fixed">Фиксированная скидка (₽)</option>
                  <option value="free_plan">Бесплатный тариф</option>
                </select>
              </div>

              {formData.discount_type === 'free_plan' ? (
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Выберите тариф для бесплатной выдачи
                  </label>
                  <select
                    value={formData.plan_id}
                    onChange={(e) => setFormData({ ...formData, plan_id: e.target.value })}
                    className="w-full dark-input rounded-xl px-4 py-3"
                    required
                  >
                    <option value="">-- Выберите тариф --</option>
                    {plans.map(plan => (
                      <option key={plan.id} value={plan.id}>
                        {plan.name} ({plan.price} ₽)
                      </option>
                    ))}
                  </select>
                  <p className="text-xs text-gray-500 mt-1">Пользователь получит этот тариф бесплатно</p>
                </div>
              ) : (
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Размер скидки
                  </label>
                  <input
                    type="number"
                    value={formData.discount_value}
                    onChange={(e) => setFormData({ ...formData, discount_value: parseFloat(e.target.value) })}
                    className="w-full dark-input rounded-xl px-4 py-3"
                    placeholder={formData.discount_type === 'percentage' ? '10' : '100'}
                    min="0"
                    step="0.01"
                    required
                  />
                </div>
              )}

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Макс. использований
                  </label>
                  <input
                    type="number"
                    value={formData.max_uses}
                    onChange={(e) => setFormData({ ...formData, max_uses: parseInt(e.target.value) })}
                    className="w-full dark-input rounded-xl px-4 py-3"
                    placeholder="100"
                    min="0"
                  />
                  <p className="text-xs text-gray-500 mt-1">0 = безлимит</p>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    На пользователя
                  </label>
                  <input
                    type="number"
                    value={formData.max_uses_per_user}
                    onChange={(e) => setFormData({ ...formData, max_uses_per_user: parseInt(e.target.value) })}
                    className="w-full dark-input rounded-xl px-4 py-3"
                    placeholder="1"
                    min="1"
                    required
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Срок действия
                </label>
                <input
                  type="date"
                  value={formData.expires_at}
                  onChange={(e) => setFormData({ ...formData, expires_at: e.target.value })}
                  className="w-full dark-input rounded-xl px-4 py-3"
                />
                <p className="text-xs text-gray-500 mt-1">Оставьте пустым для бессрочного</p>
              </div>

              <div className="flex gap-3 pt-4">
                <button
                  type="button"
                  onClick={() => {
                    setShowModal(false)
                    setEditingCode(null)
                    resetForm()
                  }}
                  className="flex-1 px-4 py-3 bg-gray-700 text-white rounded-xl hover:bg-gray-600 transition-colors"
                >
                  Отмена
                </button>
                <button
                  type="submit"
                  className="flex-1 px-4 py-3 btn-gradient rounded-xl font-medium"
                >
                  {editingCode ? 'Сохранить' : 'Создать'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
