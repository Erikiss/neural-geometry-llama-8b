import { useEffect, useRef } from 'react'
import Plotly from 'plotly.js-dist'

export function GeometryPlot({ figure }) {
  const ref = useRef(null)

  useEffect(() => {
    if (!ref.current || !figure) return
    const layout = {
      ...figure.layout,
      autosize: true,
      paper_bgcolor: '#0d1117',
      plot_bgcolor: '#0d1117',
    }
    Plotly.react(ref.current, figure.data, layout, {
      responsive: true,
      displayModeBar: true,
      displaylogo: false,
      modeBarButtonsToRemove: ['toImage', 'sendDataToCloud'],
    })
  }, [figure])

  return (
    <div className="w-full rounded-xl overflow-hidden border border-[#21262d]">
      <div ref={ref} style={{ width: '100%', height: '580px' }} />
    </div>
  )
}
