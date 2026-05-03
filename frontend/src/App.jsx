import { BarChart3, Bot, Gauge, Settings as SettingsIcon } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import Dashboard from './pages/Dashboard.jsx'
import DecisionPanel from './pages/DecisionPanel.jsx'
import Settings from './pages/Settings.jsx'
import ErrorBoundary from './components/ErrorBoundary.jsx'
import { api } from './lib/api.js'

const tabs = [
  { id: 'dashboard', label: 'Dashboard', icon: BarChart3 },
  { id: 'decision', label: 'Decision', icon: Gauge },
  { id: 'settings', label: 'Settings', icon: SettingsIcon },
]

export default function App() {
  const [activeTab, setActiveTab] = useState('dashboard')
  const [mode, setMode] = useState(null)
  const [dashboard, setDashboard] = useState(null)
  const [decision, setDecision] = useState(null)
  const [chartCandles, setChartCandles] = useState([])
  const [selectedCoin, setSelectedCoin] = useState('BTCUSDT')
  const [notice, setNotice] = useState('')

  const activeView = useMemo(() => {
    if (activeTab === 'decision') {
      return <DecisionPanel decision={decision} onRefresh={loadDecision} />
    }
    if (activeTab === 'settings') {
      return (
        <Settings
          mode={mode}
          balance={dashboard?.balance_detail}
          onModeChange={handleModeChange}
          onBalanceSaved={loadAll}
        />
      )
    }
    return (
      <Dashboard
        dashboard={dashboard}
        chartCandles={chartCandles}
        selectedCoin={selectedCoin}
        onSelectCoin={setSelectedCoin}
        onRefresh={loadAll}
        onControlBot={handleBotControl}
        onExport={handleExport}
      />
    )
  }, [activeTab, dashboard, decision, chartCandles, selectedCoin, mode])

  async function loadDashboard(currentMode = mode) {
    if (!currentMode) return
    const data = await api.dashboard(currentMode)
    if (data.success) {
      setDashboard(data)
      if (data.mode && data.mode !== mode) setMode(data.mode)
    } else {
      setNotice(data.error || 'Dashboard failed to load.')
    }
  }

  async function loadDecision(currentMode = mode) {
    if (!currentMode) return
    const data = await api.decision(currentMode)
    setDecision(data)
    if (data.success && data.coin) setSelectedCoin((current) => current || data.coin)
    if (!data.success) setNotice(data.error || 'Decision engine failed safely.')
  }

  async function loadChart(symbol = selectedCoin) {
    const data = await api.chart(symbol)
    if (data.success) setChartCandles(data.candles)
  }

  async function loadAll(currentMode = mode, symbol = selectedCoin) {
    if (!currentMode) return
    await Promise.all([loadDashboard(currentMode), loadDecision(currentMode), loadChart(symbol)])
  }

  async function handleBotControl(action) {
    if (!mode) return
    setNotice('')
    const result = await api.botControl({ action, mode })
    setNotice(result.success ? `Bot ${action === 'start' ? 'started' : 'stopped'} in ${mode} mode.` : result.error || 'Bot command failed.')
    await loadAll(mode)
  }

  async function handleModeChange(nextMode) {
    if (nextMode === 'LIVE' && mode !== 'LIVE' && !window.confirm('Switch to LIVE mode?')) return
    setNotice('')
    const result = await api.setMode(nextMode)
    if (result.success) {
      setMode(result.mode)
      setNotice(`Switched to ${result.mode} mode.`)
      await loadAll(result.mode)
    } else {
      setNotice(result.error || 'Could not switch mode.')
    }
  }

  function handleExport() {
    if (!mode) return
    window.location.href = api.exportTradesUrl(mode, 'csv')
  }

  useEffect(() => {
    async function boot() {
      const result = await api.getMode()
      const restoredMode = result.success ? result.mode : 'PAPER'
      setMode(restoredMode)
      await loadAll(restoredMode)
    }
    boot()
  }, [])

  useEffect(() => {
    if (!mode) return undefined
    const id = window.setInterval(() => loadAll(mode), 3000)
    return () => window.clearInterval(id)
  }, [mode, selectedCoin])

  useEffect(() => {
    if (!selectedCoin) return
    loadChart(selectedCoin)
  }, [selectedCoin])

  if (!mode) {
    return (
      <main className="grid min-h-screen place-items-center bg-slate-950 text-slate-100">
        <div className="rounded-lg border border-slate-800 bg-slate-900 p-6 font-bold">Loading PulseX Trader mode...</div>
      </main>
    )
  }

  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_top_left,#164e63_0%,#020617_34%,#020617_100%)] text-slate-100">
      <div className="mx-auto flex w-full max-w-7xl flex-col gap-5 px-3 py-4 sm:gap-6 sm:px-6 lg:px-8">
        <header className="panel flex flex-col gap-4 rounded-lg p-4 lg:flex-row lg:items-center lg:justify-between">
          <div className="flex min-w-0 items-center gap-3">
            <div className="grid h-12 w-12 place-items-center rounded-lg bg-cyan-400 text-slate-950">
              <Bot size={26} aria-hidden="true" />
            </div>
            <div className="min-w-0">
              <h1 className="text-2xl font-black text-slate-50">PulseX Trader</h1>
              <p className="text-sm font-medium text-slate-400">Professional multi-mode scanner and trade console</p>
            </div>
          </div>

          <div className="flex w-full flex-col gap-3 sm:flex-row sm:flex-wrap lg:w-auto lg:items-center lg:justify-end">
            <div className="grid grid-cols-2 rounded-lg bg-slate-950 p-1 sm:w-auto">
              {['PAPER', 'LIVE'].map((item) => (
                <button
                  type="button"
                  key={item}
                  onClick={() => handleModeChange(item)}
                  className={`h-11 rounded-md px-4 text-sm font-black ${mode === item ? 'bg-cyan-400 text-slate-950' : 'text-slate-400 hover:bg-slate-800'}`}
                >
                  {item}
                </button>
              ))}
            </div>
            <nav className="grid grid-cols-3 gap-2 sm:flex sm:flex-wrap">
              {tabs.map((tab) => {
                const Icon = tab.icon
                const active = activeTab === tab.id
                return (
                  <button
                    key={tab.id}
                    type="button"
                    onClick={() => setActiveTab(tab.id)}
                    className={`focus-ring inline-flex h-11 min-w-0 items-center justify-center gap-2 rounded-lg px-3 font-semibold ${
                      active ? 'bg-slate-100 text-slate-950' : 'bg-slate-950 text-slate-300 hover:bg-slate-800'
                    }`}
                  >
                    <Icon size={18} className="shrink-0" />
                    <span className="truncate">{tab.label}</span>
                  </button>
                )
              })}
            </nav>
          </div>
        </header>

        {notice && (
          <div className="rounded-lg border border-cyan-500/30 bg-cyan-500/10 px-4 py-3 text-sm font-semibold text-cyan-100">
            {notice}
          </div>
        )}

        <ErrorBoundary>
          {activeView}
        </ErrorBoundary>
      </div>
    </main>
  )
}
