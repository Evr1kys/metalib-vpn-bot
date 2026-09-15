import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { 
  CreditCardIcon,
  CheckCircleIcon,
  XCircleIcon,
  ClockIcon,
  ArrowPathIcon,
  ReceiptRefundIcon,
  DocumentArrowDownIcon
} from '@heroicons/react/24/outline'
import { api } from '../api'

interface Payment {
  id: string
  amount: number
  currency: string
  status: 'completed' | 'pending' | 'failed' | 'refunded'
  payment_method: string
  plan_name: string
  created_at: string
  receipt_url?: string
}

export default function PaymentsPage() {
  const [payments, setPayments] = useState<Payment[]>([])
  const [loading, setLoading] = useState(true)
  const [totalSpent, setTotalSpent] = useState(0)
  const [filter, setFilter] = useState<'all' | 'completed' | 'pending' | 'failed'>('all')

  useEffect(() => {
    loadPayments()
  }, [])

  const loadPayments = async () => {
    setLoading(true)
    try {
      const response = await api.getPaymentHistory()
      if (response.success && response.data) {
        setPayments(response.data.payments)
        setTotalSpent(response.data.total_spent)
      }
    } catch (error) {
      console.error('Failed to load payments:', error)
    } finally {
      setLoading(false)
    }
  }

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr)
    return date.toLocaleDateString('ru-RU', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  const formatAmount = (amount: number, currency: string) => {
    return new Intl.NumberFormat('ru-RU', {
      style: 'currency',
      currency: currency || 'RUB',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    }).format(amount)
  }

  const getStatusIcon = (status: Payment['status']) => {
    switch (status) {
      case 'completed':
        return <CheckCircleIcon className="w-5 h-5 text-[var(--success)]" />
      case 'pending':
        return <ClockIcon className="w-5 h-5 text-yellow-500" />
      case 'failed':
        return <XCircleIcon className="w-5 h-5 text-[var(--danger)]" />
      case 'refunded':
        return <ReceiptRefundIcon className="w-5 h-5 text-blue-500" />
    }
  }

  const getStatusText = (status: Payment['status']) => {
    switch (status) {
      case 'completed': return 'Оплачен'
      case 'pending': return 'В обработке'
      case 'failed': return 'Ошибка'
      case 'refunded': return 'Возврат'
    }
  }

  const getStatusColor = (status: Payment['status']) => {
    switch (status) {
      case 'completed': return 'text-[var(--success)]'
      case 'pending': return 'text-yellow-500'
      case 'failed': return 'text-[var(--danger)]'
      case 'refunded': return 'text-blue-500'
    }
  }

  const filteredPayments = payments.filter(p => 
    filter === 'all' ? true : p.status === filter
  )

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[var(--primary)]" />
      </div>
    )
  }

  return (
    <div className="p-4 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold">Платежи</h1>
        <button 
          onClick={loadPayments}
          className="p-2 glass rounded-lg hover:border-[var(--primary)] transition-all"
        >
          <ArrowPathIcon className="w-5 h-5" />
        </button>
      </div>

      {/* Total Spent Card */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="glass rounded-xl p-4 bg-gradient-to-br from-[var(--primary)]/20 to-[var(--secondary)]/20"
      >
        <div className="flex items-center gap-3">
          <div className="p-3 bg-gradient-to-br from-[var(--primary)] to-[var(--secondary)] rounded-xl">
            <CreditCardIcon className="w-6 h-6 text-white" />
          </div>
          <div>
            <p className="text-[var(--text-secondary)] text-sm">Всего потрачено</p>
            <p className="text-2xl font-bold text-white">
              {formatAmount(totalSpent, 'RUB')}
            </p>
          </div>
        </div>
      </motion.div>

      {/* Filter Tabs */}
      <div className="flex gap-1 p-1 glass rounded-lg overflow-x-auto">
        {([
          { key: 'all', label: 'Все' },
          { key: 'completed', label: 'Оплачено' },
          { key: 'pending', label: 'В ожидании' },
          { key: 'failed', label: 'Ошибки' }
        ] as const).map(({ key, label }) => (
          <button
            key={key}
            onClick={() => setFilter(key)}
            className={`px-3 py-1.5 rounded-md text-sm font-medium whitespace-nowrap transition-all ${
              filter === key
                ? 'bg-[var(--primary)] text-white'
                : 'text-[var(--text-secondary)] hover:text-white'
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {/* Payments List */}
      <div className="space-y-3">
        {filteredPayments.length === 0 ? (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="glass rounded-xl p-8 text-center"
          >
            <CreditCardIcon className="w-12 h-12 mx-auto text-[var(--text-secondary)] mb-3" />
            <p className="text-[var(--text-secondary)]">
              {filter === 'all' 
                ? 'У вас пока нет платежей' 
                : `Нет платежей со статусом "${getStatusText(filter as Payment['status'])}"`
              }
            </p>
          </motion.div>
        ) : (
          filteredPayments.map((payment, index) => (
            <motion.div
              key={payment.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.05 }}
              className="glass rounded-xl p-4"
            >
              <div className="flex items-start justify-between">
                <div className="flex items-start gap-3">
                  {getStatusIcon(payment.status)}
                  <div>
                    <h3 className="font-semibold">{payment.plan_name}</h3>
                    <p className="text-sm text-[var(--text-secondary)]">
                      {formatDate(payment.created_at)}
                    </p>
                    <p className="text-xs text-[var(--text-secondary)] mt-1">
                      {payment.payment_method}
                    </p>
                  </div>
                </div>
                <div className="text-right">
                  <p className="font-bold text-lg">
                    {formatAmount(payment.amount, payment.currency)}
                  </p>
                  <p className={`text-sm ${getStatusColor(payment.status)}`}>
                    {getStatusText(payment.status)}
                  </p>
                </div>
              </div>

              {/* Receipt Download */}
              {payment.receipt_url && payment.status === 'completed' && (
                <a
                  href={payment.receipt_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="mt-3 flex items-center justify-center gap-2 p-2 glass rounded-lg text-sm text-[var(--primary)] hover:bg-[var(--primary)]/10 transition-all"
                >
                  <DocumentArrowDownIcon className="w-4 h-4" />
                  Скачать чек
                </a>
              )}
            </motion.div>
          ))
        )}
      </div>

      {/* Payment Summary */}
      {payments.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="glass rounded-xl p-4"
        >
          <h2 className="font-semibold mb-3">Сводка</h2>
          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span className="text-[var(--text-secondary)]">Всего платежей</span>
              <span className="font-medium">{payments.length}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-[var(--text-secondary)]">Успешных</span>
              <span className="font-medium text-[var(--success)]">
                {payments.filter(p => p.status === 'completed').length}
              </span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-[var(--text-secondary)]">В ожидании</span>
              <span className="font-medium text-yellow-500">
                {payments.filter(p => p.status === 'pending').length}
              </span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-[var(--text-secondary)]">С ошибками</span>
              <span className="font-medium text-[var(--danger)]">
                {payments.filter(p => p.status === 'failed').length}
              </span>
            </div>
          </div>
        </motion.div>
      )}
    </div>
  )
}
