import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { 
  SignalIcon,
  CheckIcon,
  GlobeAltIcon,
  BoltIcon,
  StarIcon,
  MagnifyingGlassIcon
} from '@heroicons/react/24/outline'
import { useStore, Server } from '../store'
import { api } from '../api'

const flagEmojis: Record<string, string> = {
  'NL': '🇳🇱',
  'DE': '🇩🇪',
  'US': '🇺🇸',
  'GB': '🇬🇧',
  'FR': '🇫🇷',
  'JP': '🇯🇵',
  'SG': '🇸🇬',
  'AU': '🇦🇺',
  'CA': '🇨🇦',
  'CH': '🇨🇭',
  'SE': '🇸🇪',
  'FI': '🇫🇮',
  'RU': '🇷🇺',
  'KZ': '🇰🇿',
  'TR': '🇹🇷',
}

const getPingColor = (ping: number) => {
  if (ping < 50) return 'text-green-400'
  if (ping < 100) return 'text-yellow-400'
  return 'text-red-400'
}

const getLoadColor = (load: number) => {
  if (load < 50) return 'bg-green-500'
  if (load < 80) return 'bg-yellow-500'
  return 'bg-red-500'
}

export default function ServersPage() {
  const { servers, setServers, selectedServer, setSelectedServer, subscription } = useStore()
  const [loading, setLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  const [connecting, setConnecting] = useState<string | null>(null)

  useEffect(() => {
    loadServers()
  }, [])

  const loadServers = async () => {
    setLoading(true)
    try {
      const response = await api.getServers()
      if (response.success && response.servers) {
        setServers(response.servers)
      } else {
        // Mock data
        setServers([
          { id: '1', name: 'Amsterdam 1', country: 'NL', city: 'Amsterdam', flag: '🇳🇱', load: 35, ping: 28, is_premium: false, protocols: ['VLESS', 'VMess'] },
          { id: '2', name: 'Frankfurt', country: 'DE', city: 'Frankfurt', flag: '🇩🇪', load: 42, ping: 32, is_premium: false, protocols: ['VLESS'] },
          { id: '3', name: 'New York', country: 'US', city: 'New York', flag: '🇺🇸', load: 68, ping: 120, is_premium: false, protocols: ['VLESS', 'VMess'] },
          { id: '4', name: 'London', country: 'GB', city: 'London', flag: '🇬🇧', load: 55, ping: 45, is_premium: false, protocols: ['VLESS'] },
          { id: '5', name: 'Tokyo', country: 'JP', city: 'Tokyo', flag: '🇯🇵', load: 25, ping: 85, is_premium: true, protocols: ['VLESS', 'Trojan'] },
          { id: '6', name: 'Singapore', country: 'SG', city: 'Singapore', flag: '🇸🇬', load: 30, ping: 75, is_premium: true, protocols: ['VLESS'] },
          { id: '7', name: 'Paris', country: 'FR', city: 'Paris', flag: '🇫🇷', load: 48, ping: 38, is_premium: false, protocols: ['VLESS'] },
          { id: '8', name: 'Sydney', country: 'AU', city: 'Sydney', flag: '🇦🇺', load: 22, ping: 180, is_premium: true, protocols: ['VLESS'] },
        ])
      }
    } catch (error) {
      console.error('Failed to load servers:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleSelectServer = async (server: Server) => {
    if (server.is_premium && subscription?.plan_name === 'Старт') {
      window.Telegram?.WebApp?.showPopup({
        title: 'Премиум сервер',
        message: 'Этот сервер доступен только на тарифах Про и выше',
        buttons: [
          { id: 'upgrade', type: 'default', text: 'Улучшить тариф' },
          { id: 'cancel', type: 'cancel' },
        ],
      }, (buttonId) => {
        if (buttonId === 'upgrade') {
          // Navigate to subscription page
        }
      })
      return
    }

    setConnecting(server.id)
    window.Telegram?.WebApp?.HapticFeedback?.impactOccurred('medium')

    try {
      // Get VPN key for selected server
      const response = await api.getVpnKey(server.id)
      if (response.success) {
        setSelectedServer(server)
        window.Telegram?.WebApp?.HapticFeedback?.notificationOccurred('success')
      }
    } catch (error) {
      console.error('Failed to connect to server:', error)
    } finally {
      setConnecting(null)
    }
  }

  const filteredServers = servers.filter((server) => {
    const query = searchQuery.toLowerCase()
    return (
      server.name.toLowerCase().includes(query) ||
      server.country.toLowerCase().includes(query) ||
      server.city.toLowerCase().includes(query)
    )
  })

  // Sort: selected first, then by ping
  const sortedServers = [...filteredServers].sort((a, b) => {
    if (a.id === selectedServer?.id) return -1
    if (b.id === selectedServer?.id) return 1
    return a.ping - b.ping
  })

  if (loading) {
    return (
      <div className="p-4 space-y-4">
        <div className="h-12 bg-white/10 rounded-xl animate-pulse" />
        {[1, 2, 3, 4].map((i) => (
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
      <div>
        <h1 className="text-xl font-bold">Серверы</h1>
        <p className="text-gray-400 text-sm">
          {servers.length} серверов в {new Set(servers.map(s => s.country)).size} странах
        </p>
      </div>

      {/* Search */}
      <div className="relative">
        <MagnifyingGlassIcon className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="Поиск по стране или городу"
          className="input-field w-full pl-12"
        />
      </div>

      {/* Selected Server */}
      {selectedServer && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="gradient-purple rounded-2xl p-4"
        >
          <div className="flex items-center gap-3 mb-3">
            <div className="text-2xl">
              {flagEmojis[selectedServer.country] || '🌍'}
            </div>
            <div className="flex-1">
              <h3 className="font-bold">{selectedServer.name}</h3>
              <p className="text-white/70 text-sm">{selectedServer.city}</p>
            </div>
            <div className="flex items-center gap-1 px-3 py-1 bg-white/20 rounded-full">
              <CheckIcon className="w-4 h-4 text-green-400" />
              <span className="text-sm">Подключено</span>
            </div>
          </div>
          <div className="flex items-center gap-4 text-sm text-white/70">
            <div className="flex items-center gap-1">
              <SignalIcon className="w-4 h-4" />
              <span>{selectedServer.ping} мс</span>
            </div>
            <div className="flex items-center gap-1">
              <BoltIcon className="w-4 h-4" />
              <span>{selectedServer.protocols.join(', ')}</span>
            </div>
          </div>
        </motion.div>
      )}

      {/* Servers List */}
      <div className="space-y-3">
        {sortedServers.map((server, index) => {
          const isSelected = server.id === selectedServer?.id
          const isConnecting = connecting === server.id

          return (
            <motion.button
              key={server.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.05 }}
              onClick={() => handleSelectServer(server)}
              disabled={isConnecting || isSelected}
              className={`w-full glass rounded-2xl p-4 text-left transition-all ${
                isSelected 
                  ? 'border-2 border-purple-500 opacity-50' 
                  : 'border-2 border-transparent hover:border-white/20'
              }`}
            >
              <div className="flex items-center gap-4">
                <div className="relative">
                  <div className="text-3xl">
                    {flagEmojis[server.country] || server.flag}
                  </div>
                  {server.is_premium && (
                    <div className="absolute -top-1 -right-1 p-1 bg-yellow-500 rounded-full">
                      <StarIcon className="w-2 h-2 text-yellow-900" />
                    </div>
                  )}
                </div>

                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <h3 className="font-medium truncate">{server.name}</h3>
                    {server.is_premium && (
                      <span className="px-2 py-0.5 bg-yellow-500/20 text-yellow-400 text-xs rounded-full">
                        Premium
                      </span>
                    )}
                  </div>
                  <p className="text-gray-400 text-sm">{server.city}</p>
                </div>

                <div className="flex flex-col items-end gap-1">
                  {isConnecting ? (
                    <div className="w-5 h-5 border-2 border-purple-400/30 border-t-purple-400 rounded-full animate-spin" />
                  ) : (
                    <>
                      <div className={`flex items-center gap-1 text-sm ${getPingColor(server.ping)}`}>
                        <SignalIcon className="w-4 h-4" />
                        <span>{server.ping} мс</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <div className="w-16 h-1.5 bg-white/10 rounded-full overflow-hidden">
                          <div
                            className={`h-full ${getLoadColor(server.load)}`}
                            style={{ width: `${server.load}%` }}
                          />
                        </div>
                        <span className="text-xs text-gray-400">{server.load}%</span>
                      </div>
                    </>
                  )}
                </div>
              </div>
            </motion.button>
          )
        })}
      </div>

      {/* Empty Search */}
      {filteredServers.length === 0 && (
        <div className="text-center py-8">
          <GlobeAltIcon className="w-12 h-12 text-gray-500 mx-auto mb-4" />
          <p className="text-gray-400">Серверы не найдены</p>
          <button
            onClick={() => setSearchQuery('')}
            className="text-purple-400 text-sm mt-2"
          >
            Сбросить поиск
          </button>
        </div>
      )}

      {/* Legend */}
      <div className="glass rounded-2xl p-4">
        <h4 className="font-medium mb-3">Условные обозначения</h4>
        <div className="grid grid-cols-2 gap-3 text-sm">
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 bg-green-500 rounded-full" />
            <span className="text-gray-400">Низкая нагрузка</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 bg-yellow-500 rounded-full" />
            <span className="text-gray-400">Средняя нагрузка</span>
          </div>
          <div className="flex items-center gap-2">
            <SignalIcon className="w-4 h-4 text-green-400" />
            <span className="text-gray-400">Быстрый пинг</span>
          </div>
          <div className="flex items-center gap-2">
            <StarIcon className="w-4 h-4 text-yellow-400" />
            <span className="text-gray-400">Premium сервер</span>
          </div>
        </div>
      </div>
    </div>
  )
}
