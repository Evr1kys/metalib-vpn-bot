import type { 
  TelegramUser, 
  Subscription, 
  Device, 
  Server, 
  ReferralStats 
} from './store'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'https://vpn.metalib.xyz/api/v1'

interface ApiResponse<T> {
  success: boolean
  data?: T
  error?: string
}

class ApiClient {
  private token: string | null = null
  private initData: string | null = null

  setInitData(initData: string) {
    this.initData = initData
  }

  setToken(token: string) {
    this.token = token
  }

  private async request<T>(
    endpoint: string, 
    options: RequestInit = {}
  ): Promise<ApiResponse<T>> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...(options.headers as Record<string, string>),
    }

    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`
    }

    if (this.initData) {
      headers['X-Telegram-Init-Data'] = this.initData
    }

    try {
      const response = await fetch(`${API_BASE_URL}${endpoint}`, {
        ...options,
        headers,
      })

      const data = await response.json()

      if (!response.ok) {
        return {
          success: false,
          error: data.detail || data.message || 'Request failed',
        }
      }

      return {
        success: true,
        data,
      }
    } catch (error) {
      console.error('API request failed:', error)
      return {
        success: false,
        error: 'Network error. Please try again.',
      }
    }
  }

  // Authentication
  async auth(initData: string): Promise<{ success: boolean; user?: TelegramUser; token?: string }> {
    this.setInitData(initData)
    
    const response = await this.request<{ user: TelegramUser; token: string }>('/telegram/auth', {
      method: 'POST',
      body: JSON.stringify({ init_data: initData }),
    })

    if (response.success && response.data) {
      this.setToken(response.data.token)
      return {
        success: true,
        user: response.data.user,
        token: response.data.token,
      }
    }

    return { success: false }
  }

  // Subscription
  async getSubscription(): Promise<{ success: boolean; subscription?: Subscription }> {
    const response = await this.request<Subscription>('/subscription/current')
    
    if (response.success && response.data) {
      return { success: true, subscription: response.data }
    }

    return { success: false }
  }

  async getPlans(): Promise<{ success: boolean; plans?: any[] }> {
    const response = await this.request<any[]>('/plans')
    return response.success ? { success: true, plans: response.data } : { success: false }
  }

  async createPayment(planId: string): Promise<{ success: boolean; paymentUrl?: string }> {
    const response = await this.request<{ payment_url: string }>('/payments/create', {
      method: 'POST',
      body: JSON.stringify({ plan_id: planId }),
    })

    if (response.success && response.data) {
      return { success: true, paymentUrl: response.data.payment_url }
    }

    return { success: false }
  }

  async toggleAutoRenewal(enabled: boolean): Promise<{ success: boolean }> {
    const response = await this.request('/subscription/auto-renewal', {
      method: 'POST',
      body: JSON.stringify({ enabled }),
    })

    return { success: response.success }
  }

  // Devices
  async getDevices(): Promise<{ success: boolean; devices?: Device[] }> {
    const response = await this.request<Device[]>('/devices')
    return response.success ? { success: true, devices: response.data } : { success: false }
  }

  async addDevice(name: string, type: string): Promise<{ success: boolean; device?: Device }> {
    const response = await this.request<Device>('/devices', {
      method: 'POST',
      body: JSON.stringify({ name, type }),
    })

    if (response.success && response.data) {
      return { success: true, device: response.data }
    }

    return { success: false }
  }

  async removeDevice(deviceId: string): Promise<{ success: boolean }> {
    const response = await this.request(`/devices/${deviceId}`, {
      method: 'DELETE',
    })

    return { success: response.success }
  }

  async renameDevice(deviceId: string, name: string): Promise<{ success: boolean }> {
    const response = await this.request(`/devices/${deviceId}`, {
      method: 'PATCH',
      body: JSON.stringify({ name }),
    })

    return { success: response.success }
  }

  // VPN Key
  async getVpnKey(serverId?: string): Promise<{ success: boolean; key?: string; qrCode?: string }> {
    const endpoint = serverId ? `/vpn/key?server_id=${serverId}` : '/vpn/key'
    const response = await this.request<{ key: string; qr_code: string }>(endpoint)

    if (response.success && response.data) {
      return { 
        success: true, 
        key: response.data.key, 
        qrCode: response.data.qr_code 
      }
    }

    return { success: false }
  }

  // Servers
  async getServers(): Promise<{ success: boolean; servers?: Server[] }> {
    const response = await this.request<Server[]>('/servers')
    return response.success ? { success: true, servers: response.data } : { success: false }
  }

  async checkServerPing(serverId: string): Promise<{ success: boolean; ping?: number }> {
    const response = await this.request<{ ping: number }>(`/servers/${serverId}/ping`)
    return response.success && response.data 
      ? { success: true, ping: response.data.ping } 
      : { success: false }
  }

  // Referrals
  async getReferralStats(): Promise<{ success: boolean; stats?: ReferralStats }> {
    const response = await this.request<ReferralStats>('/referrals/stats')
    return response.success ? { success: true, stats: response.data } : { success: false }
  }

  async getReferralHistory(): Promise<{ success: boolean; history?: any[] }> {
    const response = await this.request<any[]>('/referrals/history')
    return response.success ? { success: true, history: response.data } : { success: false }
  }

  async withdrawReferralEarnings(): Promise<{ success: boolean }> {
    const response = await this.request('/referrals/withdraw', {
      method: 'POST',
    })

    return { success: response.success }
  }

  // Settings
  async updateLanguage(language: string): Promise<{ success: boolean }> {
    const response = await this.request('/users/language', {
      method: 'POST',
      body: JSON.stringify({ language }),
    })

    return { success: response.success }
  }

  async updateNotifications(enabled: boolean): Promise<{ success: boolean }> {
    const response = await this.request('/users/notifications', {
      method: 'POST',
      body: JSON.stringify({ enabled }),
    })

    return { success: response.success }
  }

  // Support
  async sendSupportMessage(message: string): Promise<{ success: boolean; ticketId?: string }> {
    const response = await this.request<{ ticket_id: string }>('/support/message', {
      method: 'POST',
      body: JSON.stringify({ message }),
    })

    if (response.success && response.data) {
      return { success: true, ticketId: response.data.ticket_id }
    }

    return { success: false }
  }

  // Usage Statistics
  async getUsageStats(period: '7d' | '30d' | 'all' = '7d'): Promise<{ success: boolean; data?: any }> {
    const response = await this.request<any>(`/telegram/stats?period=${period}`)
    return response.success ? { success: true, data: response.data } : { success: false }
  }

  // Payment History
  async getPaymentHistory(): Promise<{ success: boolean; data?: { payments: any[]; total: number; total_spent: number } }> {
    const response = await this.request<{ payments: any[]; total: number; total_spent: number }>('/telegram/payments')
    return response.success ? { success: true, data: response.data } : { success: false }
  }
}

export const api = new ApiClient()
