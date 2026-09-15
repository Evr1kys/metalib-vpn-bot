import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export type ThemeName = 'dark' | 'purple' | 'blue' | 'green' | 'orange'

interface ThemeColors {
  primary: string
  secondary: string
  accent: string
  background: string
  surface: string
  text: string
  textSecondary: string
  success: string
  danger: string
  warning: string
}

export const themes: Record<ThemeName, ThemeColors> = {
  dark: {
    primary: '#8b5cf6',
    secondary: '#6366f1',
    accent: '#a855f7',
    background: '#0f0f1a',
    surface: '#1a1a2e',
    text: '#ffffff',
    textSecondary: '#9ca3af',
    success: '#22c55e',
    danger: '#ef4444',
    warning: '#f59e0b',
  },
  purple: {
    primary: '#a855f7',
    secondary: '#7c3aed',
    accent: '#c084fc',
    background: '#1a0a2e',
    surface: '#2d1b4e',
    text: '#ffffff',
    textSecondary: '#c4b5fd',
    success: '#22c55e',
    danger: '#ef4444',
    warning: '#f59e0b',
  },
  blue: {
    primary: '#3b82f6',
    secondary: '#1d4ed8',
    accent: '#60a5fa',
    background: '#0a1628',
    surface: '#1e3a5f',
    text: '#ffffff',
    textSecondary: '#93c5fd',
    success: '#22c55e',
    danger: '#ef4444',
    warning: '#f59e0b',
  },
  green: {
    primary: '#22c55e',
    secondary: '#15803d',
    accent: '#4ade80',
    background: '#0a1f0f',
    surface: '#1a3a1f',
    text: '#ffffff',
    textSecondary: '#86efac',
    success: '#22c55e',
    danger: '#ef4444',
    warning: '#f59e0b',
  },
  orange: {
    primary: '#f97316',
    secondary: '#ea580c',
    accent: '#fb923c',
    background: '#1a0f0a',
    surface: '#3a2a1a',
    text: '#ffffff',
    textSecondary: '#fdba74',
    success: '#22c55e',
    danger: '#ef4444',
    warning: '#f59e0b',
  },
}

export const themeLabels: Record<ThemeName, { name: string; emoji: string }> = {
  dark: { name: 'Тёмная', emoji: '🌙' },
  purple: { name: 'Фиолетовая', emoji: '💜' },
  blue: { name: 'Синяя', emoji: '💙' },
  green: { name: 'Зелёная', emoji: '💚' },
  orange: { name: 'Оранжевая', emoji: '🧡' },
}

interface ThemeStore {
  theme: ThemeName
  setTheme: (theme: ThemeName) => void
}

export const useThemeStore = create<ThemeStore>()(
  persist(
    (set) => ({
      theme: 'dark',
      setTheme: (theme) => {
        set({ theme })
        applyTheme(theme)
      },
    }),
    {
      name: 'metalib-theme',
    }
  )
)

export function applyTheme(themeName: ThemeName) {
  const theme = themes[themeName]
  const root = document.documentElement
  
  root.style.setProperty('--primary', theme.primary)
  root.style.setProperty('--secondary', theme.secondary)
  root.style.setProperty('--accent', theme.accent)
  root.style.setProperty('--bg', theme.background)
  root.style.setProperty('--surface', theme.surface)
  root.style.setProperty('--text', theme.text)
  root.style.setProperty('--text-secondary', theme.textSecondary)
  root.style.setProperty('--success', theme.success)
  root.style.setProperty('--danger', theme.danger)
  root.style.setProperty('--warning', theme.warning)
  
  // Update body background
  document.body.style.backgroundColor = theme.background
}

// Initialize theme on load
export function initTheme() {
  const stored = localStorage.getItem('metalib-theme')
  if (stored) {
    try {
      const parsed = JSON.parse(stored)
      if (parsed.state?.theme && themes[parsed.state.theme as ThemeName]) {
        applyTheme(parsed.state.theme as ThemeName)
        return
      }
    } catch (e) {
      console.warn('Failed to parse stored theme')
    }
  }
  applyTheme('dark')
}
