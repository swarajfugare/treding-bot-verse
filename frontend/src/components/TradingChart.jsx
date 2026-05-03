import { CandlestickSeries, LineSeries, createChart, createSeriesMarkers } from 'lightweight-charts'
import { useEffect, useRef } from 'react'

function ema(data, period) {
  const multiplier = 2 / (period + 1)
  let previous = data[0]?.close || 0
  return data.map((item, index) => {
    previous = index === 0 ? item.close : item.close * multiplier + previous * (1 - multiplier)
    return { time: item.time, value: Number(previous.toFixed(4)) }
  })
}

export default function TradingChart({ candles = [], trades = [], symbol }) {
  const containerRef = useRef(null)

  useEffect(() => {
    if (!containerRef.current || candles.length === 0) return undefined

    const chart = createChart(containerRef.current, {
      height: containerRef.current.clientHeight || 360,
      layout: { background: { color: '#0b1120' }, textColor: '#94a3b8' },
      grid: { vertLines: { color: '#1e293b' }, horzLines: { color: '#1e293b' } },
      rightPriceScale: { borderColor: '#334155' },
      timeScale: { borderColor: '#334155', timeVisible: true },
      crosshair: { mode: 1 },
    })

    const candleSeries = chart.addSeries(CandlestickSeries, {
      upColor: '#22c55e',
      downColor: '#ef4444',
      borderVisible: false,
      wickUpColor: '#22c55e',
      wickDownColor: '#ef4444',
    })
    candleSeries.setData(candles)

    const ema20 = chart.addSeries(LineSeries, { color: '#38bdf8', lineWidth: 2 })
    ema20.setData(ema(candles, 20))
    const ema50 = chart.addSeries(LineSeries, { color: '#f59e0b', lineWidth: 2 })
    ema50.setData(ema(candles, 50))

    const markers = trades
      .filter((trade) => trade.symbol === symbol)
      .slice(0, 20)
      .map((trade) => ({
        time: candles[candles.length - 1]?.time,
        position: trade.side === 'BUY' ? 'belowBar' : 'aboveBar',
        color: trade.side === 'BUY' ? '#22c55e' : '#ef4444',
        shape: trade.side === 'BUY' ? 'arrowUp' : 'arrowDown',
        text: trade.side,
      }))
    createSeriesMarkers(candleSeries, markers)

    chart.timeScale().fitContent()
    const resizeObserver = new ResizeObserver(() => {
      chart.applyOptions({ width: containerRef.current.clientWidth })
      chart.timeScale().fitContent()
    })
    resizeObserver.observe(containerRef.current)

    return () => {
      resizeObserver.disconnect()
      chart.remove()
    }
  }, [candles, trades, symbol])

  return <div ref={containerRef} className="h-[300px] w-full overflow-hidden rounded-lg border border-slate-800 bg-slate-950 sm:h-[360px]" />
}
