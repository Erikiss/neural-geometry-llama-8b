import Plot from 'react-plotly.js'

export function GeometryPlot({ figure }) {
  const layout = {
    ...figure.layout,
    autosize: true,
    paper_bgcolor: '#0d1117',
    plot_bgcolor: '#0d1117',
  }

  return (
    <div className="w-full rounded-xl overflow-hidden border border-[#21262d]">
      <Plot
        data={figure.data}
        layout={layout}
        useResizeHandler
        style={{ width: '100%', height: '580px' }}
        config={{
          responsive: true,
          displayModeBar: true,
          displaylogo: false,
          modeBarButtonsToRemove: ['toImage', 'sendDataToCloud'],
        }}
      />
    </div>
  )
}
