export interface ProgressEvent {
  agent: string
  message: string
}

export interface ReportChunk {
  chunk: string
}

export interface KeyConcept {
  concept: string
  explanation: string
}

export interface CodeExample {
  language: string
  description: string
  code: string
}

export interface Tool {
  name: string
  url: string
  description: string
}

export interface Source {
  title: string
  url: string
  confidence: string
}

export interface ReportMetadata {
  model: string
  deep_search_used: boolean
  sources_count: number
  error?: string
}

export interface ResearchReport {
  query: string
  overview: string
  key_concepts: KeyConcept[]
  code_examples: CodeExample[]
  tools_and_libraries: Tool[]
  best_practices: string[]
  sources: Source[]
  metadata: ReportMetadata
}

export interface ErrorEvent {
  message: string
}

export type SSEHandler = {
  onStatus?: (event: ProgressEvent) => void
  onReportChunk?: (event: ReportChunk) => void
  onComplete?: (event: ResearchReport) => void
  onError?: (event: ErrorEvent) => void
}

export function startResearch(
  query: string,
  deepSearch: boolean,
  handlers: SSEHandler,
): AbortController {
  const controller = new AbortController()

  fetch("/api/research", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, deep_search: deepSearch }),
    signal: controller.signal,
  })
    .then(async (response) => {
      if (!response.ok) {
        handlers.onError?.({ message: `Server error: ${response.status}` })
        return
      }

      const reader = response.body?.getReader()
      if (!reader) {
        handlers.onError?.({ message: "No response body" })
        return
      }

      const decoder = new TextDecoder()
      let buffer = ""

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split("\n")
        buffer = lines.pop() || ""

        let eventType = ""
        for (const line of lines) {
          if (line.startsWith("event: ")) {
            eventType = line.slice(7).trim()
          } else if (line.startsWith("data: ")) {
            const data = line.slice(6)
            try {
              const parsed = JSON.parse(data)
              switch (eventType) {
                case "status":
                  handlers.onStatus?.(parsed as ProgressEvent)
                  break
                case "report_chunk":
                  handlers.onReportChunk?.(parsed as ReportChunk)
                  break
                case "complete":
                  handlers.onComplete?.(parsed as ResearchReport)
                  break
                case "error":
                  handlers.onError?.(parsed as ErrorEvent)
                  break
              }
            } catch {
              // skip malformed data
            }
            eventType = ""
          }
        }
      }
    })
    .catch((err) => {
      if (err.name !== "AbortError") {
        handlers.onError?.({ message: err.message })
      }
    })

  return controller
}
