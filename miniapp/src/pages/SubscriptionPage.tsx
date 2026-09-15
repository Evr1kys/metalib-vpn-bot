import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { 
  CheckIcon,
  StarIcon,
  SparklesIcon,
  ArrowPathIcon,
  CreditCardIcon
} from '@heroicons/react/24/outline'
import { useStore } from '../store'
import { api } from '../api'

interface Plan {
  id: string
  name: string
  price: number
  duration_days: number
  traffic_limit: number
  max_devices: number
  features: string[]
  is_popular?: boolean
  discount_percent?: number
}

export default function SubscriptionPage() {
  const { subscription, setSubscription } = useStore()
  const [plans, setPlans] = useState<Plan[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedPlan, setSelectedPlan] = useState<string | null>(null)
  const [processingPayment, setProcessingPayment] = useState(false)
  const [autoRenewLoading, setAutoRenewLoading] = useState(false)

  useEffect(() => {
    loadPlans()
  }, [])

  const loadPlans = async () => {
    setLoading(true)
    try {
      const response = await api.getPlans()
      if (response.success && response.plans) {
        setPlans(response.plans)
      } else {
        // Mock data for development
        setPlans([
          {
            id: '1',
            name: 'Старт',
            price: 149,
            duration_days: 30,
            traffic_limit: 50 * 1024 * 1024 * 1024,
            max_devices: 3,
            features: ['50 ГБ трафика', '3 устройства', 'Базовые серверы'],
          },
          {
            id: '2',
            name: 'Про',
            price: 299,
            duration_days: 30,
            traffic_limit: 150 * 1024 * 1024 * 1024,
            max_devices: 5,
            features: ['150 ГБ трафика', '5 устройств', 'Все серверы', 'Приоритетная поддержка'],
            is_popular: true,
          },
          {
            id: '3',
            name: 'Безлимит',
            price: 499,
            duration_days: 30,
            traffic_limit: -1,
            max_devices: 10,
            features: ['Безлимитный трафик', '10 устройств', 'Все серверы', 'VIP поддержка', 'Выделенный IP'],
          },
          {
            id: '4',
            name: 'Годовой',
            price: 2499,
            duration_days: 365,
            traffic_limit: -1,
            max_devices: 10,
            features: ['Безлимитный трафик', '10 устройств', 'Все серверы', 'VIP поддержка', 'Выделенный IP'],
            discount_percent: 40,
          },
        ])
      }
    } catch (error) {
      console.error('Failed to load plans:', error)
    } finally {
      setLoading(false)
    }
  }

  const handlePurchase = async (planId: string) => {
    setSelectedPlan(planId)
    setProcessingPayment(true)
    window.Telegram?.WebApp?.HapticFeedback?.impactOccurred('medium')

    try {
      const response = await api.createPayment(planId)
      if (response.success && response.paymentUrl) {
        // Open payment in Telegram browser
        window.Telegram?.WebApp?.openLink(response.paymentUrl)
      } else {
        window.Telegram?.WebApp?.showAlert('Не удалось создать платеж. Попробуйте позже.')
      }
    } catch (error) {
      console.error('Failed to create payment:', error)
      window.Telegram?.WebApp?.showAlert('Произошла ошибка. Попробуйте позже.')
    } finally {
      setProcessingPayment(false)
      setSelectedPlan(null)
    }
  }

  const toggleAutoRenew = async () => {
    if (!subscription) return
    
    setAutoRenewLoading(true)
    try {
      const newValue = !subscription.auto_renew
      const response = await api.toggleAutoRenewal(newValue)
      
      if (response.success) {
        setSubscription({ ...subscription, auto_renew: newValue })
        window.Telegram?.WebApp?.HapticFeedback?.notificationOccurred('success')
      }
    } catch (error) {
      console.error('Failed to toggle auto-renewal:', error)
    } finally {
      setAutoRenewLoading(false)
    }
  }

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('ru-RU', {
      day: 'numeric',
      month: 'long',
      year: 'numeric',
    })
  }

  if (loading) {
    return (
      <div className="p-4 space-y-4">
        {[1, 2, 3].map((i) => (
          <div key={i} className="glass rounded-2xl p-5 animate-pulse">
            <div className="h-6 bg-white/10 rounded w-1/3 mb-4" />
            <div className="h-8 bg-white/10 rounded w-1/2 mb-4" />
            <div className="space-y-2">
              <div className="h-4 bg-white/10 rounded w-3/4" />
              <div className="h-4 bg-white/10 rounded w-2/3" />
            </div>
          </div>
        ))}
      </div>
    )
  }

  return (
    <div className="p-4 space-y-4">
      {/* Current Subscription */}
      {subscription && subscription.status === 'active' && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="gradient-purple rounded-2xl p-5 space-y-4"
        >
          <div className="flex items-center justify-between">
            <div>
              <p className="text-white/70 text-sm">Текущий тариф</p>
              <h2 className="text-xl font-bold">{subscription.plan_name}</h2>
            </div>
            <div className="px-3 py-1 bg-white/20 rounded-full text-sm">
              Активен
            </div>
          </div>

          <div className="flex items-center justify-between text-sm">
            <span className="text-white/70">Действует до</span>
            <span className="font-medium">{formatDate(subscription.expires_at)}</span>
          </div>

          <div className="flex items-center justify-between pt-3 border-t border-white/20">
            <div className="flex items-center gap-2">
              <ArrowPathIcon className="w-5 h-5 text-white/70" />
              <span className="text-sm">Автопродление</span>
            </div>
            <button
              onClick={toggleAutoRenew}
              disabled={autoRenewLoading}
              className={`relative w-12 h-6 rounded-full transition-colors ${
                subscription.auto_renew ? 'bg-green-500' : 'bg-white/20'
              }`}
            >
              <motion.div
                layout
                className="absolute top-1 w-4 h-4 bg-white rounded-full"
                style={{ left: subscription.auto_renew ? '26px' : '4px' }}
              />
            </button>
          </div>
        </motion.div>
      )}

      {/* Plans */}
      <h2 className="text-lg font-semibold">
        {subscription ? 'Сменить тариф' : 'Выберите тариф'}
      </h2>

      <div className="space-y-3">
        {plans.map((plan, index) => (
          <motion.div
            key={plan.id}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.1 }}
            className={`relative glass rounded-2xl p-5 border-2 transition-colors ${
              plan.is_popular 
                ? 'border-purple-500' 
                : 'border-transparent hover:border-white/20'
            }`}
          >
            {plan.is_popular && (
              <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-1 bg-purple-500 rounded-full text-xs font-medium flex items-center gap-1">
                <StarIcon className="w-3 h-3" />
                Популярный
              </div>
            )}

            {plan.discount_percent && (
              <div className="absolute -top-3 right-4 px-3 py-1 bg-green-500 rounded-full text-xs font-medium">
                -{plan.discount_percent}%
              </div>
            )}

            <div className="flex items-start justify-between mb-4">
              <div>
                <h3 className="font-bold text-lg">{plan.name}</h3>
                <p className="text-gray-400 text-sm">
                  {plan.duration_days === 30 ? 'На месяц' : 
                   plan.duration_days === 365 ? 'На год' : 
                   `${plan.duration_days} дней`}
                </p>
              </div>
              <div className="text-right">
                <p className="text-2xl font-bold">{plan.price} ₽</p>
                {plan.duration_days === 365 && (
                  <p className="text-green-400 text-xs">
                    {Math.round(plan.price / 12)} ₽/мес
                  </p>
                )}
              </div>
            </div>

            <div className="space-y-2 mb-4">
              {plan.features.map((feature, i) => (
                <div key={i} className="flex items-center gap-2 text-sm">
                  <CheckIcon className="w-4 h-4 text-green-400 flex-shrink-0" />
                  <span className="text-gray-300">{feature}</span>
                </div>
              ))}
            </div>

            <button
              onClick={() => handlePurchase(plan.id)}
              disabled={processingPayment}
              className={`w-full flex items-center justify-center gap-2 py-3 rounded-xl font-medium transition-all ${
                plan.is_popular
                  ? 'bg-purple-500 hover:bg-purple-600 text-white'
                  : 'bg-white/10 hover:bg-white/20 text-white'
              } ${processingPayment && selectedPlan === plan.id ? 'opacity-50' : ''}`}
            >
              {processingPayment && selectedPlan === plan.id ? (
                <>
                  <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  Обработка...
                </>
              ) : (
                <>
                  <CreditCardIcon className="w-5 h-5" />
                  {subscription ? 'Сменить тариф' : 'Оформить'}
                </>
              )}
            </button>
          </motion.div>
        ))}
      </div>

      {/* Payment Methods */}
      <div className="glass rounded-2xl p-4">
        <h3 className="font-medium mb-3">Способы оплаты</h3>
        <div className="flex flex-wrap gap-2">
          {['Visa', 'MasterCard', 'МИР', 'СБП', 'Crypto'].map((method) => (
            <div
              key={method}
              className="px-3 py-1 bg-white/10 rounded-lg text-sm text-gray-300"
            >
              {method}
            </div>
          ))}
        </div>
      </div>

      {/* Money Back Guarantee */}
      <div className="glass rounded-2xl p-4 flex items-center gap-3">
        <div className="p-2 bg-green-500/20 rounded-xl">
          <SparklesIcon className="w-6 h-6 text-green-400" />
        </div>
        <div>
          <h3 className="font-medium">Гарантия возврата</h3>
          <p className="text-gray-400 text-sm">
            Вернём деньги в течение 7 дней, если не понравится
          </p>
        </div>
      </div>
    </div>
  )
}
