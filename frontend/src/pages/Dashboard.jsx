import { Activity, CircleDollarSign, Download, Play, Square, TrendingUp } from 'lucide-react'
import StatCard from '../components/StatCard.jsx'
import StatusPill from '../components/StatusPill.jsx'
import TradingChart from '../components/TradingChart.jsx'

function money(value, currency = 'USDT') {
  return `${Number(value || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })} ${currency}`
}

function signalClass(signal) {
  if (signal === 'BUY') return 'border-emerald-500/40 bg-emerald-500/10 text-emerald-200'
  if (signal === 'SELL') return 'border-rose-500/40 bg-rose-500/10 text-rose-200'
  return 'border-slate-700 bg-slate-800/70 text-slate-300'
}

export default function Dashboard({
  dashboard,
  chartCandles,
  selectedCoin,
  onSelectCoin,
  onRefresh,
  onControlBot,
  onExport,
}) {
  const status = dashboard?.bot_status || {}
  const activeTrade = dashboard?.active_trade
  const trades = dashboard?.trades || []
  const scanner = dashboard?.scanner || []
  const balance = dashboard?.balance_detail || {}
  const currentBalance = Number(balance.usdt_equivalent || 0)
  const startingBalance = Number(balance.starting_balance ?? dashboard?.starting_balance ?? (status.mode === 'PAPER' ? 10000 : currentBalance))
  const realPnl = currentBalance - startingBalance
  const realPnlPercent = startingBalance > 0 ? (realPnl / startingBalance) * 100 : 0

  return (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-6">
        <StatCard icon={CircleDollarSign} label="INR Balance" value={money(balance.inr_balance, 'INR')} tone="amber" />
        <StatCard icon={CircleDollarSign} label={status.mode === 'LIVE' ? 'USD Trading Balance' : 'USDT Equivalent'} value={money(balance.usdt_equivalent)} tone="emerald" />
        <StatCard icon={CircleDollarSign} label="Starting Balance" value={money(startingBalance)} tone="cyan" />
        <StatCard icon={TrendingUp} label="Real PnL" value={`${money(realPnl)} (${realPnlPercent.toFixed(2)}%)`} tone={realPnl >= 0 ? 'emerald' : 'rose'} />
        <StatCard icon={Activity} label="Bot Status" value={status.running ? 'Running' : 'Stopped'} tone={status.running ? 'emerald' : 'amber'} />
        <StatCard icon={TrendingUp} label="Best Coin" value={dashboard?.best_coin?.coin || 'Scanning'} tone="cyan" />
      </div>

      {balance.error && (
        <div className="rounded-lg border border-rose-500/30 bg-rose-500/10 px-4 py-3 text-sm font-semibold text-rose-100">
          {balance.error}
        </div>
      )}

      <section className="panel rounded-lg p-5">
        <div className="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
          <div>
            <div className="flex flex-wrap items-center gap-3">
              <h2 className="text-xl font-bold text-slate-50">Multi-Coin Scanner</h2>
              <StatusPill active={status.running} label={status.running ? `${status.mode} Bot Running` : `${status.mode || 'PAPER'} Bot Stopped`} />
            </div>
            <p className="mt-2 max-w-3xl text-sm text-slate-400">
              BTC, ETH, and SOL are scored with EMA distance, RSI bands, multi-timeframe trend alignment, and volume filters.
            </p>
          </div>
          <div className="flex flex-wrap gap-3">
            <button
              type="button"
              onClick={() => onControlBot(status.running ? 'stop' : 'start')}
              className={`focus-ring inline-flex h-11 items-center gap-2 rounded-lg px-4 font-semibold text-white ${
                status.running ? 'bg-rose-600 hover:bg-rose-700' : 'bg-emerald-600 hover:bg-emerald-700'
              }`}
            >
              {status.running ? <Square size={18} /> : <Play size={18} />}
              {status.running ? 'Stop Bot' : 'Start Bot'}
            </button>
            <button
              type="button"
              onClick={onExport}
              className="focus-ring inline-flex h-11 items-center gap-2 rounded-lg border border-slate-700 bg-slate-950 px-4 font-semibold text-slate-200 hover:bg-slate-800"
            >
              <Download size={18} />
              Export Trades
            </button>
            <button
              type="button"
              onClick={onRefresh}
              className="focus-ring h-11 rounded-lg border border-slate-700 bg-slate-950 px-4 font-semibold text-slate-200 hover:bg-slate-800"
            >
              Refresh
            </button>
          </div>
        </div>

        <div className="mt-5 grid gap-3 md:grid-cols-3">
          {scanner.map((coin) => (
            <button
              type="button"
              key={coin.coin}
              onClick={() => onSelectCoin(coin.coin)}
              className={`rounded-lg border p-4 text-left transition ${signalClass(coin.signal)} ${selectedCoin === coin.coin ? 'ring-2 ring-cyan-400' : ''}`}
            >
              <div className="flex items-center justify-between gap-3">
                <strong className="text-lg text-slate-50">{coin.coin}</strong>
                <span className="rounded-full bg-slate-950/60 px-2 py-1 text-xs font-bold">{coin.signal}</span>
              </div>
              <div className="mt-3 grid grid-cols-2 gap-2 text-sm">
                <span className="text-slate-400">Price</span><span className="text-right font-semibold">{money(coin.price)}</span>
                <span className="text-slate-400">Confidence</span><span className="text-right font-semibold">{coin.confidence}%</span>
                <span className="text-slate-400">Trend</span><span className="text-right font-semibold">{coin.trend}</span>
              </div>
            </button>
          ))}
        </div>
      </section>

      <section className="grid gap-5 xl:grid-cols-[1.35fr_0.65fr]">
        <div className="panel rounded-lg p-5">
          <div className="mb-4 flex items-center justify-between gap-3">
            <h3 className="text-lg font-bold text-slate-50">{selectedCoin} Live Chart</h3>
            <div className="flex gap-4 text-xs font-semibold text-slate-400">
              <span className="text-cyan-300">EMA 9</span>
              <span className="text-amber-300">EMA 21</span>
            </div>
          </div>
          <TradingChart candles={chartCandles} trades={trades} symbol={selectedCoin} />
        </div>

        <div className="panel rounded-lg p-5">
          <h3 className="text-lg font-bold text-slate-50">Active Trade</h3>
          {activeTrade ? (
            <div className="mt-4 space-y-3 text-sm">
              <div className="flex justify-between"><span className="text-slate-400">Coin</span><strong>{activeTrade.symbol}</strong></div>
              <div className="flex justify-between"><span className="text-slate-400">Side</span><strong>{activeTrade.side}</strong></div>
              <div className="flex justify-between"><span className="text-slate-400">Entry</span><strong>{money(activeTrade.entry_price)}</strong></div>
              <div className="flex justify-between"><span className="text-slate-400">Stop Loss</span><strong>{money(activeTrade.stop_loss)}</strong></div>
              <div className="flex justify-between"><span className="text-slate-400">Take Profit</span><strong>{money(activeTrade.take_profit)}</strong></div>
              <p className="rounded-lg bg-slate-950 p-3 text-slate-300">{activeTrade.reason}</p>
            </div>
          ) : (
            <p className="mt-4 rounded-lg bg-slate-950 p-4 text-sm text-slate-400">No active {status.mode || 'PAPER'} trade. Duplicate trade protection is active.</p>
          )}
        </div>
      </section>

      <section className="panel rounded-lg p-5">
        <h3 className="text-lg font-bold text-slate-50">Recent {status.mode || 'PAPER'} Trades</h3>
        <div className="mt-4 overflow-hidden rounded-lg border border-slate-800">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-950 text-slate-400">
              <tr>
                <th className="px-3 py-2">Coin</th>
                <th className="px-3 py-2">Side</th>
                <th className="px-3 py-2">Status</th>
                <th className="px-3 py-2">Confidence</th>
                <th className="px-3 py-2">PnL</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800 bg-slate-900">
              {trades.length === 0 ? (
                <tr><td className="px-3 py-4 text-slate-500" colSpan="5">No trades logged in this mode.</td></tr>
              ) : (
                trades.slice(0, 8).map((trade) => (
                  <tr key={trade.id}>
                    <td className="px-3 py-3 font-semibold text-slate-100">{trade.symbol}</td>
                    <td className="px-3 py-3">{trade.side}</td>
                    <td className="px-3 py-3 capitalize">{trade.status}</td>
                    <td className="px-3 py-3">{trade.confidence}%</td>
                    <td className={`px-3 py-3 font-semibold ${Number(trade.pnl) >= 0 ? 'text-emerald-300' : 'text-rose-300'}`}>{money(trade.pnl)}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  )
}
