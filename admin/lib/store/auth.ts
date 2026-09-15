import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface Admin {
  id: number
  username: string
  role: string
}

interface AuthState {
  token: string | null
  admin: Admin | null
  setAuth: (token: string, admin: Admin) => void
  logout: () => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      admin: null,
      setAuth: (token, admin) => set({ token, admin }),
      logout: () => set({ token: null, admin: null }),
    }),
    {
      name: 'admin-auth',
    }
  )
)
