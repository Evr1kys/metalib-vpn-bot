'use client'

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/lib/api'
import { FiDollarSign, FiUser, FiCalendar, FiFilter, FiDownload, FiCheckCircle, FiClock, FiXCircle, FiChevronLeft, FiChevronRight } from 'react-icons/fi'

export default function TransactionsPage() {
  const [statusFilter, setStatusFilter] = useState('all')
  const [dateFilter, setDateFilter] = useState('all')
  const [page, setPage] = useState(0)
  const limit = 20

  const { data: payments, isLoading } = useQuery({
    queryKey: ['payments', statusFilter, page],
    queryFn: () => apiClient.getPayments({ skip: page * limit, limit: 500, status: statusFilter !== 'all' ? statusFilter : undefined })
  })

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-500"></div>
      </div>
    )
  }

  const paymentList = Array.isArray(payments) ? payments : []

  // Calculate stats
  const totalAmount = paymentList.filter((p: any) => p.status === 'paid').reduce((sum: number, p: any) => sum + p.amount, 0)
  const completedCount = paymentList.filter((p: any) => p.status === 'paid').length
  const pendingCount = paymentList.filter((p: any) => p.status === 'pending').length

  // Filter by date
  const dateFilteredPayments = paymentList.filter((p: any) => {
    if (dateFilter === 'all') return true
    const date = new Date(p.created_at)
    const now = new Date()
    if (dateFilter === 'today') {
      return date.toDateString() === now.toDateString()
    }
    if (dateFilter === 'week') {
      const weekAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000)
      return date >= weekAgo
    }
    if (dateFilter === 'month') {
      const monthAgo = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000)
      return date >= monthAgo
    }
    return true
  })

  // Pagination
  const totalFiltered = dateFilteredPayments.length
  const totalPages = Math.ceil(totalFiltered / limit)
  const filteredPayments = dateFilteredPayments.slice(page * limit, (page + 1) * limit)

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'paid':
        return (
          <span className="px-2 py-1 rounded-full bg-green-500/20 text-green-400 text-xs flex items-center">
            <FiCheckCircle className="mr-1" /> Оплачено
          </span>
        )
      case 'pending':
        return (
          <span className="px-2 py-1 rounded-full bg-yellow-500/20 text-yellow-400 text-xs flex items-center">
            <FiClock className="mr-1" /> Ожидает
          </span>
        )
      default:
        return (
          <span className="px-2 py-1 rounded-full bg-red-500/20 text-red-400 text-xs flex items-center">
            <FiXCircle className="mr-1" /> Отменено
          </span>
        )
    }
  }

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold gradient-text">Транзакции</h1>
          <p className="mt-2 text-gray-400">История платежей пользователей</p>
        </div>
        <button className="px-4 py-2 rounded-xl bg-[#1a1a2e] border border-purple-500/20 text-gray-300 hover:text-white flex items-center transition-colors">
          <FiDownload className="mr-2" /> Экспорт CSV
        </button>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="stat-gradient-green p-5 rounded-xl">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-gray-400 text-sm">Общий доход</p>
              <p className="text-2xl font-bold text-white">{totalAmount.toLocaleString()} ₽</p>
            </div>
            <FiDollarSign className="w-8 h-8 text-green-400" />
          </div>
        </div>
        
        <div className="stat-gradient-blue p-5 rounded-xl">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-gray-400 text-sm">Успешных платежей</p>
              <p className="text-2xl font-bold text-white">{completedCount}</p>
            </div>
            <FiCheckCircle className="w-8 h-8 text-blue-400" />
          </div>
        </div>

        <div className="stat-gradient-orange p-5 rounded-xl">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-gray-400 text-sm">Ожидают оплаты</p>
              <p className="text-2xl font-bold text-white">{pendingCount}</p>
            </div>
            <FiClock className="w-8 h-8 text-orange-400" />
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="dark-card p-4">
        <div className="flex flex-wrap items-center gap-4">
          <div className="flex items-center space-x-2">
            <FiFilter className="text-gray-400" />
            <span className="text-gray-400">Фильтры:</span>
          </div>
          
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-4 py-2 bg-[#1a1a2e] border border-purple-500/20 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-purple-500"
          >
            <option value="all">Все статусы</option>
            <option value="paid">Оплачено</option>
            <option value="pending">Ожидает</option>
            <option value="cancelled">Отменено</option>
          </select>

          <select
            value={dateFilter}
            onChange={(e) => setDateFilter(e.target.value)}
            className="px-4 py-2 bg-[#1a1a2e] border border-purple-500/20 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-purple-500"
          >
            <option value="all">За все время</option>
            <option value="today">Сегодня</option>
            <option value="week">За неделю</option>
            <option value="month">За месяц</option>
          </select>
        </div>
      </div>

      {/* Transactions Table */}
      <div className="dark-card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-purple-500/20">
                <th className="text-left p-4 text-gray-400 font-medium">Пользователь</th>
                <th className="text-left p-4 text-gray-400 font-medium">Сумма</th>
                <th className="text-left p-4 text-gray-400 font-medium">Тариф</th>
                <th className="text-left p-4 text-gray-400 font-medium">Статус</th>
                <th className="text-left p-4 text-gray-400 font-medium">Дата</th>
              </tr>
            </thead>
            <tbody>
              {filteredPayments.length === 0 ? (
                <tr>
                  <td colSpan={5} className="p-8 text-center text-gray-500">
                    <FiDollarSign className="w-12 h-12 mx-auto mb-3 opacity-50" />
                    <p>Транзакций не найдено</p>
                  </td>
                </tr>
              ) : (
                filteredPayments.map((payment: any) => (
                  <tr key={payment.id} className="border-b border-purple-500/10 hover:bg-purple-500/5 transition-colors">
                    <td className="p-4">
                      <div className="flex items-center space-x-3">
                        <div className="w-10 h-10 rounded-full bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center">
                          <FiUser className="w-5 h-5 text-white" />
                        </div>
                        <div>
                          <p className="text-white font-medium">
                            {payment.user?.first_name || payment.user?.username || 'Пользователь'}
                          </p>
                          <p className="text-xs text-gray-500">
                            {payment.user?.username ? `@${payment.user.username}` : `ID: ${payment.user?.telegram_id || payment.user_id}`}
                          </p>
                        </div>
                      </div>
                    </td>
                    <td className="p-4">
                      <span className="text-white font-semibold">{payment.amount?.toLocaleString()} {payment.currency}</span>
                    </td>
                    <td className="p-4">
                      <span className="text-gray-300">{payment.plan_name || '—'}</span>
                    </td>
                    <td className="p-4">
                      {getStatusBadge(payment.status)}
                    </td>
                    <td className="p-4">
                      <div className="flex items-center text-gray-400 text-sm">
                        <FiCalendar className="mr-2" />
                        {new Date(payment.created_at).toLocaleString('ru-RU')}
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="p-4 border-t border-purple-500/20 flex flex-col sm:flex-row items-center justify-between gap-4">
            <p className="text-sm text-gray-400">
              Показано {page * limit + 1}-{Math.min((page + 1) * limit, totalFiltered)} из {totalFiltered}
            </p>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setPage(p => Math.max(0, p - 1))}
                disabled={page === 0}
                className="p-2 rounded-lg bg-[#1a1a2e] border border-purple-500/20 text-gray-400 hover:text-white disabled:opacity-50 transition-colors"
              >
                <FiChevronLeft size={20} />
              </button>
              <span className="px-4 py-2 text-white">
                {page + 1} / {totalPages}
              </span>
              <button
                onClick={() => setPage(p => Math.min(totalPages - 1, p + 1))}
                disabled={page >= totalPages - 1}
                className="p-2 rounded-lg bg-[#1a1a2e] border border-purple-500/20 text-gray-400 hover:text-white disabled:opacity-50 transition-colors"
              >
                <FiChevronRight size={20} />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
