import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:5001',
  timeout: 120_000,  // simulations can take up to 2 minutes
})

export const getHealth   = ()        => api.get('/api/airwave/health').then(r => r.data)
export const getTriggers = ()        => api.get('/api/airwave/triggers').then(r => r.data)
export const getAgents   = ()        => api.get('/api/airwave/agents').then(r => r.data)

export const fetchSeed   = (body)    => api.post('/api/airwave/seed', body).then(r => r.data)
export const runCascade  = (body)    => api.post('/api/airwave/cascade', body).then(r => r.data)
export const runSimulate = (body)    => api.post('/api/airwave/simulate', body).then(r => r.data)
