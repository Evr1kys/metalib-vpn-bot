import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { 
  ShieldCheckIcon, 
  BoltIcon, 
  ClockIcon,
  ArrowRightIcon,
  QrCodeIcon,
  DocumentDuplicateIcon,
  CheckIcon,
  DevicePhoneMobileIcon,
  GlobeAltIcon,
  LockClosedIcon,
  SignalIcon,
  FingerPrintIcon
} from '@heroicons/react/24/outline'
import { useState, useEffect } from 'react'
import { useStore } from '../store'
import { api } from '../api'

export default function HomePage() {
  const navigate = useNavigate()
  const { user, subscription, setVpnKey, vpnKey } = useStore()
  const [copied, setCopied] = useState(false)
  const [showQR, setShowQR] = useState(false)
  const [qrCode, setQrCode] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const isActive = subscription?.status === 'active'

  const loadVpnKey = async () => {
    if (vpnKey) return
    
    setLoading(true)
    try {
      const response = await api.getVpnKey()
      if (response.success && response.key) {
        setVpnKey(response.key)
        if (response.qrCode) {
          setQrCode(response.qrCode)
        }
      }
    } catch (error) {
      console.error('Failed to load VPN key:', error)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (isActive) {
      loadVpnKey()
    }
  }, [isActive])

  const copyKey = async () => {
    if (vpnKey) {
      await navigator.clipboard.writeText(vpnKey)
      setCopied(true)
      window.Telegram?.WebApp?.HapticFeedback?.notificationOccurred('success')
      setTimeout(() => setCopied(false), 2000)
    }
  }

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr)
    return date.toLocaleDateString('ru-RU', { 
      day: 'numeric', 
      month: 'long', 
      year: 'numeric' 
    })
  }

  const getProgressColor = (percent: number) => {
    if (percent < 50) return 'bg-green-500'
    if (percent < 80) return 'bg-yellow-500'
    return 'bg-red-500'
  }

  const trafficPercent = subscription 
    ? (subscription.traffic_used / subscription.traffic_limit) * 100 
    : 0

  return (
    <div className="p-4 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white">
            Привет, {user?.first_name || 'друг'}
          </h1>
          <p className="text-[var(--text-secondary)] text-sm">
            {isActive ? 'VPN активен и защищает вас' : 'Подключите VPN для защиты'}
          </p>
        </div>
        <div className={`px-3 py-1.5 rounded-full text-sm font-medium border ${
          isActive 
            ? 'bg-green-500/20 text-green-400 border-green-500/30' 
            : 'bg-red-500/20 text-red-400 border-red-500/30'
        }`}>
          {isActive ? 'Активен' : 'Неактивен'}
        </div>
      </div>

      {/* Main Card - Subscription Info */}
      {isActive && subscription ? (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="subscription-card"
        >
          <div className="relative z-10 space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="p-3 bg-gradient-to-br from-[var(--primary)] to-[var(--secondary)] rounded-xl shadow-lg">
                  <ShieldCheckIcon className="w-6 h-6 text-white" />
                </div>
                <div>
                  <h2 className="font-bold text-lg">{subscription.plan_name}</h2>
                  <p className="text-[var(--text-secondary)] text-sm">
                    {subscription.days_left} дней осталось
                  </p>
                </div>
              </div>
              <button 
                onClick={() => navigate('/subscription')}
                className="p-2.5 glass rounded-xl hover:border-[var(--primary)] transition-all duration-300"
              >
                <ArrowRightIcon className="w-5 h-5" />
              </button>
            </div>

            {/* Traffic Usage */}
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-[var(--text-secondary)]">Трафик</span>
                <span className="font-medium">
                  {(subscription.traffic_used / 1024 / 1024 / 1024).toFixed(1)} / {(subscription.traffic_limit / 1024 / 1024 / 1024).toFixed(0)} GB
                </span>
              </div>
              <div className="h-2 bg-white/10 rounded-full overflow-hidden">
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${Math.min(trafficPercent, 100)}%` }}
                  transition={{ duration: 0.5, ease: 'easeOut' }}
                  className={`h-full rounded-full ${getProgressColor(trafficPercent)}`}
                />
              </div>
            </div>

            {/* Expiry Date */}
            <div className="flex items-center gap-2 text-[var(--text-secondary)] text-sm">
              <ClockIcon className="w-4 h-4" />
              <span>Действует до {formatDate(subscription.expires_at)}</span>
            </div>
          </div>
        </motion.div>
      ) : (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="metalib-card relative overflow-hidden"
        >
          <div className="absolute inset-0 bg-gradient-to-br from-[var(--primary)]/10 to-[var(--secondary)]/10 pointer-events-none" />
          <div className="relative z-10 text-center space-y-4">
            <div className="w-16 h-16 mx-auto bg-gradient-to-br from-[var(--primary)] to-[var(--secondary)] rounded-2xl flex items-center justify-center shadow-lg animate-glow">
              <ShieldCheckIcon className="w-8 h-8 text-white" />
            </div>
            <div>
              <h2 className="font-bold text-lg">Нет активной подписки</h2>
              <p className="text-[var(--text-secondary)] text-sm mt-1">
                Оформите подписку для безопасного доступа в интернет
              </p>
            </div>
            <button
              onClick={() => navigate('/subscription')}
              className="w-full btn-primary flex items-center justify-center gap-2"
            >
              <BoltIcon className="w-5 h-5" />
              Выбрать тариф
            </button>
          </div>
        </motion.div>
      )}

      {/* VPN Key Section */}
      {isActive && vpnKey && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="metalib-card space-y-4"
        >
          <div className="flex items-center justify-between">
            <h3 className="font-semibold">Ваш ключ VPN</h3>
            <button
              onClick={() => setShowQR(!showQR)}
              className="p-2 glass rounded-lg hover:border-[var(--primary)] transition-all duration-300"
            >
              <QrCodeIcon className="w-5 h-5" />
            </button>
          </div>

          {showQR && qrCode ? (
            <motion.div
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              className="flex justify-center p-4 bg-white rounded-xl"
            >
              <img src={qrCode} alt="QR Code" className="w-48 h-48" />
            </motion.div>
          ) : (
            <div className="flex gap-2">
              <div className="flex-1 bg-[var(--bg-secondary)] rounded-xl p-3 font-mono text-sm truncate border border-[var(--border)]">
                {vpnKey.substring(0, 40)}...
              </div>
              <button
                onClick={copyKey}
                className={`p-3 rounded-xl transition-all duration-300 ${
                  copied 
                    ? 'bg-[var(--success)]/20 text-[var(--success)] border border-[var(--success)]/30' 
                    : 'glass hover:border-[var(--primary)]'
                }`}
              >
                {copied ? (
                  <CheckIcon className="w-5 h-5" />
                ) : (
                  <DocumentDuplicateIcon className="w-5 h-5" />
                )}
              </button>
            </div>
          )}

          <p className="text-xs text-[var(--text-muted)] text-center">
            Скопируйте ключ или отсканируйте QR-код в приложении
          </p>
        </motion.div>
      )}

      {/* Loading VPN Key */}
      {isActive && loading && !vpnKey && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="metalib-card"
        >
          <div className="flex items-center justify-center gap-3 py-4">
            <div className="w-5 h-5 border-2 border-[var(--primary)] border-t-transparent rounded-full animate-spin" />
            <span className="text-[var(--text-secondary)]">Загрузка ключа...</span>
          </div>
        </motion.div>
      )}

      {/* Quick Stats */}
      {isActive && subscription && (
        <div className="grid grid-cols-2 gap-3">
          <motion.button
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            onClick={() => navigate('/devices')}
            className="stats-card card-hover text-left"
          >
            <div className="flex items-center justify-between mb-2">
              <span className="stats-card-value">
                {subscription.devices_count}
              </span>
              <span className="text-[var(--text-muted)]">/ {subscription.max_devices}</span>
            </div>
            <p className="text-[var(--text-secondary)] text-sm">Устройств</p>
          </motion.button>

          <motion.button
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
            onClick={() => navigate('/servers')}
            className="stats-card card-hover text-left"
          >
            <div className="flex items-center justify-between mb-2">
              <span className="stats-card-value">15+</span>
              <GlobeAltIcon className="w-5 h-5 text-[var(--primary)]" />
            </div>
            <p className="text-[var(--text-secondary)] text-sm">Серверов</p>
          </motion.button>
        </div>
      )}

      {/* Features List */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.4 }}
        className="metalib-card space-y-3"
      >
        <h3 className="font-semibold bg-gradient-to-r from-[var(--primary)] to-[var(--secondary)] bg-clip-text text-transparent">
          Преимущества MetaLib VPN
        </h3>
        <div className="space-y-2">
          <div className="flex items-center gap-3 p-2 rounded-lg hover:bg-[var(--surface-light)] transition-colors">
            <LockClosedIcon className="w-5 h-5 text-[var(--primary)]" />
            <span className="text-[var(--text-secondary)] text-sm">Шифрование военного уровня</span>
          </div>
          <div className="flex items-center gap-3 p-2 rounded-lg hover:bg-[var(--surface-light)] transition-colors">
            <SignalIcon className="w-5 h-5 text-[var(--primary)]" />
            <span className="text-[var(--text-secondary)] text-sm">Скорость до 1 Гбит/с</span>
          </div>
          <div className="flex items-center gap-3 p-2 rounded-lg hover:bg-[var(--surface-light)] transition-colors">
            <GlobeAltIcon className="w-5 h-5 text-[var(--primary)]" />
            <span className="text-[var(--text-secondary)] text-sm">Серверы в 15+ странах</span>
          </div>
          <div className="flex items-center gap-3 p-2 rounded-lg hover:bg-[var(--surface-light)] transition-colors">
            <DevicePhoneMobileIcon className="w-5 h-5 text-[var(--primary)]" />
            <span className="text-[var(--text-secondary)] text-sm">До 5 устройств одновременно</span>
          </div>
          <div className="flex items-center gap-3 p-2 rounded-lg hover:bg-[var(--surface-light)] transition-colors">
            <FingerPrintIcon className="w-5 h-5 text-[var(--primary)]" />
            <span className="text-[var(--text-secondary)] text-sm">Без логов и отслеживания</span>
          </div>
        </div>
      </motion.div>
    </div>
  )
}
