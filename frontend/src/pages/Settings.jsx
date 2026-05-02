import { KeyRound, PlugZap, Save, Upload } from 'lucide-react'
import { useEffect, useState } from 'react'
import StatusPill from '../components/StatusPill.jsx'
import { api } from '../lib/api.js'

export default function Settings({ mode, balance, onModeChange, onBalanceSaved }) {
  const [credentials, setCredentials] = useState({ connected: false })
  const [form, setForm] = useState({ api_key: '', api_secret: '' })
  const [balanceForm, setBalanceForm] = useState({ usdt_balance: '', inr_balance: '' })
  const [message, setMessage] = useState('')
  const [analysis, setAnalysis] = useState(null)
  const [saving, setSaving] = useState(false)

  async function loadCredentials() {
    const data = await api.credentials()
    setCredentials(data)
  }

  useEffect(() => {
    loadCredentials()
  }, [])

  useEffect(() => {
    setBalanceForm({
      usdt_balance: balance?.native_usdt_balance ?? '',
      inr_balance: balance?.inr_balance ?? '',
    })
  }, [balance])

  async function saveCredentials(event) {
    event.preventDefault()
    setSaving(true)
    setMessage('')
    const result = await api.saveCredentials(form)
    setSaving(false)
    setMessage(result.success ? 'Credentials saved securely.' : result.error || 'Unable to save credentials.')
    if (result.success) {
      setForm({ api_key: '', api_secret: '' })
      loadCredentials()
    }
  }

  async function saveBalance(event) {
    event.preventDefault()
    const result = await api.saveBalance({
      mode,
      usdt_balance: Number(balanceForm.usdt_balance || 0),
      inr_balance: Number(balanceForm.inr_balance || 0),
    })
    setMessage(result.success ? `${mode} balance saved.` : result.error || 'Unable to save balance.')
    if (result.success) onBalanceSaved()
  }

  async function testConnection() {
    setMessage('')
    const result = await api.testCredentials()
    setMessage(result.success ? 'Connection format looks valid.' : result.error || 'Connection test failed.')
  }

  async function uploadTradeData(event) {
    const file = event.target.files?.[0]
    if (!file) return
    const content = await file.text()
    const result = await api.analyzeStrategy({ filename: file.name, content })
    setAnalysis(result)
  }

  return (
    <section className="panel rounded-lg p-5">
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h2 className="text-xl font-bold text-slate-50">Settings</h2>
          <p className="mt-2 text-sm text-slate-400">Mode, balances, credentials, and strategy improvement tools.</p>
        </div>
        <StatusPill active={Boolean(credentials.connected)} label={credentials.connected ? 'Connected' : 'Not Connected'} />
      </div>

      <div className="mt-6 grid gap-6 xl:grid-cols-3">
        <div className="rounded-lg border border-slate-800 bg-slate-950 p-5">
          <h3 className="font-bold text-slate-50">Trading Mode</h3>
          <div className="mt-4 grid grid-cols-2 gap-2 rounded-lg bg-slate-900 p-1">
            {['PAPER', 'LIVE'].map((item) => (
              <button
                type="button"
                key={item}
                onClick={() => onModeChange(item)}
                className={`h-10 rounded-md font-bold ${mode === item ? 'bg-cyan-500 text-slate-950' : 'text-slate-400 hover:bg-slate-800'}`}
              >
                {item}
              </button>
            ))}
          </div>

          <form onSubmit={saveBalance} className="mt-5 grid gap-4">
            <label className="grid gap-2 text-sm font-semibold text-slate-300">
              USDT Balance
              <input
                value={balanceForm.usdt_balance}
                onChange={(event) => setBalanceForm((current) => ({ ...current, usdt_balance: event.target.value }))}
                className="focus-ring h-11 rounded-lg border border-slate-700 bg-slate-900 px-3 text-slate-100"
                type="number"
                step="0.01"
              />
            </label>
            <label className="grid gap-2 text-sm font-semibold text-slate-300">
              INR Balance
              <input
                value={balanceForm.inr_balance}
                onChange={(event) => setBalanceForm((current) => ({ ...current, inr_balance: event.target.value }))}
                className="focus-ring h-11 rounded-lg border border-slate-700 bg-slate-900 px-3 text-slate-100"
                type="number"
                step="0.01"
              />
            </label>
            <button type="submit" className="focus-ring inline-flex h-11 items-center justify-center gap-2 rounded-lg bg-cyan-500 px-4 font-bold text-slate-950 hover:bg-cyan-400">
              <Save size={18} />
              Save Balance
            </button>
          </form>
        </div>

        <form onSubmit={saveCredentials} className="rounded-lg border border-slate-800 bg-slate-950 p-5">
          <div className="flex items-center gap-3">
            <div className="grid h-10 w-10 place-items-center rounded-lg bg-emerald-500/15 text-emerald-300">
              <KeyRound size={21} />
            </div>
            <div>
              <h3 className="font-bold text-slate-50">API Credentials</h3>
              <p className="text-sm text-slate-500">Current key: {credentials.api_key || 'not saved'}</p>
            </div>
          </div>

          <div className="mt-5 grid gap-4">
            <label className="grid gap-2 text-sm font-semibold text-slate-300">
              API Key
              <input value={form.api_key} onChange={(event) => setForm((current) => ({ ...current, api_key: event.target.value }))} className="focus-ring h-11 rounded-lg border border-slate-700 bg-slate-900 px-3 text-slate-100" />
            </label>
            <label className="grid gap-2 text-sm font-semibold text-slate-300">
              API Secret
              <input value={form.api_secret} onChange={(event) => setForm((current) => ({ ...current, api_secret: event.target.value }))} className="focus-ring h-11 rounded-lg border border-slate-700 bg-slate-900 px-3 text-slate-100" type="password" />
            </label>
          </div>

          <div className="mt-5 flex flex-wrap gap-3">
            <button type="submit" disabled={saving} className="focus-ring inline-flex h-11 items-center gap-2 rounded-lg bg-emerald-600 px-4 font-semibold text-white hover:bg-emerald-500 disabled:opacity-60">
              <Save size={18} />
              {saving ? 'Saving' : 'Save'}
            </button>
            <button type="button" onClick={testConnection} className="focus-ring inline-flex h-11 items-center gap-2 rounded-lg border border-slate-700 bg-slate-900 px-4 font-semibold text-slate-200 hover:bg-slate-800">
              <PlugZap size={18} />
              Test
            </button>
          </div>
          {message && <p className="mt-4 rounded-lg bg-slate-900 p-3 text-sm font-medium text-slate-300">{message}</p>}
        </form>

        <div className="rounded-lg border border-slate-800 bg-slate-950 p-5">
          <h3 className="font-bold text-slate-50">Strategy Improvement</h3>
          <p className="mt-2 text-sm text-slate-400">Upload exported CSV or JSON trade data for performance suggestions.</p>
          <label className="focus-ring mt-5 inline-flex h-11 cursor-pointer items-center gap-2 rounded-lg border border-slate-700 bg-slate-900 px-4 font-semibold text-slate-200 hover:bg-slate-800">
            <Upload size={18} />
            Upload Trade Data
            <input type="file" accept=".csv,.json" className="hidden" onChange={uploadTradeData} />
          </label>
          {analysis && (
            <div className="mt-5 rounded-lg bg-slate-900 p-4 text-sm">
              {analysis.success ? (
                <>
                  <div className="grid grid-cols-2 gap-2 text-slate-300">
                    <span>Trades</span><strong>{analysis.summary.trades}</strong>
                    <span>Win Rate</span><strong>{analysis.summary.win_rate}%</strong>
                    <span>Average PnL</span><strong>{analysis.summary.average_pnl}</strong>
                  </div>
                  <div className="mt-4 space-y-2 text-slate-300">
                    {analysis.suggestions.map((item) => <p key={item}>{item}</p>)}
                  </div>
                </>
              ) : (
                <p className="text-rose-300">{analysis.error}</p>
              )}
            </div>
          )}
        </div>
      </div>
    </section>
  )
}
