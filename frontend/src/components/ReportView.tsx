import type { ResearchReport } from "../api/client"

interface ReportViewProps {
  report: ResearchReport
  rawText: string
}

function CodeBlock({ code, language }: { code: string; language: string }) {
  return (
    <pre>
      <code>{code}</code>
    </pre>
  )
}

export default function ReportView({ report, rawText }: ReportViewProps) {
  if (rawText && !report) {
    return (
      <div className="report">
        <pre style={{ whiteSpace: "pre-wrap", fontSize: "0.8125rem" }}>{rawText}</pre>
      </div>
    )
  }

  return (
    <div>
      <div className="report">
        <h1>{report.query}</h1>

        <section>
          <h2>Overview</h2>
          <p>{report.overview}</p>
        </section>

        {report.key_concepts.length > 0 && (
          <section>
            <h2>Key Concepts</h2>
            {report.key_concepts.map((c, i) => (
              <div key={i}>
                <h3>{c.concept}</h3>
                <p>{c.explanation}</p>
              </div>
            ))}
          </section>
        )}

        {report.code_examples.length > 0 && (
          <section>
            <h2>Code Examples</h2>
            {report.code_examples.map((ex, i) => (
              <div key={i}>
                <h3>{ex.description}</h3>
                <p style={{ fontSize: "0.8125rem", color: "var(--text-muted)", marginBottom: "0.25rem" }}>
                  Language: {ex.language}
                </p>
                <CodeBlock code={ex.code} language={ex.language} />
              </div>
            ))}
          </section>
        )}

        {report.tools_and_libraries.length > 0 && (
          <section>
            <h2>Tools & Libraries</h2>
            <ul>
              {report.tools_and_libraries.map((t, i) => (
                <li key={i}>
                  <strong>{t.name}</strong>
                  {t.url && (
                    <>
                      {" — "}
                      <a href={t.url} target="_blank" rel="noopener noreferrer">{t.url}</a>
                    </>
                  )}
                  <br />
                  {t.description}
                </li>
              ))}
            </ul>
          </section>
        )}

        {report.best_practices.length > 0 && (
          <section>
            <h2>Best Practices</h2>
            <ul>
              {report.best_practices.map((p, i) => (
                <li key={i}>{p}</li>
              ))}
            </ul>
          </section>
        )}
      </div>

      {report.sources.length > 0 && (
        <div className="sources">
          <h3>Sources</h3>
          {report.sources.map((s, i) => (
            <a key={i} href={s.url} target="_blank" rel="noopener noreferrer">
              {s.title} {s.confidence && <span style={{ opacity: 0.5 }}>({s.confidence})</span>}
            </a>
          ))}
        </div>
      )}

      {report.metadata && (
        <div style={{ marginTop: "1rem", fontSize: "0.75rem", color: "var(--text-muted)" }}>
          Model: {report.metadata.model} | Deep search: {report.metadata.deep_search_used ? "yes" : "no"} |
          Sources: {report.metadata.sources_count}
        </div>
      )}
    </div>
  )
}
