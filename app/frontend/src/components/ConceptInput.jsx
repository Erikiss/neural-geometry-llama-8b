export function ConceptInput({ query, setQuery, layer, setLayer, onSubmit, loading }) {
  return (
    <div className="flex flex-col gap-3">
      <div className="flex gap-2">
        <input
          type="text"
          value={query}
          onChange={e => setQuery(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && !loading && query.trim() && onSubmit()}
          placeholder="Enter a concept… e.g. 'days of the week', 'musical notes', 'seasons'"
          className="flex-1 bg-[#161b22] border border-[#30363d] rounded-lg px-4 py-3 text-[#e6edf3] placeholder-[#484f58] focus:outline-none focus:border-[#58a6ff] text-sm transition-colors"
          disabled={loading}
        />
        <button
          onClick={onSubmit}
          disabled={loading || !query.trim()}
          className="bg-[#238636] hover:bg-[#2ea043] disabled:opacity-40 disabled:cursor-not-allowed text-white font-semibold px-5 py-3 rounded-lg text-sm transition-colors whitespace-nowrap"
        >
          {loading ? 'Running…' : 'Visualize →'}
        </button>
      </div>
      <div className="flex items-center gap-3">
        <label className="text-[#8b949e] text-xs whitespace-nowrap">Layer (0–31)</label>
        <input
          type="number"
          min={0}
          max={31}
          value={layer}
          onChange={e => setLayer(Math.max(0, Math.min(31, parseInt(e.target.value) || 0)))}
          className="w-16 bg-[#161b22] border border-[#30363d] rounded-md px-2 py-1 text-[#e6edf3] text-sm focus:outline-none focus:border-[#58a6ff]"
          disabled={loading}
        />
        <span className="text-[#484f58] text-xs">default: 28 (richest semantic layer for Llama 3.1 8B)</span>
      </div>
    </div>
  )
}
