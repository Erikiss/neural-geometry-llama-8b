export function ProgressStepper({ message, pct }) {
  return (
    <div className="flex flex-col gap-3">
      <div className="flex justify-between text-sm text-[#8b949e]">
        <span>{message}</span>
        <span>{pct}%</span>
      </div>
      <div className="h-1.5 bg-[#21262d] rounded-full overflow-hidden">
        <div
          className="h-full bg-[#238636] rounded-full transition-all duration-300"
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  )
}
