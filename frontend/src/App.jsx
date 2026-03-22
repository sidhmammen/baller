import { QueryClient, QueryClientProvider, useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { Setup } from './pages/Setup'
import { Dashboard } from './pages/Dashboard'
import DashboardLayout from './components/DashboardLayout'
import { useSessionId } from './hooks/useRoster'
import { getNotifications } from './lib/api'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
})

function AppInner() {
  const { sessionId, saveSession } = useSessionId()
  const [view, setView] = useState(sessionId ? 'dashboard' : 'setup')
  const [activeTab, setActiveTab] = useState('roster')
  const [connected, setConnected] = useState(false)

  const handleSetupComplete = (id) => {
    saveSession(id)
    setView('dashboard')
  }

  const handleResetRoster = () => {
    setView('setup')
  }

  // Fetch notifications for layout
  const notifQuery = useQuery({
    queryKey: ['notifications', sessionId],
    queryFn: () => getNotifications(sessionId).then(r => r.data),
    enabled: !!sessionId,
    staleTime: 30000,
  })

  if (view === 'setup') {
    return <Setup onComplete={handleSetupComplete} />
  }

  return (
    <DashboardLayout
      sessionId={sessionId}
      notifications={notifQuery.data || []}
      onMarkRead={() => notifQuery.refetch()}
      activeTab={activeTab}
      onTabChange={setActiveTab}
      connected={connected}
    >
      <Dashboard
        sessionId={sessionId}
        onResetRoster={handleResetRoster}
        activeTab={activeTab}
        onTabChange={setActiveTab}
        onConnectedChange={setConnected}
      />
    </DashboardLayout>
  )
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AppInner />
    </QueryClientProvider>
  )
}