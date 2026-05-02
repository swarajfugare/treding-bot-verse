export default function StatusPill({ active, label }) {
  return (
    <span
      className={`inline-flex min-h-8 items-center rounded-full px-3 text-sm font-semibold ${
        active ? 'bg-emerald-500/15 text-emerald-300' : 'bg-slate-800 text-slate-400'
      }`}
    >
      {label}
    </span>
  )
}
