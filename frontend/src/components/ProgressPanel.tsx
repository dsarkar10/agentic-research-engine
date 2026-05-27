interface Step {
  agent: string
  message: string
}

interface ProgressPanelProps {
  steps: Step[]
  currentAgent: string | null
}

const LABELS: Record<string, string> = {
  search_web: "Searching web",
  assess_depth: "Assessing depth",
  deep_search: "Deep searching",
  extract_info: "Extracting info",
  verify_sources: "Verifying sources",
  write_report: "Writing report",
}

export default function ProgressPanel({ steps, currentAgent }: ProgressPanelProps) {
  if (steps.length === 0) return null

  return (
    <div className="progress-panel">
      {steps.map((step, i) => {
        const isActive = step.agent === currentAgent
        const isPast = !isActive && i < steps.length - 1
        return (
          <div key={i} className={`progress-step ${isActive ? "active" : ""}`}>
            {isActive && <div className="spinner" />}
            {isPast && <span className="check">✓</span>}
            {!isPast && !isActive && <span style={{ width: 14, flexShrink: 0 }} />}
            <span className="label">{step.message}</span>
          </div>
        )
      })}
    </div>
  )
}
