import { useState } from 'react'
import { motion } from 'framer-motion'
import { 
  GlobeAltIcon,
  BellIcon,
  ShieldCheckIcon,
  QuestionMarkCircleIcon,
  DocumentTextIcon,
  ChevronRightIcon,
  SwatchIcon
} from '@heroicons/react/24/outline'
import { useStore } from '../store'
import { api } from '../api'
import { useThemeStore, themes, themeLabels, ThemeName } from '../theme'

const languages = [
  { code: 'ru', name: 'Русский', flag: '🇷🇺' },
  { code: 'en', name: 'English', flag: '🇬🇧' },
  { code: 'uk', name: 'Українська', flag: '🇺🇦' },
]

export default function SettingsPage() {
  const { 
    user, 
    subscription,
    language, 
    setLanguage, 
    notifications, 
    setNotifications 
  } = useStore()
  
  const { theme, setTheme } = useThemeStore()
  const [showLanguageModal, setShowLanguageModal] = useState(false)
  const [showThemeModal, setShowThemeModal] = useState(false)
  const [notificationLoading, setNotificationLoading] = useState(false)

  const handleLanguageChange = async (lang: 'ru' | 'en' | 'uk') => {
    try {
      await api.updateLanguage(lang)
      setLanguage(lang)
      setShowLanguageModal(false)
      window.Telegram?.WebApp?.HapticFeedback?.notificationOccurred('success')
    } catch (error) {
      console.error('Failed to update language:', error)
    }
  }

  const handleNotificationToggle = async () => {
    setNotificationLoading(true)
    try {
      const newValue = !notifications
      await api.updateNotifications(newValue)
      setNotifications(newValue)
      window.Telegram?.WebApp?.HapticFeedback?.selectionChanged()
    } catch (error) {
      console.error('Failed to update notifications:', error)
    } finally {
      setNotificationLoading(false)
    }
  }

  const openSupport = () => {
    window.Telegram?.WebApp?.openTelegramLink('https://t.me/metalib_support')
  }

  const openPrivacy = () => {
    window.Telegram?.WebApp?.openLink('https://metalib.xyz/privacy')
  }

  const openTerms = () => {
    window.Telegram?.WebApp?.openLink('https://metalib.xyz/terms')
  }

  const currentLanguage = languages.find(l => l.code === language)
  const currentTheme = themeLabels[theme]

  return (
    <div className="p-4 space-y-4">
      {/* User Info */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="glass rounded-2xl p-5"
      >
        <div className="flex items-center gap-4">
          <div className="w-16 h-16 bg-purple-500/20 rounded-2xl flex items-center justify-center">
            <span className="text-2xl font-bold text-purple-400">
              {user?.first_name?.charAt(0) || '?'}
            </span>
          </div>
          <div className="flex-1">
            <h2 className="font-bold text-lg">
              {user?.first_name} {user?.last_name || ''}
            </h2>
            {user?.username && (
              <p className="text-gray-400">@{user.username}</p>
            )}
            <p className="text-sm text-gray-500">ID: {user?.id}</p>
          </div>
        </div>

        {subscription && (
          <div className="mt-4 pt-4 border-t border-white/10 flex items-center justify-between">
            <div>
              <p className="text-gray-400 text-sm">Текущий тариф</p>
              <p className="font-medium">{subscription.plan_name}</p>
            </div>
            <div className={`px-3 py-1 rounded-full text-sm ${
              subscription.status === 'active' 
                ? 'bg-green-500/20 text-green-400' 
                : 'bg-red-500/20 text-red-400'
            }`}>
              {subscription.status === 'active' ? 'Активен' : 'Неактивен'}
            </div>
          </div>
        )}
      </motion.div>

      {/* Settings List */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="glass rounded-2xl divide-y divide-white/10"
      >
        {/* Language */}
        <button
          onClick={() => setShowLanguageModal(true)}
          className="w-full p-4 flex items-center justify-between"
        >
          <div className="flex items-center gap-3">
            <GlobeAltIcon className="w-5 h-5 text-purple-400" />
            <span>Язык</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-gray-400">
              {currentLanguage?.flag} {currentLanguage?.name}
            </span>
            <ChevronRightIcon className="w-5 h-5 text-gray-500" />
          </div>
        </button>

        {/* Theme */}
        <button
          onClick={() => setShowThemeModal(true)}
          className="w-full p-4 flex items-center justify-between"
        >
          <div className="flex items-center gap-3">
            <SwatchIcon className="w-5 h-5 text-purple-400" />
            <span>Тема оформления</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-gray-400">
              {currentTheme.emoji} {currentTheme.name}
            </span>
            <ChevronRightIcon className="w-5 h-5 text-gray-500" />
          </div>
        </button>

        {/* Notifications */}
        <div className="p-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <BellIcon className="w-5 h-5 text-purple-400" />
            <div>
              <span>Уведомления</span>
              <p className="text-xs text-gray-400">
                Напоминания о продлении
              </p>
            </div>
          </div>
          <button
            onClick={handleNotificationToggle}
            disabled={notificationLoading}
            className={`relative w-12 h-6 rounded-full transition-colors ${
              notifications ? 'bg-green-500' : 'bg-white/20'
            }`}
          >
            <motion.div
              layout
              className="absolute top-1 w-4 h-4 bg-white rounded-full"
              style={{ left: notifications ? '26px' : '4px' }}
            />
          </button>
        </div>
      </motion.div>

      {/* Support & Legal */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
        className="glass rounded-2xl divide-y divide-white/10"
      >
        <button
          onClick={openSupport}
          className="w-full p-4 flex items-center justify-between"
        >
          <div className="flex items-center gap-3">
            <QuestionMarkCircleIcon className="w-5 h-5 text-purple-400" />
            <span>Поддержка</span>
          </div>
          <ChevronRightIcon className="w-5 h-5 text-gray-500" />
        </button>

        <button
          onClick={openPrivacy}
          className="w-full p-4 flex items-center justify-between"
        >
          <div className="flex items-center gap-3">
            <ShieldCheckIcon className="w-5 h-5 text-purple-400" />
            <span>Политика конфиденциальности</span>
          </div>
          <ChevronRightIcon className="w-5 h-5 text-gray-500" />
        </button>

        <button
          onClick={openTerms}
          className="w-full p-4 flex items-center justify-between"
        >
          <div className="flex items-center gap-3">
            <DocumentTextIcon className="w-5 h-5 text-purple-400" />
            <span>Условия использования</span>
          </div>
          <ChevronRightIcon className="w-5 h-5 text-gray-500" />
        </button>
      </motion.div>

      {/* App Info */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.3 }}
        className="text-center pt-4"
      >
        <p className="text-gray-500 text-sm">MetaLib VPN v1.0.0</p>
        <p className="text-gray-600 text-xs mt-1">
          Сделано с ❤️ в России
        </p>
      </motion.div>

      {/* Language Modal */}
      {showLanguageModal && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 bg-black/60 z-50 flex items-end justify-center"
          onClick={() => setShowLanguageModal(false)}
        >
          <motion.div
            initial={{ y: '100%' }}
            animate={{ y: 0 }}
            exit={{ y: '100%' }}
            transition={{ type: 'spring', damping: 25, stiffness: 300 }}
            onClick={(e) => e.stopPropagation()}
            className="w-full max-w-lg glass rounded-t-3xl p-6 safe-area-bottom"
          >
            <div className="w-12 h-1 bg-white/30 rounded-full mx-auto mb-6" />
            
            <h2 className="text-xl font-bold mb-4">Выберите язык</h2>

            <div className="space-y-2">
              {languages.map((lang) => (
                <button
                  key={lang.code}
                  onClick={() => handleLanguageChange(lang.code as 'ru' | 'en' | 'uk')}
                  className={`w-full p-4 rounded-xl flex items-center justify-between transition-colors ${
                    language === lang.code
                      ? 'bg-purple-500/20 border-2 border-purple-500'
                      : 'bg-white/5 border-2 border-transparent hover:bg-white/10'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <span className="text-2xl">{lang.flag}</span>
                    <span className="font-medium">{lang.name}</span>
                  </div>
                  {language === lang.code && (
                    <div className="w-6 h-6 bg-purple-500 rounded-full flex items-center justify-center">
                      <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                      </svg>
                    </div>
                  )}
                </button>
              ))}
            </div>
          </motion.div>
        </motion.div>
      )}

      {/* Theme Modal */}
      {showThemeModal && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 bg-black/60 z-50 flex items-end justify-center"
          onClick={() => setShowThemeModal(false)}
        >
          <motion.div
            initial={{ y: '100%' }}
            animate={{ y: 0 }}
            exit={{ y: '100%' }}
            transition={{ type: 'spring', damping: 25, stiffness: 300 }}
            onClick={(e) => e.stopPropagation()}
            className="w-full max-w-lg glass rounded-t-3xl p-6 safe-area-bottom"
          >
            <div className="w-12 h-1 bg-white/30 rounded-full mx-auto mb-6" />
            
            <h2 className="text-xl font-bold mb-4">Выберите тему</h2>

            <div className="grid grid-cols-2 gap-3">
              {(Object.keys(themes) as ThemeName[]).map((themeName) => {
                const themeInfo = themeLabels[themeName]
                const themeColors = themes[themeName]
                
                return (
                  <button
                    key={themeName}
                    onClick={() => {
                      setTheme(themeName)
                      setShowThemeModal(false)
                      window.Telegram?.WebApp?.HapticFeedback?.selectionChanged()
                    }}
                    className={`p-4 rounded-xl flex flex-col items-center gap-2 transition-all ${
                      theme === themeName
                        ? 'ring-2 ring-[var(--primary)] bg-white/10'
                        : 'bg-white/5 hover:bg-white/10'
                    }`}
                  >
                    {/* Color Preview */}
                    <div className="flex gap-1">
                      <div 
                        className="w-6 h-6 rounded-full" 
                        style={{ backgroundColor: themeColors.primary }}
                      />
                      <div 
                        className="w-6 h-6 rounded-full" 
                        style={{ backgroundColor: themeColors.secondary }}
                      />
                      <div 
                        className="w-6 h-6 rounded-full" 
                        style={{ backgroundColor: themeColors.background }}
                      />
                    </div>
                    <div className="flex items-center gap-1">
                      <span className="text-lg">{themeInfo.emoji}</span>
                      <span className="font-medium text-sm">{themeInfo.name}</span>
                    </div>
                    {theme === themeName && (
                      <div className="w-5 h-5 bg-[var(--primary)] rounded-full flex items-center justify-center">
                        <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                        </svg>
                      </div>
                    )}
                  </button>
                )
              })}
            </div>
          </motion.div>
        </motion.div>
      )}
    </div>
  )
}
