import { useState } from 'react'
import { ConceptInput } from './components/ConceptInput'
import { GeometryPlot } from './components/GeometryPlot'
import { ProgressStepper } from './components/ProgressStepper'
import { ResultMetadata } from './components/ResultMetadata'

const API_BASE = import.meta.env.VITE_API_URL ?? ''

export default function App() {
  const [query, setQuery] = useState('')
  const [layer, setLayer] = useState(28)
  const [loading, setLoading] = useState(false)
  const [progress, setProgress] = useState(null)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)

  const handleSubmit = async () => {
    if (!query.trim() || loading) return
    setLoading(true)
    setResult(null)
    setError(null)
    setProgress({ message: 'Starting…', pct: 0 })

    try {
      const res = await fetch(`${API_BASE}/api/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ concept: query.trim(), layer }),
      })

      if (!res.ok) throw new Error(`Server error ${res.status}`)

      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() ?? ''

        for (const line of lines) {
          if (!line.startsWith('data:')) continue
          const raw = line.slice(5).trim()
          if (!raw) continue

          let parsed
          try { parsed = JSON.parse(raw) } catch { continue }

          if (parsed.pct !== undefined) {
            setProgress({ message: parsed.message, pct: parsed.pct })
          }
          if (parsed.concept_name) {
            setResult(parsed)
            setLoading(false)
            setProgress(null)
          }
          if (parsed.message && parsed.pct === undefined && !parsed.concept_name) {
            setError(parsed.message)
            setLoading(false)
            setProgress(null)
          }
        }
      }
    } catch (e) {
      setError(e.message)
      setLoading(false)
      setProgress(null)
    }
  }

  return (
    <div className="min-h-screen bg-[#0d1117] text-[#e6edf3]">
      <div className="max-w-5xl mx-auto px-4 py-10 flex flex-col gap-8">

        <div>
          <h1 className="text-2xl font-bold text-white mb-1">Exploring manifold structure in Llama</h1>
          <p className="text-[#8b949e] text-sm leading-relaxed">
            Visualize how Llama 3.1 8B represents ordered concepts as geometric structures in activation space.
            Inspired by{' '}
            <a
              href="https://arxiv.org/abs/2605.05115"
              target="_blank"
              rel="noopener noreferrer"
              className="text-[#58a6ff] hover:underline"
            >
              Goodfire's manifold steering research
            </a>
            .{' '}
            <a
              href="https://github.com/Talib-Mirza/Neural-Geometry-Llama-8b"
              target="_blank"
              rel="noopener noreferrer"
              className="text-[#58a6ff] hover:underline"
            >
              View on GitHub
            </a>
            .
          </p>
        </div>

        <div className="bg-[#161b22] border border-[#30363d] rounded-xl p-5">
          <ConceptInput
            query={query}
            setQuery={setQuery}
            layer={layer}
            setLayer={setLayer}
            onSubmit={handleSubmit}
            loading={loading}
          />
        </div>

        {loading && progress && (
          <div className="bg-[#161b22] border border-[#30363d] rounded-xl p-5">
            <ProgressStepper message={progress.message} pct={progress.pct} />
          </div>
        )}

        {error && (
          <div className="bg-[#1a1a2e] border border-[#da3633] rounded-xl p-4 text-[#f85149] text-sm">
            {error}
          </div>
        )}

        {result && (
          <div className="flex flex-col gap-5">
            <GeometryPlot figure={result.figure} />
            <ResultMetadata result={result} />
          </div>
        )}

        {!loading && !result && !error && (
          <div className="text-center py-16 text-[#484f58] text-sm">
            <div className="text-4xl mb-3">⬡</div>
            <div>Enter a concept above to explore its neural geometry</div>
            <div className="mt-2 text-xs">
              Try: "days of the week" · "musical notes" · "planets from the sun" · "seasons"
            </div>
          </div>
        )}

      </div>
    </div>
  )
}
