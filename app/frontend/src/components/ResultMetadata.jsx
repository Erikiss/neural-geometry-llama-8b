import { useState } from 'react'

export function ResultMetadata({ result }) {
  const [open, setOpen] = useState(false)
  const totalVar = result.pca_variance.reduce((a, b) => a + b, 0)

  return (
    <div className="flex flex-col gap-4">
      {/* Stats row */}
      <div className="flex flex-wrap gap-2">
        <Chip label={result.concept_name} color="blue" />
        <Chip label={`Layer ${result.layer}`} color="gray" />
        <Chip label={result.is_cyclic ? 'Cyclic ↻' : 'Linear →'} color={result.is_cyclic ? 'purple' : 'green'} />
        <Chip label={`${(totalVar * 100).toFixed(0)}% variance in 3D`} color="gray" />
        <Chip label={`${result.n_prompts} prompts`} color="gray" />
        {result.cache_hit && <Chip label="⚡ Cache hit" color="yellow" />}
      </div>

      {/* PCA variance bars */}
      <div className="grid grid-cols-3 gap-2">
        {result.pca_variance.map((v, i) => (
          <div key={i} className="bg-[#161b22] border border-[#21262d] rounded-lg p-3 text-center">
            <div className="text-[#8b949e] text-xs mb-1">PC{i + 1}</div>
            <div className="text-[#e6edf3] font-semibold text-sm">{(v * 100).toFixed(1)}%</div>
            <div className="mt-1.5 h-1 bg-[#21262d] rounded-full overflow-hidden">
              <div className="h-full bg-[#58a6ff] rounded-full" style={{ width: `${v * 100}%` }} />
            </div>
          </div>
        ))}
      </div>

      {/* Concept values */}
      <div className="flex flex-wrap gap-1.5">
        {result.values.map(v => (
          <span key={v} className="text-xs bg-[#21262d] text-[#8b949e] rounded px-2 py-0.5">{v}</span>
        ))}
      </div>

      {/* Prompts collapsible */}
      <div className="border border-[#21262d] rounded-lg overflow-hidden">
        <button
          onClick={() => setOpen(o => !o)}
          className="w-full flex justify-between items-center px-4 py-3 text-sm text-[#8b949e] hover:bg-[#161b22] transition-colors"
        >
          <span>Prompts used ({result.prompts.length})</span>
          <span>{open ? '▲' : '▼'}</span>
        </button>
        {open && (
          <div className="divide-y divide-[#21262d] max-h-64 overflow-y-auto">
            {result.prompts.map((p, i) => (
              <div key={i} className="px-4 py-2.5 flex justify-between gap-4 text-xs">
                <span className="text-[#e6edf3]">{p.prompt}</span>
                <span className="text-[#58a6ff] whitespace-nowrap font-medium shrink-0">→ {p.answer}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

function Chip({ label, color }) {
  const colors = {
    blue:   'bg-[#1a3a5c] text-[#58a6ff]',
    gray:   'bg-[#21262d] text-[#8b949e]',
    purple: 'bg-[#2d1b69] text-[#a78bfa]',
    green:  'bg-[#1a3a2c] text-[#3fb950]',
    yellow: 'bg-[#2d2a1a] text-[#d29922]',
  }
  return (
    <span className={`text-xs font-medium px-2.5 py-1 rounded-full ${colors[color] ?? colors.gray}`}>
      {label}
    </span>
  )
}
