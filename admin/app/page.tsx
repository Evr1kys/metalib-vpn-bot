'use client'

import { useEffect, useState } from 'react'
import { useAuthStore } from '@/lib/store/auth'

export default function HomePage() {
  const { token } = useAuthStore()
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    setMounted(true)
  }, [])

  useEffect(() => {
    if (mounted) {
      // Use window.location for static export with basePath
      if (token) {
        window.location.replace('/admin/dashboard/')
      } else {
        window.location.replace('/admin/login/')
      }
    }
  }, [mounted, token])

  return (
    <div className="flex items-center justify-center min-h-screen bg-[#0f0f1a]">
      <div className="flex flex-col items-center gap-4">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-500"></div>
        <p className="text-white/60 text-sm">Загрузка...</p>
      </div>
    </div>
  )
}
