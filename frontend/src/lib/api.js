 ~
 import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export const api = axios.create({
  baseURL: API_URL,
  timeout: 15000,
})

// --- Sleeper ---
export const lookupSleeperUser = (username) => api.get(`/sleeper/user/${username}`)
export const getSleeperLeagues = (username) => api.get(`/sleeper/user/${username}/leagues`)
export const previewLeague = (leagueId) => api.get(`/sleeper/league/${leagueId}/preview`)

// --- Roster ---
export const setupRoster = (data) => api.post('/roster/setup', data)
export const getRoster = (sessionId) => api.get(`/roster/${sessionId}`)
export const removePlayer = (sessionId, playerId) => api.delete(`/roster/${sessionId}/player/${playerId}`)

// --- Players ---
export const searchPlayers = (q) => api.get('/players/search', { params: { q } })

// --- Schedule + Streaming ---
export const getWeeklySchedule = (sessionId) => api.get(`/schedule/${sessionId}`)
export const getWaiverTargets = (sessionId) => api.get(`/schedule/${sessionId}/waiver`)

// --- Notifications ---
export const getNotifications = (sessionId) => api.get(`/notifications/${sessionId}`)
export const markAllRead = (sessionId) => api.post(`/notifications/${sessionId}/read-all`)
export const getTodayGames = () => api.get('/notifications/games/today')
