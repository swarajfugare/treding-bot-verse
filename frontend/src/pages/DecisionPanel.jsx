import { Brain, Gauge, RefreshCw } from 'lucide-react'

function Bar({ label, value, color }) {
  const numericValue = Number(value || 0)
  return (
    <div>
      <div className="mb-2 flex justify-between text-sm">
        <span className="text-slate-400">{label}</span>
        <strong className="text-slate-100">{numericValue}</strong>
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-slate-800">
        <div className={`h-full ${color}`} style={{ width: `${Math.min(numericValue, 100)}%` }} />
      </div>
    </div>
  )
}

function Metric({ label, value, className = 'text-slate-100' }) {
  return (
    <div className="rounded-lg bg-slate-900 p-3">
      <span className="text-slate-500">{label}</span>
      <p className={`mt-2 break-words font-bold ${className}`}>{value ?? '...'}</p>
    </div>
  )
}

export default function DecisionPanel({ decision, onRefresh }) {
  const confidence = Number(decision?.confidence || 0)
  const components = decision?.components || {}
  const scan = decision?.scan || []
  const signalTone = decision?.signal === 'BUY' ? 'text-emerald-300 bg-emerald-500/15' : decision?.signal === 'SELL' ? 'text-rose-300 bg-rose-500/15' : 'text-slate-300 bg-slate-800'
  const indicators = decision?.indicators_used || ['EMA50/EMA200 trend filter', 'MACD(12,26,9)', 'RSI(14)', 'Volume average', '1m + 5m trend alignment']

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
          className="focus-ring inline-flex h-11 items-center justify-center gap-2 rounded-lg border border-slate-700 bg-slate-950 px-4 font-semibold text-slate-200 hover:bg-slate-800"
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

          <div className="mt-5 grid grid-cols-1 gap-3 text-sm sm:grid-cols-2">
            <div className="rounded-lg bg-slate-900 p-3"><span className="text-slate-500">Signal</span><p className={`mt-2 inline-flex rounded-full px-3 py-1 font-bold ${signalTone}`}>{decision?.signal || 'HOLD'}</p></div>
            <Metric label="Price" value={decision?.price} />
            <Metric label="EMA 20" value={decision?.ema20 ?? decision?.ema9} className="text-cyan-300" />
            <Metric label="EMA 50" value={decision?.ema50 ?? decision?.ema21} className="text-amber-300" />
            <Metric label="EMA 200" value={decision?.ema200} className="text-emerald-300" />
            <Metric label="RSI 14" value={decision?.rsi} />
            <Metric label="MACD" value={decision?.macd} className="text-sky-300" />
            <Metric label="MACD Signal" value={decision?.macd_signal} className="text-violet-300" />
            <Metric label="Volume" value={decision?.volume} />
            <Metric label="Trend" value={decision?.trend} />
            <Metric label="Stop Loss" value={decision?.stop_loss ?? 'Waiting'} className="text-rose-300" />
            <Metric label="Take Profit" value={decision?.take_profit ?? 'Waiting'} className="text-emerald-300" />
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
            <Bar label="EMA trend filter" value={components.trend_filter || 0} color="bg-cyan-400" />
            <Bar label="MACD confirmation" value={components.macd_confirmation || 0} color="bg-sky-400" />
            <Bar label="RSI quality" value={components.rsi_quality || 0} color="bg-violet-400" />
            <Bar label="Trend alignment" value={components.trend_alignment || 0} color="bg-emerald-400" />
            <Bar label="Volume" value={components.volume || 0} color="bg-amber-400" />
            <Bar label="Risk filter" value={components.risk_filter || 0} color="bg-rose-400" />
          </div>

          <div className="mt-5 rounded-lg bg-slate-900 p-4">
            <h4 className="text-sm font-bold text-slate-200">Indicators Used</h4>
            <div className="mt-3 flex flex-wrap gap-2">
              {indicators.map((item) => (
                <span key={item} className="rounded-full bg-slate-950 px-3 py-1 text-xs font-semibold text-slate-300">{item}</span>
              ))}
            </div>
          </div>
        </div>
      </div>

      <div className="mt-5 grid gap-3 md:grid-cols-3">
        {scan.length === 0 ? (
          <div className="rounded-lg border border-slate-800 bg-slate-950 p-4 text-sm text-slate-400 md:col-span-3">
            Waiting for the scanner to publish decisions.
          </div>
        ) : scan.map((coin) => (
          <div key={coin.coin} className="rounded-lg border border-slate-800 bg-slate-950 p-4">
            <div className="flex items-center justify-between gap-3">
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
