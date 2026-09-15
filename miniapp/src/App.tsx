import { useState, useEffect } from 'react'
import { Routes, Route, useNavigate, useLocation } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import HomePage from './pages/HomePage'
import SubscriptionPage from './pages/SubscriptionPage'
import DevicesPage from './pages/DevicesPage'
import ServersPage from './pages/ServersPage'
import ReferralPage from './pages/ReferralPage'
import SettingsPage from './pages/SettingsPage'
import StatsPage from './pages/StatsPage'
import PaymentsPage from './pages/PaymentsPage'
import Navigation from './components/Navigation'
import { useStore } from './store'
import { api } from './api'
import { initTheme } from './theme'

// Initialize theme on app load
initTheme()

const pageVariants = {
  initial: { opacity: 0, y: 20 },
  in: { opacity: 1, y: 0 },
  out: { opacity: 0, y: -20 }
}

const pageTransition = {
  type: 'tween',
  ease: 'anticipate',
  duration: 0.3
}

function App() {
  const location = useLocation()
  const navigate = useNavigate()
  const { setUser, setSubscription, setLoading, isLoading } = useStore()
  const [isInitialized, setIsInitialized] = useState(false)

  useEffect(() => {
    const initApp = async () => {
      setLoading(true)
      
      try {
        // Get Telegram WebApp data
        const tg = window.Telegram?.WebApp
        
        if (tg?.initData) {
          // Authenticate with backend using Telegram init data
          const authResponse = await api.auth(tg.initData)
          
          if (authResponse.success && authResponse.user) {
            setUser(authResponse.user)
            
            // Load subscription data
            const subResponse = await api.getSubscription()
            if (subResponse.success && subResponse.subscription) {
              setSubscription(subResponse.subscription)
            }
          }
        } else {
          // Development mode - use mock data
          console.log('Running in development mode without Telegram WebApp')
          setUser({
            id: 123456789,
            first_name: 'Test',
            last_name: 'User',
            username: 'testuser',
            language_code: 'ru'
          })
        }
      } catch (error) {
        console.error('Failed to initialize app:', error)
      } finally {
        setLoading(false)
        setIsInitialized(true)
      }
    }

    initApp()
  }, [])

  // Handle Telegram back button
  useEffect(() => {
    const tg = window.Telegram?.WebApp

    if (tg) {
      if (location.pathname !== '/') {
        tg.BackButton.show()
        tg.BackButton.onClick(() => {
          navigate(-1)
        })
      } else {
        tg.BackButton.hide()
      }
    }

    return () => {
      tg?.BackButton.offClick(() => {})
    }
  }, [location.pathname, navigate])

  if (!isInitialized || isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="flex flex-col items-center gap-4">
          <div className="w-12 h-12 border-4 border-purple-500 border-t-transparent rounded-full animate-spin" />
          <p className="text-gray-400">Загрузка...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col min-h-screen pb-20 safe-area-bottom">
      <AnimatePresence mode="wait">
        <motion.div
          key={location.pathname}
          initial="initial"
          animate="in"
          exit="out"
          variants={pageVariants}
          transition={pageTransition}
          className="flex-1"
        >
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/subscription" element={<SubscriptionPage />} />
            <Route path="/devices" element={<DevicesPage />} />
            <Route path="/servers" element={<ServersPage />} />
            <Route path="/referral" element={<ReferralPage />} />
            <Route path="/settings" element={<SettingsPage />} />
            <Route path="/stats" element={<StatsPage />} />
            <Route path="/payments" element={<PaymentsPage />} />
          </Routes>
        </motion.div>
      </AnimatePresence>
      
      <Navigation />
    </div>
  )
}

export default App
