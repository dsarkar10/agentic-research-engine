import { useState, useCallback, useRef } from "react"
import SearchBar from "./components/SearchBar"
import ProgressPanel from "./components/ProgressPanel"
import ReportView from "./components/ReportView"
import { startResearch, type ProgressEvent, type ResearchReport, type ErrorEvent } from "./api/client"

interface Step {
  agent: string
  message: string
}

export default function App() {
  const [steps, setSteps] = useState<Step[]>([])
  const [currentAgent, setCurrentAgent] = useState<string | null>(null)
  const [report, setReport] = useState<ResearchReport | null>(null)
  const [rawText, setRawText] = useState("")
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const abortRef = useRef<AbortController | null>(null)

  const handleSearch = useCallback((query: string, deepSearch: boolean) => {
    abortRef.current?.abort()
    setSteps([])
    setCurrentAgent(null)
    setReport(null)
    setRawText("")
    setError(null)
    setLoading(true)

    abortRef.current = startResearch(query, deepSearch, {
      onStatus: (e: ProgressEvent) => {
        setSteps((prev) => {
          if (prev.some((s) => s.agent === e.agent)) return prev
          return [...prev, { agent: e.agent, message: e.message }]
        })
        setCurrentAgent(e.agent)
      },
      onReportChunk: (e) => {
        setCurrentAgent("write_report")
        setRawText((prev) => prev + e.chunk)
      },
      onComplete: (e: ResearchReport) => {
        setReport(e)
        setRawText("")
        setCurrentAgent(null)
        setLoading(false)
      },
      onError: (e: ErrorEvent) => {
        setError(e.message)
        setCurrentAgent(null)
        setLoading(false)
      },
    })
  }, [])

  return (
    <div>
      <header>
        <h1>Agentic Research Engine</h1>
        <p>Multi-agent system — LangGraph + Groq + DuckDuckGo — outputs structured JSON</p>
      </header>

      <SearchBar onSearch={handleSearch} disabled={loading} />

      {error && <div className="error-banner">{error}</div>}

      <ProgressPanel steps={steps} currentAgent={currentAgent} />

      {!loading && !report && !rawText && !error && (
        <div className="placeholder">
          <h2>Enter a tech research topic</h2>
          <p>The agent will search the web, extract code examples, verify sources, and write a structured JSON report.</p>
        </div>
      )}

      {(report || rawText) && (
        <ReportView report={report!} rawText={rawText} />
      )}
    </div>
  )
}
