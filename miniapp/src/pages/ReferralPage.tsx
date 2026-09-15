import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { 
  UserGroupIcon,
  GiftIcon,
  ShareIcon,
  DocumentDuplicateIcon,
  CheckIcon,
  ArrowTrendingUpIcon,
  BanknotesIcon,
  UserPlusIcon
} from '@heroicons/react/24/outline'
import { useStore } from '../store'
import { api } from '../api'

interface ReferralHistoryItem {
  id: string
  username: string
  joined_at: string
  has_subscription: boolean
  earned: number
}

export default function ReferralPage() {
  const { referralStats, setReferralStats } = useStore()
  const [loading, setLoading] = useState(true)
  const [copied, setCopied] = useState(false)
  const [history, setHistory] = useState<ReferralHistoryItem[]>([])
  const [showHistory, setShowHistory] = useState(false)
  const [withdrawing, setWithdrawing] = useState(false)

  useEffect(() => {
    loadReferralData()
  }, [])

  const loadReferralData = async () => {
    setLoading(true)
    try {
      const [statsResponse, historyResponse] = await Promise.all([
        api.getReferralStats(),
        api.getReferralHistory(),
      ])

      if (statsResponse.success && statsResponse.stats) {
        setReferralStats(statsResponse.stats)
      } else {
        // Mock data
        setReferralStats({
          total_referrals: 12,
          active_referrals: 8,
          total_earned: 2450,
          pending_earnings: 350,
          referral_code: 'METALIB123',
          referral_link: 'https://t.me/metalib_vpn_bot?start=ref_METALIB123',
        })
      }

      if (historyResponse.success && historyResponse.history) {
        setHistory(historyResponse.history)
      } else {
        // Mock data
        setHistory([
          { id: '1', username: 'alex_dev', joined_at: new Date(Date.now() - 86400000).toISOString(), has_subscription: true, earned: 150 },
          { id: '2', username: 'maria_k', joined_at: new Date(Date.now() - 172800000).toISOString(), has_subscription: true, earned: 150 },
          { id: '3', username: 'ivan2024', joined_at: new Date(Date.now() - 259200000).toISOString(), has_subscription: false, earned: 0 },
        ])
      }
    } catch (error) {
      console.error('Failed to load referral data:', error)
    } finally {
      setLoading(false)
    }
  }

  const copyLink = async () => {
    if (referralStats?.referral_link) {
      await navigator.clipboard.writeText(referralStats.referral_link)
      setCopied(true)
      window.Telegram?.WebApp?.HapticFeedback?.notificationOccurred('success')
      setTimeout(() => setCopied(false), 2000)
    }
  }

  const shareLink = () => {
    if (referralStats?.referral_link) {
      const text = `Попробуй MetaLib VPN - быстрый и безопасный VPN!\n\nПереходи по моей ссылке и получи скидку 10% на первую подписку:`
      const url = `https://t.me/share/url?url=${encodeURIComponent(referralStats.referral_link)}&text=${encodeURIComponent(text)}`
      window.Telegram?.WebApp?.openTelegramLink(url)
    }
  }

  const handleWithdraw = async () => {
    if (!referralStats || referralStats.pending_earnings < 500) {
      window.Telegram?.WebApp?.showAlert('Минимальная сумма для вывода: 500 ₽')
      return
    }

    window.Telegram?.WebApp?.showConfirm(
      `Вывести ${referralStats.pending_earnings} ₽ на баланс?`,
      async (confirmed) => {
        if (confirmed) {
          setWithdrawing(true)
          try {
            const response = await api.withdrawReferralEarnings()
            if (response.success) {
              setReferralStats({
                ...referralStats,
                total_earned: referralStats.total_earned + referralStats.pending_earnings,
                pending_earnings: 0,
              })
              window.Telegram?.WebApp?.HapticFeedback?.notificationOccurred('success')
              window.Telegram?.WebApp?.showAlert('Средства успешно переведены на баланс!')
            }
          } catch (error) {
            console.error('Failed to withdraw:', error)
          } finally {
            setWithdrawing(false)
          }
        }
      }
    )
  }

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr)
    const now = new Date()
    const diff = now.getTime() - date.getTime()
    const days = Math.floor(diff / 86400000)

    if (days === 0) return 'Сегодня'
    if (days === 1) return 'Вчера'
    if (days < 7) return `${days} дн. назад`

    return date.toLocaleDateString('ru-RU', {
      day: 'numeric',
      month: 'short',
    })
  }

  if (loading) {
    return (
      <div className="p-4 space-y-4">
        <div className="gradient-purple rounded-2xl p-5 animate-pulse">
          <div className="h-6 bg-white/20 rounded w-1/2 mb-4" />
          <div className="grid grid-cols-2 gap-4">
            <div className="h-16 bg-white/10 rounded-xl" />
            <div className="h-16 bg-white/10 rounded-xl" />
          </div>
        </div>
        <div className="glass rounded-2xl p-4 animate-pulse">
          <div className="h-12 bg-white/10 rounded-xl" />
        </div>
      </div>
    )
  }

  if (!referralStats) {
    return (
      <div className="p-4">
        <div className="text-center py-8">
          <p className="text-gray-400">Не удалось загрузить данные</p>
          <button
            onClick={loadReferralData}
            className="btn-secondary mt-4"
          >
            Попробовать снова
          </button>
        </div>
      </div>
    )
  }

  const conversionRate = referralStats.total_referrals > 0
    ? Math.round((referralStats.active_referrals / referralStats.total_referrals) * 100)
    : 0

  return (
    <div className="p-4 space-y-4">
      {/* Header Stats */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="gradient-purple rounded-2xl p-5"
      >
        <div className="flex items-center gap-3 mb-4">
          <div className="p-2 bg-white/20 rounded-xl">
            <UserGroupIcon className="w-6 h-6" />
          </div>
          <div>
            <h2 className="font-bold text-lg">Реферальная программа</h2>
            <p className="text-white/70 text-sm">Приглашайте друзей и зарабатывайте</p>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div className="bg-white/10 rounded-xl p-3">
            <p className="text-white/70 text-sm">Рефералов</p>
            <p className="text-2xl font-bold">
              {referralStats.active_referrals}
              <span className="text-sm font-normal text-white/50">
                /{referralStats.total_referrals}
              </span>
            </p>
          </div>
          <div className="bg-white/10 rounded-xl p-3">
            <p className="text-white/70 text-sm">Конверсия</p>
            <p className="text-2xl font-bold">{conversionRate}%</p>
          </div>
        </div>
      </motion.div>

      {/* Earnings Card */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="glass rounded-2xl p-5"
      >
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-semibold">Ваш заработок</h3>
          <ArrowTrendingUpIcon className="w-5 h-5 text-green-400" />
        </div>

        <div className="grid grid-cols-2 gap-4 mb-4">
          <div>
            <p className="text-gray-400 text-sm">Всего заработано</p>
            <p className="text-xl font-bold text-green-400">
              {referralStats.total_earned} ₽
            </p>
          </div>
          <div>
            <p className="text-gray-400 text-sm">Доступно к выводу</p>
            <p className="text-xl font-bold text-purple-400">
              {referralStats.pending_earnings} ₽
            </p>
          </div>
        </div>

        <button
          onClick={handleWithdraw}
          disabled={withdrawing || referralStats.pending_earnings < 500}
          className="w-full btn-primary disabled:opacity-50 flex items-center justify-center gap-2"
        >
          {withdrawing ? (
            <>
              <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              Обработка...
            </>
          ) : (
            <>
              <BanknotesIcon className="w-5 h-5" />
              Вывести на баланс
            </>
          )}
        </button>
        
        {referralStats.pending_earnings < 500 && (
          <p className="text-xs text-gray-400 text-center mt-2">
            Минимум для вывода: 500 ₽
          </p>
        )}
      </motion.div>

      {/* Referral Link */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
        className="glass rounded-2xl p-5"
      >
        <h3 className="font-semibold mb-3">Ваша реферальная ссылка</h3>
        
        <div className="flex gap-2 mb-4">
          <div className="flex-1 bg-white/5 rounded-xl p-3 font-mono text-sm truncate">
            {referralStats.referral_link}
          </div>
          <button
            onClick={copyLink}
            className={`p-3 rounded-xl transition-colors ${
              copied 
                ? 'bg-green-500/20 text-green-400' 
                : 'bg-white/10 hover:bg-white/20'
            }`}
          >
            {copied ? (
              <CheckIcon className="w-5 h-5" />
            ) : (
              <DocumentDuplicateIcon className="w-5 h-5" />
            )}
          </button>
        </div>

        <button
          onClick={shareLink}
          className="w-full btn-secondary flex items-center justify-center gap-2"
        >
          <ShareIcon className="w-5 h-5" />
          Поделиться в Telegram
        </button>
      </motion.div>

      {/* How it works */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.3 }}
        className="glass rounded-2xl p-5"
      >
        <h3 className="font-semibold mb-4">Как это работает?</h3>
        
        <div className="space-y-4">
          <div className="flex gap-4">
            <div className="w-8 h-8 bg-purple-500/20 rounded-full flex items-center justify-center flex-shrink-0">
              <span className="text-purple-400 font-bold">1</span>
            </div>
            <div>
              <h4 className="font-medium">Поделитесь ссылкой</h4>
              <p className="text-gray-400 text-sm">
                Отправьте вашу реферальную ссылку друзьям
              </p>
            </div>
          </div>

          <div className="flex gap-4">
            <div className="w-8 h-8 bg-purple-500/20 rounded-full flex items-center justify-center flex-shrink-0">
              <span className="text-purple-400 font-bold">2</span>
            </div>
            <div>
              <h4 className="font-medium">Друг оформляет подписку</h4>
              <p className="text-gray-400 text-sm">
                Ваш друг получает скидку 10% на первый месяц
              </p>
            </div>
          </div>

          <div className="flex gap-4">
            <div className="w-8 h-8 bg-purple-500/20 rounded-full flex items-center justify-center flex-shrink-0">
              <span className="text-purple-400 font-bold">3</span>
            </div>
            <div>
              <h4 className="font-medium">Получите вознаграждение</h4>
              <p className="text-gray-400 text-sm">
                Вы получаете 15% от каждой оплаты реферала
              </p>
            </div>
          </div>
        </div>
      </motion.div>

      {/* Referral History */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.4 }}
        className="glass rounded-2xl overflow-hidden"
      >
        <button
          onClick={() => setShowHistory(!showHistory)}
          className="w-full p-4 flex items-center justify-between"
        >
          <div className="flex items-center gap-3">
            <UserPlusIcon className="w-5 h-5 text-purple-400" />
            <span className="font-semibold">История рефералов</span>
          </div>
          <motion.div
            animate={{ rotate: showHistory ? 180 : 0 }}
            transition={{ duration: 0.2 }}
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </motion.div>
        </button>

        <AnimatePresence>
          {showHistory && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.2 }}
            >
              <div className="border-t border-white/10">
                {history.length > 0 ? (
                  history.map((item, index) => (
                    <div
                      key={item.id}
                      className={`p-4 flex items-center justify-between ${
                        index < history.length - 1 ? 'border-b border-white/10' : ''
                      }`}
                    >
                      <div className="flex items-center gap-3">
                        <div className={`w-10 h-10 rounded-full flex items-center justify-center ${
                          item.has_subscription 
                            ? 'bg-green-500/20' 
                            : 'bg-gray-500/20'
                        }`}>
                          <span className="text-sm font-medium">
                            {item.username.charAt(0).toUpperCase()}
                          </span>
                        </div>
                        <div>
                          <p className="font-medium">@{item.username}</p>
                          <p className="text-xs text-gray-400">
                            {formatDate(item.joined_at)}
                          </p>
                        </div>
                      </div>
                      <div className="text-right">
                        {item.has_subscription ? (
                          <>
                            <p className="text-green-400 font-medium">
                              +{item.earned} ₽
                            </p>
                            <span className="badge-active">Активен</span>
                          </>
                        ) : (
                          <span className="badge-pending">Ожидание</span>
                        )}
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="p-8 text-center">
                    <GiftIcon className="w-12 h-12 text-gray-500 mx-auto mb-3" />
                    <p className="text-gray-400">У вас пока нет рефералов</p>
                    <p className="text-gray-500 text-sm mt-1">
                      Поделитесь ссылкой, чтобы начать зарабатывать
                    </p>
                  </div>
                )}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>
    </div>
  )
}
