import axios, { AxiosInstance } from 'axios'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'https://panel.metalib.xyz/api/v1'

class ApiClient {
  private client: AxiosInstance

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      headers: {
        'Content-Type': 'application/json',
      },
    })

    // Request interceptor for adding auth token
    this.client.interceptors.request.use(
      (config) => {
        const token = localStorage.getItem('admin_token')
        if (token) {
          config.headers.Authorization = `Bearer ${token}`
        }
        return config
      },
      (error) => Promise.reject(error)
    )

    // Response interceptor for handling errors
    this.client.interceptors.response.use(
      (response) => response,
      (error) => {
        if (error.response?.status === 401) {
          localStorage.removeItem('admin_token')
          window.location.href = '/admin/login'
        }
        return Promise.reject(error)
      }
    )
  }

  // Auth
  async login(username: string, password: string) {
    const response = await this.client.post('/auth/login', { username, password })
    return response.data
  }

  async getProfile() {
    const response = await this.client.get('/auth/me')
    return response.data
  }

  // Dashboard
  async getDashboardStats() {
    const response = await this.client.get('/admin/dashboard')
    return response.data
  }

  async getDashboardChartData(days: number = 30) {
    const response = await this.client.get('/admin/dashboard/chart', { params: { days } })
    return response.data
  }

  // Traffic
  async getTrafficStats() {
    const response = await this.client.get('/admin/traffic')
    return response.data
  }

  // Users
  async getUsers(params?: { skip?: number; limit?: number; search?: string }) {
    const response = await this.client.get('/admin/users', { params })
    return response.data
  }

  async getUserById(userId: number) {
    const response = await this.client.get(`/admin/users/${userId}`)
    return response.data
  }

  async banUser(userId: number) {
    const response = await this.client.post(`/admin/users/${userId}/ban`)
    return response.data
  }

  async unbanUser(userId: number) {
    const response = await this.client.post(`/admin/users/${userId}/unban`)
    return response.data
  }

  // Plans
  async getPlans() {
    const response = await this.client.get('/admin/plans')
    return response.data
  }

  async createPlan(data: any) {
    const response = await this.client.post('/admin/plans', data)
    return response.data
  }

  async updatePlan(planId: number, data: any) {
    const response = await this.client.put(`/admin/plans/${planId}`, data)
    return response.data
  }

  async deletePlan(planId: number) {
    const response = await this.client.delete(`/admin/plans/${planId}`)
    return response.data
  }

  // Servers
  async getServers() {
    const response = await this.client.get('/servers/')
    return response.data
  }

  async createServer(data: any) {
    const response = await this.client.post('/servers/', data)
    return response.data
  }

  async updateServer(serverId: string | number, data: any) {
    const response = await this.client.put(`/servers/${serverId}`, data)
    return response.data
  }

  async deleteServer(serverId: string | number) {
    const response = await this.client.delete(`/servers/${serverId}`)
    return response.data
  }

  async testServerConnection(serverId: string | number) {
    const response = await this.client.post(`/servers/${serverId}/health-check`)
    return response.data
  }

  // Payments
  async getPayments(params?: { skip?: number; limit?: number }) {
    const response = await this.client.get('/admin/payments', { params })
    return response.data
  }

  // Export
  async exportUsersCSV() {
    const response = await this.client.get('/admin/export/users', { responseType: 'blob' })
    return response.data
  }

  async exportPaymentsCSV() {
    const response = await this.client.get('/admin/export/payments', { responseType: 'blob' })
    return response.data
  }

  // Broadcasts
  async sendBroadcast(data: { message: string; users?: number[]; filter?: any }) {
    const response = await this.client.post('/admin/broadcast', data)
    return response.data
  }

  async getBroadcastHistory() {
    const response = await this.client.get('/admin/broadcasts')
    return response.data
  }

  // Referrals
  async getReferralStats() {
    const response = await this.client.get('/referrals/stats')
    return response.data
  }

  async getReferralsStatus() {
    const response = await this.client.get('/admin/referrals/status')
    return response.data
  }

  async toggleReferrals() {
    const response = await this.client.post('/admin/referrals/toggle')
    return response.data
  }

  // Settings
  async getSettings() {
    const response = await this.client.get('/admin/settings')
    return response.data
  }

  async updateSettings(data: any) {
    const response = await this.client.put('/admin/settings', data)
    return response.data
  }

  async uploadImage(file: File, type: 'banner' | 'logo') {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('type', type)
    const response = await this.client.post('/admin/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return response.data
  }

  // Alerts
  async getAlertStats() {
    const response = await this.client.get('/admin/alerts/stats')
    return response.data
  }

  async getAlerts(params?: { status_filter?: string; category?: string; limit?: number }) {
    const response = await this.client.get('/admin/alerts/', { params })
    return response.data
  }

  async resolveAlert(alertId: string, note?: string) {
    const response = await this.client.post(`/admin/alerts/${alertId}/resolve`, { note })
    return response.data
  }

  // Analytics
  async getAnalytics(period: string = '30d') {
    const response = await this.client.get('/admin/analytics', { params: { period } })
    return response.data
  }

  async exportAnalytics(period: string = '30d') {
    const response = await this.client.get('/admin/analytics/export', { 
      params: { period },
      responseType: 'blob'
    })
    return response.data
  }

  // Audit Logs
  async getAuditLogs(params?: { 
    admin_id?: string; 
    resource_type?: string; 
    action?: string;
    limit?: number;
    offset?: number;
  }) {
    const response = await this.client.get('/admin/audit-logs', { params })
    return response.data
  }

  // IP Whitelist
  async getIPWhitelist() {
    const response = await this.client.get('/admin/settings/ip-whitelist')
    return response.data
  }

  async addToIPWhitelist(ip: string) {
    const response = await this.client.post('/admin/settings/ip-whitelist', { ip })
    return response.data
  }

  async removeFromIPWhitelist(ip: string) {
    const response = await this.client.delete(`/admin/settings/ip-whitelist/${ip}`)
    return response.data
  }

  // Generic methods
  async get(url: string, params?: any) {
    const response = await this.client.get(url, { params })
    return response.data
  }

  async post(url: string, data?: any) {
    const response = await this.client.post(url, data)
    return response.data
  }

  async put(url: string, data?: any) {
    const response = await this.client.put(url, data)
    return response.data
  }

  async patch(url: string, data?: any) {
    const response = await this.client.patch(url, data)
    return response.data
  }

  async delete(url: string) {
    const response = await this.client.delete(url)
    return response.data
  }
}

export const apiClient = new ApiClient()
export const api = apiClient // alias for compatibility
