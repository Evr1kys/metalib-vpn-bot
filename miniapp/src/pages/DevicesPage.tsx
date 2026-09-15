import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { 
  DevicePhoneMobileIcon,
  ComputerDesktopIcon,
  DeviceTabletIcon,
  WifiIcon,
  PlusIcon,
  TrashIcon,
  PencilIcon,
  CheckIcon,
  XMarkIcon,
  SignalIcon
} from '@heroicons/react/24/outline'
import { useStore, Device } from '../store'
import { api } from '../api'

const deviceIcons: Record<string, React.ComponentType<{ className?: string }>> = {
  mobile: DevicePhoneMobileIcon,
  desktop: ComputerDesktopIcon,
  tablet: DeviceTabletIcon,
  router: WifiIcon,
  other: DevicePhoneMobileIcon,
}

const deviceTypes = [
  { value: 'mobile', label: 'Телефон', icon: DevicePhoneMobileIcon },
  { value: 'desktop', label: 'Компьютер', icon: ComputerDesktopIcon },
  { value: 'tablet', label: 'Планшет', icon: DeviceTabletIcon },
  { value: 'router', label: 'Роутер', icon: WifiIcon },
]

export default function DevicesPage() {
  const { devices, setDevices, subscription, addDevice, removeDevice } = useStore()
  const [loading, setLoading] = useState(true)
  const [showAddModal, setShowAddModal] = useState(false)
  const [editingDevice, setEditingDevice] = useState<string | null>(null)
  const [editName, setEditName] = useState('')
  const [newDeviceName, setNewDeviceName] = useState('')
  const [newDeviceType, setNewDeviceType] = useState('mobile')
  const [addingDevice, setAddingDevice] = useState(false)
  const [deletingDevice, setDeletingDevice] = useState<string | null>(null)

  useEffect(() => {
    loadDevices()
  }, [])

  const loadDevices = async () => {
    setLoading(true)
    try {
      const response = await api.getDevices()
      if (response.success && response.devices) {
        setDevices(response.devices)
      } else {
        // Mock data
        setDevices([
          {
            id: '1',
            name: 'iPhone 15 Pro',
            type: 'mobile',
            platform: 'iOS',
            last_connected: new Date().toISOString(),
            is_online: true,
            created_at: new Date().toISOString(),
          },
          {
            id: '2',
            name: 'MacBook Pro',
            type: 'desktop',
            platform: 'macOS',
            last_connected: new Date(Date.now() - 3600000).toISOString(),
            is_online: false,
            created_at: new Date().toISOString(),
          },
        ])
      }
    } catch (error) {
      console.error('Failed to load devices:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleAddDevice = async () => {
    if (!newDeviceName.trim()) {
      window.Telegram?.WebApp?.showAlert('Введите название устройства')
      return
    }

    setAddingDevice(true)
    try {
      const response = await api.addDevice(newDeviceName.trim(), newDeviceType)
      if (response.success && response.device) {
        addDevice(response.device)
        setShowAddModal(false)
        setNewDeviceName('')
        setNewDeviceType('mobile')
        window.Telegram?.WebApp?.HapticFeedback?.notificationOccurred('success')
      }
    } catch (error) {
      console.error('Failed to add device:', error)
      window.Telegram?.WebApp?.showAlert('Не удалось добавить устройство')
    } finally {
      setAddingDevice(false)
    }
  }

  const handleRemoveDevice = async (deviceId: string) => {
    window.Telegram?.WebApp?.showConfirm(
      'Вы уверены, что хотите удалить это устройство?',
      async (confirmed) => {
        if (confirmed) {
          setDeletingDevice(deviceId)
          try {
            const response = await api.removeDevice(deviceId)
            if (response.success) {
              removeDevice(deviceId)
              window.Telegram?.WebApp?.HapticFeedback?.notificationOccurred('success')
            }
          } catch (error) {
            console.error('Failed to remove device:', error)
          } finally {
            setDeletingDevice(null)
          }
        }
      }
    )
  }

  const handleEditDevice = async (deviceId: string) => {
    if (!editName.trim()) {
      setEditingDevice(null)
      return
    }

    try {
      const response = await api.renameDevice(deviceId, editName.trim())
      if (response.success) {
        setDevices(
          devices.map((d) =>
            d.id === deviceId ? { ...d, name: editName.trim() } : d
          )
        )
        window.Telegram?.WebApp?.HapticFeedback?.notificationOccurred('success')
      }
    } catch (error) {
      console.error('Failed to rename device:', error)
    } finally {
      setEditingDevice(null)
      setEditName('')
    }
  }

  const startEditing = (device: Device) => {
    setEditingDevice(device.id)
    setEditName(device.name)
  }

  const formatLastConnected = (dateStr: string | null) => {
    if (!dateStr) return 'Никогда'
    
    const date = new Date(dateStr)
    const now = new Date()
    const diff = now.getTime() - date.getTime()
    
    if (diff < 60000) return 'Только что'
    if (diff < 3600000) return `${Math.floor(diff / 60000)} мин назад`
    if (diff < 86400000) return `${Math.floor(diff / 3600000)} ч назад`
    
    return date.toLocaleDateString('ru-RU', {
      day: 'numeric',
      month: 'short',
    })
  }

  const maxDevices = subscription?.max_devices || 3
  const canAddDevice = devices.length < maxDevices

  if (loading) {
    return (
      <div className="p-4 space-y-4">
        <div className="h-8 bg-white/10 rounded w-1/2 animate-pulse" />
        {[1, 2].map((i) => (
          <div key={i} className="glass rounded-2xl p-4 animate-pulse">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 bg-white/10 rounded-xl" />
              <div className="flex-1 space-y-2">
                <div className="h-5 bg-white/10 rounded w-1/2" />
                <div className="h-4 bg-white/10 rounded w-1/3" />
              </div>
            </div>
          </div>
        ))}
      </div>
    )
  }

  return (
    <div className="p-4 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold">Мои устройства</h1>
          <p className="text-gray-400 text-sm">
            {devices.length} из {maxDevices} устройств
          </p>
        </div>
        {canAddDevice && (
          <button
            onClick={() => setShowAddModal(true)}
            className="p-2 bg-purple-500 rounded-xl hover:bg-purple-600 transition-colors"
          >
            <PlusIcon className="w-6 h-6" />
          </button>
        )}
      </div>

      {/* Devices List */}
      <AnimatePresence>
        {devices.map((device, index) => {
          const Icon = deviceIcons[device.type] || DevicePhoneMobileIcon

          return (
            <motion.div
              key={device.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, x: -100 }}
              transition={{ delay: index * 0.1 }}
              className="glass rounded-2xl p-4"
            >
              <div className="flex items-center gap-4">
                <div className={`p-3 rounded-xl ${
                  device.is_online 
                    ? 'bg-green-500/20' 
                    : 'bg-white/10'
                }`}>
                  <Icon className={`w-6 h-6 ${
                    device.is_online ? 'text-green-400' : 'text-gray-400'
                  }`} />
                </div>

                <div className="flex-1 min-w-0">
                  {editingDevice === device.id ? (
                    <div className="flex items-center gap-2">
                      <input
                        type="text"
                        value={editName}
                        onChange={(e) => setEditName(e.target.value)}
                        className="input-field flex-1"
                        autoFocus
                        onKeyDown={(e) => {
                          if (e.key === 'Enter') handleEditDevice(device.id)
                          if (e.key === 'Escape') setEditingDevice(null)
                        }}
                      />
                      <button
                        onClick={() => handleEditDevice(device.id)}
                        className="p-2 bg-green-500/20 rounded-lg"
                      >
                        <CheckIcon className="w-4 h-4 text-green-400" />
                      </button>
                      <button
                        onClick={() => setEditingDevice(null)}
                        className="p-2 bg-red-500/20 rounded-lg"
                      >
                        <XMarkIcon className="w-4 h-4 text-red-400" />
                      </button>
                    </div>
                  ) : (
                    <>
                      <h3 className="font-medium truncate">{device.name}</h3>
                      <div className="flex items-center gap-2 text-sm text-gray-400">
                        <span>{device.platform}</span>
                        <span>•</span>
                        <span className="flex items-center gap-1">
                          {device.is_online ? (
                            <>
                              <SignalIcon className="w-3 h-3 text-green-400" />
                              Онлайн
                            </>
                          ) : (
                            formatLastConnected(device.last_connected)
                          )}
                        </span>
                      </div>
                    </>
                  )}
                </div>

                {editingDevice !== device.id && (
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => startEditing(device)}
                      className="p-2 bg-white/10 rounded-lg hover:bg-white/20 transition-colors"
                    >
                      <PencilIcon className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => handleRemoveDevice(device.id)}
                      disabled={deletingDevice === device.id}
                      className="p-2 bg-red-500/20 rounded-lg hover:bg-red-500/30 transition-colors"
                    >
                      {deletingDevice === device.id ? (
                        <div className="w-4 h-4 border-2 border-red-400/30 border-t-red-400 rounded-full animate-spin" />
                      ) : (
                        <TrashIcon className="w-4 h-4 text-red-400" />
                      )}
                    </button>
                  </div>
                )}
              </div>
            </motion.div>
          )
        })}
      </AnimatePresence>

      {/* Empty State */}
      {devices.length === 0 && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="glass rounded-2xl p-8 text-center"
        >
          <div className="w-16 h-16 mx-auto bg-purple-500/20 rounded-2xl flex items-center justify-center mb-4">
            <DevicePhoneMobileIcon className="w-8 h-8 text-purple-400" />
          </div>
          <h3 className="font-bold text-lg mb-2">Нет устройств</h3>
          <p className="text-gray-400 text-sm mb-4">
            Добавьте устройство, чтобы использовать VPN
          </p>
          <button
            onClick={() => setShowAddModal(true)}
            className="btn-primary"
          >
            Добавить устройство
          </button>
        </motion.div>
      )}

      {/* Limit Warning */}
      {!canAddDevice && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-yellow-500/10 border border-yellow-500/30 rounded-2xl p-4 flex items-center gap-3"
        >
          <div className="p-2 bg-yellow-500/20 rounded-xl">
            <DevicePhoneMobileIcon className="w-5 h-5 text-yellow-400" />
          </div>
          <div className="flex-1">
            <p className="text-sm">
              Достигнут лимит устройств. Удалите устройство или{' '}
              <span className="text-purple-400">улучшите тариф</span>.
            </p>
          </div>
        </motion.div>
      )}

      {/* Add Device Modal */}
      <AnimatePresence>
        {showAddModal && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/60 z-50 flex items-end justify-center"
            onClick={() => setShowAddModal(false)}
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
              
              <h2 className="text-xl font-bold mb-6">Добавить устройство</h2>

              <div className="space-y-4">
                <div>
                  <label className="block text-sm text-gray-400 mb-2">
                    Название
                  </label>
                  <input
                    type="text"
                    value={newDeviceName}
                    onChange={(e) => setNewDeviceName(e.target.value)}
                    placeholder="Например: Мой iPhone"
                    className="input-field w-full"
                  />
                </div>

                <div>
                  <label className="block text-sm text-gray-400 mb-2">
                    Тип устройства
                  </label>
                  <div className="grid grid-cols-4 gap-2">
                    {deviceTypes.map(({ value, label, icon: Icon }) => (
                      <button
                        key={value}
                        onClick={() => setNewDeviceType(value)}
                        className={`p-3 rounded-xl flex flex-col items-center gap-2 transition-colors ${
                          newDeviceType === value
                            ? 'bg-purple-500 text-white'
                            : 'bg-white/10 text-gray-400 hover:bg-white/20'
                        }`}
                      >
                        <Icon className="w-6 h-6" />
                        <span className="text-xs">{label}</span>
                      </button>
                    ))}
                  </div>
                </div>

                <button
                  onClick={handleAddDevice}
                  disabled={addingDevice || !newDeviceName.trim()}
                  className="w-full btn-primary disabled:opacity-50"
                >
                  {addingDevice ? (
                    <div className="flex items-center justify-center gap-2">
                      <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                      Добавление...
                    </div>
                  ) : (
                    'Добавить'
                  )}
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
