'use client'

import { useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/lib/api'
import toast from 'react-hot-toast'
import { 
  FiSettings, FiServer, FiDollarSign, FiShield, FiSave, FiRefreshCw, 
  FiDatabase, FiDownload, FiTrash2, FiAlertTriangle, FiCheck, FiX,
  FiCopy, FiKey, FiUser, FiGlobe, FiMail, FiLock, FiZap, FiBell
} from 'react-icons/fi'

export default function SettingsPage() {
  const queryClient = useQueryClient()
  const [saving, setSaving] = useState(false)
  const [showDangerZone, setShowDangerZone] = useState(false)
  const [confirmDelete, setConfirmDelete] = useState('')
  
  const [settings, setSettings] = useState({
    // Bot Settings
    allowRegistration: true,
    enableReferrals: true,
    maintenanceMode: false,
    welcomeMessage: 'Добро пожаловать в MetaLib VPN! 🚀',
    
    // Payment Settings
    defaultCurrency: 'RUB',
    referralPercent: 10,
    minWithdraw: 500,
    autoActivation: true,
    
    // VPN Settings
    trialDays: 3,
    maxDevices: 5,
    defaultProtocol: 'vless',
    autoSelectServer: true,
    
    // Notifications
    notifyNewUsers: true,
    notifyPayments: true,
    notifyErrors: true,
    
    // Security
    adminNotifyIp: true,
    requireEmailVerify: false,
    twoFactorEnabled: false,
  })

  const handleSave = async () => {
    setSaving(true)
    try {
      // TODO: Save settings to backend
      await new Promise(resolve => setTimeout(resolve, 1000))
      toast.success('Настройки сохранены!')
    } catch (error) {
      toast.error('Ошибка сохранения')
    } finally {
      setSaving(false)
    }
  }

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text)
    toast.success('Скопировано в буфер обмена')
  }

  const handleExportData = async (type: 'users' | 'payments' | 'all') => {
    toast.success(`Экспорт ${type} начат...`)
  }

  const handleClearCache = () => {
    queryClient.invalidateQueries()
    toast.success('Кэш очищен')
  }

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold gradient-text">Настройки системы</h1>
          <p className="mt-2 text-gray-400">Управление конфигурацией и параметрами</p>
        </div>
        <div className="flex space-x-3">
          <button
            onClick={handleClearCache}
            className="flex items-center px-4 py-2 rounded-xl bg-[#1a1a2e] border border-purple-500/20 text-gray-400 hover:text-white transition-colors"
          >
            <FiRefreshCw className="mr-2" />
            Очистить кэш
          </button>
          <button
            onClick={handleSave}
            disabled={saving}
            className="btn-gradient px-6 py-2 rounded-xl flex items-center"
          >
            {saving ? (
              <FiRefreshCw className="mr-2 animate-spin" />
            ) : (
              <FiSave className="mr-2" />
            )}
            Сохранить все
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* API & Integrations */}
        <div className="dark-card p-6">
          <div className="flex items-center space-x-3 mb-6">
            <div className="p-3 rounded-xl bg-gradient-to-br from-purple-500 to-pink-500">
              <FiShield className="w-6 h-6 text-white" />
            </div>
            <h2 className="text-xl font-semibold text-white">API и интеграции</h2>
          </div>
          
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Telegram Bot Token
              </label>
              <div className="flex space-x-2">
                <input
                  type="password"
                  value="••••••••••••••••••••••••••••••••••••"
                  disabled
                  className="flex-1 h-11 px-4 py-2 bg-[#1a1a2e] border border-purple-500/20 rounded-xl text-gray-500"
                />
                <button 
                  onClick={() => copyToClipboard('bot_token')}
                  className="p-3 rounded-xl bg-[#1a1a2e] border border-purple-500/20 text-gray-400 hover:text-purple-400 transition-colors"
                >
                  <FiCopy />
                </button>
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Platega Merchant ID
              </label>
              <div className="flex space-x-2">
                <input
                  type="text"
                  value="d79b214f-40d4-40a9-b624-0a613c89cd4b"
                  disabled
                  className="flex-1 h-11 px-4 py-2 bg-[#1a1a2e] border border-purple-500/20 rounded-xl text-gray-400 font-mono text-sm"
                />
                <button 
                  onClick={() => copyToClipboard('d79b214f-40d4-40a9-b624-0a613c89cd4b')}
                  className="p-3 rounded-xl bg-[#1a1a2e] border border-purple-500/20 text-gray-400 hover:text-purple-400 transition-colors"
                >
                  <FiCopy />
                </button>
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Webhook URL
              </label>
              <div className="flex space-x-2">
                <input
                  type="text"
                  value="https://panel.metalib.xyz/api/v1/webhooks/platega"
                  disabled
                  className="flex-1 h-11 px-4 py-2 bg-[#1a1a2e] border border-purple-500/20 rounded-xl text-gray-400 font-mono text-sm"
                />
                <button 
                  onClick={() => copyToClipboard('https://panel.metalib.xyz/api/v1/webhooks/platega')}
                  className="p-3 rounded-xl bg-[#1a1a2e] border border-purple-500/20 text-gray-400 hover:text-purple-400 transition-colors"
                >
                  <FiCopy />
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Bot Settings */}
        <div className="dark-card p-6">
          <div className="flex items-center space-x-3 mb-6">
            <div className="p-3 rounded-xl bg-gradient-to-br from-blue-500 to-cyan-500">
              <FiSettings className="w-6 h-6 text-white" />
            </div>
            <h2 className="text-xl font-semibold text-white">Настройки бота</h2>
          </div>
          
          <div className="space-y-4">
            <ToggleSwitch
              checked={settings.allowRegistration}
              onChange={(v) => setSettings({...settings, allowRegistration: v})}
              label="Разрешить регистрацию новых пользователей"
            />

            <ToggleSwitch
              checked={settings.enableReferrals}
              onChange={(v) => setSettings({...settings, enableReferrals: v})}
              label="Включить реферальную систему"
            />

            <ToggleSwitch
              checked={settings.maintenanceMode}
              onChange={(v) => setSettings({...settings, maintenanceMode: v})}
              label="Режим обслуживания"
              color="orange"
            />

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Приветственное сообщение
              </label>
              <textarea
                value={settings.welcomeMessage}
                onChange={(e) => setSettings({...settings, welcomeMessage: e.target.value})}
                rows={3}
                className="w-full px-4 py-3 bg-[#1a1a2e] border border-purple-500/20 rounded-xl text-white focus:outline-none focus:ring-2 focus:ring-purple-500 resize-none"
              />
            </div>
          </div>
        </div>

        {/* Payment Settings */}
        <div className="dark-card p-6">
          <div className="flex items-center space-x-3 mb-6">
            <div className="p-3 rounded-xl bg-gradient-to-br from-green-500 to-emerald-500">
              <FiDollarSign className="w-6 h-6 text-white" />
            </div>
            <h2 className="text-xl font-semibold text-white">Платежи</h2>
          </div>
          
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Валюта по умолчанию
              </label>
              <select 
                value={settings.defaultCurrency}
                onChange={(e) => setSettings({...settings, defaultCurrency: e.target.value})}
                className="w-full h-11 px-4 py-2 bg-[#1a1a2e] border border-purple-500/20 rounded-xl text-white focus:outline-none focus:ring-2 focus:ring-purple-500"
              >
                <option value="RUB">RUB (₽)</option>
                <option value="USD">USD ($)</option>
                <option value="EUR">EUR (€)</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Реферальный процент (%)
              </label>
              <input
                type="number"
                value={settings.referralPercent}
                onChange={(e) => setSettings({...settings, referralPercent: parseInt(e.target.value)})}
                className="w-full h-11 px-4 py-2 bg-[#1a1a2e] border border-purple-500/20 rounded-xl text-white focus:outline-none focus:ring-2 focus:ring-purple-500"
              />
              <p className="text-xs text-gray-500 mt-1">
                Процент от платежа, который получает реферер
              </p>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Минимальная сумма вывода (₽)
              </label>
              <input
                type="number"
                value={settings.minWithdraw}
                onChange={(e) => setSettings({...settings, minWithdraw: parseInt(e.target.value)})}
                className="w-full h-11 px-4 py-2 bg-[#1a1a2e] border border-purple-500/20 rounded-xl text-white focus:outline-none focus:ring-2 focus:ring-purple-500"
              />
            </div>

            <ToggleSwitch
              checked={settings.autoActivation}
              onChange={(v) => setSettings({...settings, autoActivation: v})}
              label="Автоматическая активация подписки после оплаты"
            />
          </div>
        </div>

        {/* VPN Settings */}
        <div className="dark-card p-6">
          <div className="flex items-center space-x-3 mb-6">
            <div className="p-3 rounded-xl bg-gradient-to-br from-orange-500 to-red-500">
              <FiServer className="w-6 h-6 text-white" />
            </div>
            <h2 className="text-xl font-semibold text-white">VPN настройки</h2>
          </div>
          
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Пробный период (дней)
              </label>
              <input
                type="number"
                value={settings.trialDays}
                onChange={(e) => setSettings({...settings, trialDays: parseInt(e.target.value)})}
                className="w-full h-11 px-4 py-2 bg-[#1a1a2e] border border-purple-500/20 rounded-xl text-white focus:outline-none focus:ring-2 focus:ring-purple-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Максимум устройств на аккаунт
              </label>
              <input
                type="number"
                value={settings.maxDevices}
                onChange={(e) => setSettings({...settings, maxDevices: parseInt(e.target.value)})}
                className="w-full h-11 px-4 py-2 bg-[#1a1a2e] border border-purple-500/20 rounded-xl text-white focus:outline-none focus:ring-2 focus:ring-purple-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                VPN протокол по умолчанию
              </label>
              <select 
                value={settings.defaultProtocol}
                onChange={(e) => setSettings({...settings, defaultProtocol: e.target.value})}
                className="w-full h-11 px-4 py-2 bg-[#1a1a2e] border border-purple-500/20 rounded-xl text-white focus:outline-none focus:ring-2 focus:ring-purple-500"
              >
                <option value="vless">VLESS + Reality</option>
                <option value="wireguard">WireGuard</option>
                <option value="amnezia">AmneziaWG</option>
              </select>
            </div>

            <ToggleSwitch
              checked={settings.autoSelectServer}
              onChange={(v) => setSettings({...settings, autoSelectServer: v})}
              label="Автовыбор лучшего сервера"
            />
          </div>
        </div>

        {/* Notifications */}
        <div className="dark-card p-6">
          <div className="flex items-center space-x-3 mb-6">
            <div className="p-3 rounded-xl bg-gradient-to-br from-pink-500 to-rose-500">
              <FiBell className="w-6 h-6 text-white" />
            </div>
            <h2 className="text-xl font-semibold text-white">Уведомления админа</h2>
          </div>
          
          <div className="space-y-4">
            <ToggleSwitch
              checked={settings.notifyNewUsers}
              onChange={(v) => setSettings({...settings, notifyNewUsers: v})}
              label="Уведомлять о новых пользователях"
            />

            <ToggleSwitch
              checked={settings.notifyPayments}
              onChange={(v) => setSettings({...settings, notifyPayments: v})}
              label="Уведомлять об оплатах"
            />

            <ToggleSwitch
              checked={settings.notifyErrors}
              onChange={(v) => setSettings({...settings, notifyErrors: v})}
              label="Уведомлять об ошибках"
              color="red"
            />
          </div>
        </div>

        {/* Security */}
        <div className="dark-card p-6">
          <div className="flex items-center space-x-3 mb-6">
            <div className="p-3 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-500">
              <FiLock className="w-6 h-6 text-white" />
            </div>
            <h2 className="text-xl font-semibold text-white">Безопасность</h2>
          </div>
          
          <div className="space-y-4">
            <ToggleSwitch
              checked={settings.adminNotifyIp}
              onChange={(v) => setSettings({...settings, adminNotifyIp: v})}
              label="Уведомлять о входе с нового IP"
            />

            <ToggleSwitch
              checked={settings.twoFactorEnabled}
              onChange={(v) => setSettings({...settings, twoFactorEnabled: v})}
              label="Двухфакторная аутентификация (2FA)"
            />

            <ToggleSwitch
              checked={settings.requireEmailVerify}
              onChange={(v) => setSettings({...settings, requireEmailVerify: v})}
              label="Требовать верификацию email"
            />
          </div>
        </div>

        {/* Export Data */}
        <div className="dark-card p-6">
          <div className="flex items-center space-x-3 mb-6">
            <div className="p-3 rounded-xl bg-gradient-to-br from-cyan-500 to-blue-500">
              <FiDatabase className="w-6 h-6 text-white" />
            </div>
            <h2 className="text-xl font-semibold text-white">Экспорт данных</h2>
          </div>
          
          <div className="space-y-3">
            <button 
              onClick={() => handleExportData('users')}
              className="w-full flex items-center justify-between p-4 rounded-xl bg-[#1a1a2e] hover:bg-[#252542] border border-purple-500/10 transition-colors"
            >
              <div className="flex items-center space-x-3">
                <FiUser className="text-blue-400" />
                <span className="text-white">Экспорт пользователей</span>
              </div>
              <FiDownload className="text-gray-400" />
            </button>

            <button 
              onClick={() => handleExportData('payments')}
              className="w-full flex items-center justify-between p-4 rounded-xl bg-[#1a1a2e] hover:bg-[#252542] border border-purple-500/10 transition-colors"
            >
              <div className="flex items-center space-x-3">
                <FiDollarSign className="text-green-400" />
                <span className="text-white">Экспорт платежей</span>
              </div>
              <FiDownload className="text-gray-400" />
            </button>

            <button 
              onClick={() => handleExportData('all')}
              className="w-full flex items-center justify-between p-4 rounded-xl bg-[#1a1a2e] hover:bg-[#252542] border border-purple-500/10 transition-colors"
            >
              <div className="flex items-center space-x-3">
                <FiDatabase className="text-purple-400" />
                <span className="text-white">Полный экспорт системы</span>
              </div>
              <FiDownload className="text-gray-400" />
            </button>
          </div>
        </div>

        {/* Danger Zone */}
        <div className="dark-card p-6 border border-red-500/30">
          <div className="flex items-center space-x-3 mb-6">
            <div className="p-3 rounded-xl bg-gradient-to-br from-red-500 to-orange-500">
              <FiAlertTriangle className="w-6 h-6 text-white" />
            </div>
            <h2 className="text-xl font-semibold text-white">Опасная зона</h2>
          </div>

          {!showDangerZone ? (
            <button
              onClick={() => setShowDangerZone(true)}
              className="w-full p-4 rounded-xl bg-red-500/10 border border-red-500/30 text-red-400 hover:bg-red-500/20 transition-colors"
            >
              Показать опасные действия
            </button>
          ) : (
            <div className="space-y-4">
              <p className="text-gray-400 text-sm">
                ⚠️ Эти действия необратимы. Будьте осторожны.
              </p>

              <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/20">
                <h4 className="text-red-400 font-medium mb-2">Очистить все VPN аккаунты</h4>
                <p className="text-sm text-gray-500 mb-3">
                  Удалит все VPN конфигурации пользователей. Подписки останутся.
                </p>
                <button className="px-4 py-2 rounded-lg bg-red-500/20 text-red-400 hover:bg-red-500/30 transition-colors text-sm">
                  Очистить VPN
                </button>
              </div>

              <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/20">
                <h4 className="text-red-400 font-medium mb-2">Сбросить статистику</h4>
                <p className="text-sm text-gray-500 mb-3">
                  Обнулит всю статистику использования и трафика.
                </p>
                <button className="px-4 py-2 rounded-lg bg-red-500/20 text-red-400 hover:bg-red-500/30 transition-colors text-sm">
                  Сбросить статистику
                </button>
              </div>

              <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/20">
                <h4 className="text-red-400 font-medium mb-2">Удалить все данные</h4>
                <p className="text-sm text-gray-500 mb-3">
                  Полная очистка базы данных. Введите "DELETE ALL" для подтверждения.
                </p>
                <div className="flex space-x-2">
                  <input
                    type="text"
                    value={confirmDelete}
                    onChange={(e) => setConfirmDelete(e.target.value)}
                    placeholder="DELETE ALL"
                    className="flex-1 px-4 py-2 bg-[#1a1a2e] border border-red-500/30 rounded-lg text-white focus:outline-none"
                  />
                  <button 
                    disabled={confirmDelete !== 'DELETE ALL'}
                    className="px-4 py-2 rounded-lg bg-red-500 text-white disabled:opacity-30 disabled:cursor-not-allowed hover:bg-red-600 transition-colors text-sm"
                  >
                    Удалить
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function ToggleSwitch({ 
  checked, 
  onChange, 
  label,
  color = 'purple' 
}: { 
  checked: boolean
  onChange: (value: boolean) => void
  label: string
  color?: 'purple' | 'green' | 'orange' | 'red'
}) {
  const colors = {
    purple: 'peer-checked:bg-purple-500',
    green: 'peer-checked:bg-green-500',
    orange: 'peer-checked:bg-orange-500',
    red: 'peer-checked:bg-red-500',
  }

  return (
    <label className="flex items-center space-x-3 cursor-pointer group">
      <div className="relative">
        <input 
          type="checkbox" 
          checked={checked}
          onChange={(e) => onChange(e.target.checked)}
          className="sr-only peer" 
        />
        <div className={`w-11 h-6 bg-[#1a1a2e] rounded-full peer ${colors[color]} transition-colors`}></div>
        <div className="absolute left-1 top-1 w-4 h-4 bg-gray-400 rounded-full peer-checked:translate-x-5 peer-checked:bg-white transition-transform"></div>
      </div>
      <span className="text-sm text-gray-300 group-hover:text-white transition-colors">
        {label}
      </span>
    </label>
  )
}
