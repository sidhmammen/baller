import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useState, useEffect } from 'react'
import { Setup } from './pages/Setup'
import { Dashboard } from './pages/Dashboard'
import { useSessionId } from './hooks/useRoster'

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

  const handleSetupComplete = (id) => {
    saveSession(id)
    setView('dashboard')
  }

  const handleResetRoster = () => {
    setView('setup')
  }

  if (view === 'setup') {
    return <Setup onComplete={handleSetupComplete} />
  }

  return (
    <Dashboard
      sessionId={sessionId}
      onResetRoster={handleResetRoster}
    />
  )
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AppInner />
    </QueryClientProvider>
  )
}
