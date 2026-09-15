import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export interface TelegramUser {
  id: number
  first_name: string
  last_name?: string
  username?: string
  language_code?: string
}

export interface Subscription {
  id: string
  plan_name: string
  status: 'active' | 'expired' | 'cancelled' | 'pending'
  expires_at: string
  auto_renew: boolean
  days_left: number
  traffic_used: number
  traffic_limit: number
  devices_count: number
  max_devices: number
}

export interface Device {
  id: string
  name: string
  type: 'desktop' | 'mobile' | 'router' | 'other'
  platform: string
  last_connected: string | null
  is_online: boolean
  created_at: string
}

export interface Server {
  id: string
  name: string
  country: string
  city: string
  flag: string
  load: number
  ping: number
  is_premium: boolean
  protocols: string[]
}

export interface ReferralStats {
  total_referrals: number
  active_referrals: number
  total_earned: number
  pending_earnings: number
  referral_code: string
  referral_link: string
}

interface AppState {
  // User
  user: TelegramUser | null
  setUser: (user: TelegramUser | null) => void
  
  // Subscription
  subscription: Subscription | null
  setSubscription: (subscription: Subscription | null) => void
  
  // Devices
  devices: Device[]
  setDevices: (devices: Device[]) => void
  addDevice: (device: Device) => void
  removeDevice: (deviceId: string) => void
  
  // Servers
  servers: Server[]
  setServers: (servers: Server[]) => void
  selectedServer: Server | null
  setSelectedServer: (server: Server | null) => void
  
  // Referral
  referralStats: ReferralStats | null
  setReferralStats: (stats: ReferralStats | null) => void
  
  // UI State
  isLoading: boolean
  setLoading: (loading: boolean) => void
  
  // Settings
  language: 'ru' | 'en' | 'uk'
  setLanguage: (lang: 'ru' | 'en' | 'uk') => void
  
  notifications: boolean
  setNotifications: (enabled: boolean) => void
  
  // VPN Key
  vpnKey: string | null
  setVpnKey: (key: string | null) => void
}

export const useStore = create<AppState>()(
  persist(
    (set) => ({
      // User
      user: null,
      setUser: (user) => set({ user }),
      
      // Subscription
      subscription: null,
      setSubscription: (subscription) => set({ subscription }),
      
      // Devices
      devices: [],
      setDevices: (devices) => set({ devices }),
      addDevice: (device) => set((state) => ({ 
        devices: [...state.devices, device] 
      })),
      removeDevice: (deviceId) => set((state) => ({ 
        devices: state.devices.filter(d => d.id !== deviceId) 
      })),
      
      // Servers
      servers: [],
      setServers: (servers) => set({ servers }),
      selectedServer: null,
      setSelectedServer: (server) => set({ selectedServer: server }),
      
      // Referral
      referralStats: null,
      setReferralStats: (stats) => set({ referralStats: stats }),
      
      // UI State
      isLoading: false,
      setLoading: (loading) => set({ isLoading: loading }),
      
      // Settings
      language: 'ru',
      setLanguage: (lang) => set({ language: lang }),
      
      notifications: true,
      setNotifications: (enabled) => set({ notifications: enabled }),
      
      // VPN Key
      vpnKey: null,
      setVpnKey: (key) => set({ vpnKey: key }),
    }),
    {
      name: 'metalib-vpn-storage',
      partialize: (state) => ({
        language: state.language,
        notifications: state.notifications,
        selectedServer: state.selectedServer,
      }),
    }
  )
)
