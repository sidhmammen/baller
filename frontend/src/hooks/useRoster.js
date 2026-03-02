import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getRoster, setupRoster, removePlayer } from '../lib/api'
import { useState, useEffect } from 'react'

const SESSION_KEY = 'fantasy_nba_session_id'

export function useSessionId() {
  const [sessionId, setSessionId] = useState(() => localStorage.getItem(SESSION_KEY))

  const saveSession = (id) => {
    localStorage.setItem(SESSION_KEY, id)
    setSessionId(id)
  }

  return { sessionId, saveSession }
}

export function useRoster(sessionId) {
  return useQuery({
    queryKey: ['roster', sessionId],
    queryFn: () => getRoster(sessionId).then(r => r.data),
    enabled: !!sessionId,
    staleTime: 30000,
  })
}

export function useSetupRoster() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: setupRoster,
    onSuccess: (data) => {
      qc.setQueryData(['roster', data.data.session_id], data.data)
      qc.invalidateQueries(['schedule', data.data.session_id])
    },
  })
}

export function useRemovePlayer(sessionId) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (playerId) => removePlayer(sessionId, playerId),
    onSuccess: () => {
      qc.invalidateQueries(['roster', sessionId])
      qc.invalidateQueries(['schedule', sessionId])
    },
  })
}
