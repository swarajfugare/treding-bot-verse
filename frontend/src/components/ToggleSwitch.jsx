export default function ToggleSwitch({ checked, onChange, label }) {
  return (
    <button
      type="button"
      onClick={() => onChange(!checked)}
      className={`focus-ring inline-flex h-8 w-14 items-center rounded-full p-1 ${
        checked ? 'bg-emerald-500' : 'bg-slate-300'
      }`}
      aria-pressed={checked}
      aria-label={label}
      title={label}
    >
      <span
        className={`h-6 w-6 rounded-full bg-white shadow transition-transform ${
          checked ? 'translate-x-6' : 'translate-x-0'
        }`}
      />
    </button>
  )
}
