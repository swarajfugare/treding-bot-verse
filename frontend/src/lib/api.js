const API_URL = (import.meta.env.VITE_API_URL || '').replace(/\/$/, '')

async function request(path, options = {}) {
  try {
    if (!API_URL) {
      throw new Error('VITE_API_URL is not configured.')
    }
    const endpoint = path.startsWith('/') ? path : `/${path}`
    const response = await fetch(`${API_URL}${endpoint}`, {
      headers: {
        'Content-Type': 'application/json',
        ...(options.headers || {}),
      },
      ...options,
    })
    const data = await response.json()
    return data
  } catch (error) {
    console.error('API ERROR:', error)
    return { success: false, error: error.message || 'Network request failed.' }
  }
}

export const api = {
  getMode: () => request('/api/settings/mode'),
  dashboard: (mode) => request(`/api/dashboard?mode=${mode}`),
  decision: (mode) => request(`/api/bot/decision?mode=${mode}`),
  scanner: () => request('/api/market/scanner'),
  chart: (symbol) => request(`/api/market/chart/${symbol}`),
  botStatus: () => request('/api/bot/status'),
  botControl: (body) => request('/api/bot', { method: 'POST', body: JSON.stringify(body) }),
  credentials: () => request('/api/settings/credentials'),
  saveCredentials: (body) => request('/api/settings/credentials', { method: 'POST', body: JSON.stringify(body) }),
  testCredentials: (body = {}) => request('/api/settings/credentials/test', { method: 'POST', body: JSON.stringify(body) }),
  paperMode: (enabled) => request('/api/settings/paper', { method: 'POST', body: JSON.stringify({ enabled }) }),
  setMode: (mode) => request('/api/settings/mode', { method: 'POST', body: JSON.stringify({ mode }) }),
  balance: (mode) => request(`/api/settings/balance?mode=${mode}`),
  saveBalance: (body) => request('/api/settings/balance', { method: 'POST', body: JSON.stringify(body) }),
  lossControl: () => request('/api/settings/loss-control'),
  saveLossControl: (body) => request('/api/settings/loss-control', { method: 'POST', body: JSON.stringify(body) }),
  resetLoss: () => request('/api/settings/reset-loss', { method: 'POST', body: JSON.stringify({}) }),
  analyzeStrategy: (body) => request('/api/strategy/analyze', { method: 'POST', body: JSON.stringify(body) }),
  exportTradesUrl: (mode = 'PAPER', format = 'csv') => `${API_URL}/api/trades/export?mode=${mode}&format=${format}`,
}
