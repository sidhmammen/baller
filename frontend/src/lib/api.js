import axios from 'axios'

// All requests go through Vite proxy → backend:8000
export const api = axios.create({ baseURL: '', timeout: 30000 })

export const lookupSleeperUser = (username) => api.get(`/sleeper/user/${username}`)
export const getSleeperLeagues = (username) => api.get(`/sleeper/user/${username}/leagues`)
export const setupRoster = (data) => api.post('/roster/setup', data)
export const getRoster = (sessionId) => api.get(`/roster/${sessionId}`)
export const removePlayer = (sessionId, playerId) => api.delete(`/roster/${sessionId}/player/${playerId}`)
export const searchPlayers = (q) => api.get('/players/search', { params: { q } })
export const getWeeklySchedule = (sessionId) => api.get(`/schedule/${sessionId}`)
export const getWaiverTargets = (sessionId) => api.get(`/schedule/${sessionId}/waiver`)
export const getNotifications = (sessionId) => api.get(`/notifications/${sessionId}`)
export const markAllRead = (sessionId) => api.post(`/notifications/${sessionId}/read-all`)