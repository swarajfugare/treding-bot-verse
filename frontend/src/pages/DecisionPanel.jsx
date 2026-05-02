import { Brain, Gauge, RefreshCw } from 'lucide-react'

function Bar({ label, value, color }) {
  return (
    <div>
      <div className="mb-2 flex justify-between text-sm">
        <span className="text-slate-400">{label}</span>
        <strong className="text-slate-100">{value}</strong>
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-slate-800">
        <div className={`h-full ${color}`} style={{ width: `${Math.min(Number(value), 100)}%` }} />
      </div>
    </div>
  )
}

export default function DecisionPanel({ decision, onRefresh }) {
  const confidence = Number(decision?.confidence || 0)
  const components = decision?.components || {}
  const scan = decision?.scan || []
  const signalTone = decision?.signal === 'BUY' ? 'text-emerald-300 bg-emerald-500/15' : decision?.signal === 'SELL' ? 'text-rose-300 bg-rose-500/15' : 'text-slate-300 bg-slate-800'

  return (
    <section className="panel rounded-lg p-5">
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h2 className="text-xl font-bold text-slate-50">Bot Thinking</h2>
          <p className="mt-2 text-sm text-slate-400">Every signal shows the exact filters that passed or blocked the trade.</p>
        </div>
        <button
          type="button"
          onClick={onRefresh}
          className="focus-ring inline-flex h-11 items-center gap-2 rounded-lg border border-slate-700 bg-slate-950 px-4 font-semibold text-slate-200 hover:bg-slate-800"
        >
          <RefreshCw size={18} />
          Refresh
        </button>
      </div>

      <div className="mt-6 grid gap-4 lg:grid-cols-[0.9fr_1.1fr]">
        <div className="rounded-lg border border-slate-800 bg-slate-950 p-5">
          <div className="flex items-center gap-3">
            <div className="grid h-11 w-11 place-items-center rounded-lg bg-cyan-500/15 text-cyan-300">
              <Brain size={24} />
            </div>
            <div>
              <p className="text-sm font-medium text-slate-400">Best Selected Coin</p>
              <p className="text-2xl font-black text-slate-50">{decision?.coin || '...'}</p>
            </div>
          </div>

          <div className="mt-5 grid grid-cols-2 gap-3 text-sm">
            <div className="rounded-lg bg-slate-900 p-3"><span className="text-slate-500">Signal</span><p className={`mt-2 inline-flex rounded-full px-3 py-1 font-bold ${signalTone}`}>{decision?.signal || 'HOLD'}</p></div>
            <div className="rounded-lg bg-slate-900 p-3"><span className="text-slate-500">Price</span><p className="mt-2 font-bold text-slate-100">{decision?.price ?? '...'}</p></div>
            <div className="rounded-lg bg-slate-900 p-3"><span className="text-slate-500">EMA 9</span><p className="mt-2 font-bold text-cyan-300">{decision?.ema9 ?? '...'}</p></div>
            <div className="rounded-lg bg-slate-900 p-3"><span className="text-slate-500">EMA 21</span><p className="mt-2 font-bold text-amber-300">{decision?.ema21 ?? '...'}</p></div>
            <div className="rounded-lg bg-slate-900 p-3"><span className="text-slate-500">RSI</span><p className="mt-2 font-bold text-slate-100">{decision?.rsi ?? '...'}</p></div>
            <div className="rounded-lg bg-slate-900 p-3"><span className="text-slate-500">Trend</span><p className="mt-2 font-bold text-slate-100">{decision?.trend ?? '...'}</p></div>
          </div>

          <div className="mt-5 rounded-lg bg-slate-900 p-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-slate-300"><Gauge size={18} /> Confidence</div>
              <strong className="text-xl text-slate-50">{confidence}%</strong>
            </div>
            <div className="mt-3 h-3 overflow-hidden rounded-full bg-slate-800">
              <div className="h-full rounded-full bg-cyan-400 transition-all" style={{ width: `${Math.min(confidence, 100)}%` }} />
            </div>
          </div>
        </div>

        <div className="rounded-lg border border-slate-800 bg-slate-950 p-5">
          <h3 className="font-bold text-slate-50">Reason</h3>
          <p className="mt-3 rounded-lg bg-slate-900 p-4 text-sm leading-6 text-slate-300">
            {decision?.reason || 'Waiting for the first decision.'}
          </p>

          <div className="mt-5 space-y-4">
            <Bar label="EMA crossover" value={components.ema_crossover || 0} color="bg-cyan-400" />
            <Bar label="RSI quality" value={components.rsi_quality || 0} color="bg-violet-400" />
            <Bar label="Trend alignment" value={components.trend_alignment || 0} color="bg-emerald-400" />
            <Bar label="Volume" value={components.volume || 0} color="bg-amber-400" />
          </div>
        </div>
      </div>

      <div className="mt-5 grid gap-3 md:grid-cols-3">
        {scan.map((coin) => (
          <div key={coin.coin} className="rounded-lg border border-slate-800 bg-slate-950 p-4">
            <div className="flex items-center justify-between">
              <strong className="text-slate-50">{coin.coin}</strong>
              <span className="text-sm font-bold text-slate-300">{coin.confidence}%</span>
            </div>
            <p className="mt-2 text-sm text-slate-400">{coin.reason}</p>
          </div>
        ))}
      </div>
    </section>
  )
}
