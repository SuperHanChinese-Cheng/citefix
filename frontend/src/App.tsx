import { useCallback, useRef, useState } from 'react'
import './App.css'

interface Issue {
  footnote: number
  rule: string
  description: string
  current: string
  suggested: string
  severity: 'error' | 'warning' | 'info'
  auto_fixable: boolean
}

interface AnalyzeResult {
  footnote_count: number
  total_issues: number
  auto_fixable: number
  needs_review: number
  issues: Issue[]
}

type Mode = 'fix' | 'analyze'

function App() {
  const [mode, setMode] = useState<Mode>('fix')
  const [file, setFile] = useState<File | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [fixedBlob, setFixedBlob] = useState<Blob | null>(null)
  const [fixedName, setFixedName] = useState('')
  const [analyzeResult, setAnalyzeResult] = useState<AnalyzeResult | null>(null)
  const [dragging, setDragging] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  const reset = useCallback(() => {
    setFile(null)
    setError(null)
    setFixedBlob(null)
    setFixedName('')
    setAnalyzeResult(null)
  }, [])

  const handleFile = useCallback((f: File) => {
    if (!f.name.toLowerCase().endsWith('.docx')) {
      setError('Only .docx files are supported')
      return
    }
    setFile(f)
    setError(null)
    setFixedBlob(null)
    setAnalyzeResult(null)
  }, [])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setDragging(false)
    const f = e.dataTransfer.files[0]
    if (f) handleFile(f)
  }, [handleFile])

  const submit = useCallback(async () => {
    if (!file) return
    setLoading(true)
    setError(null)

    const formData = new FormData()
    formData.append('file', file)

    try {
      if (mode === 'fix') {
        const res = await fetch('/fix', { method: 'POST', body: formData })
        if (!res.ok) {
          const err = await res.json().catch(() => ({ detail: 'Upload failed' }))
          throw new Error(err.detail || `Error ${res.status}`)
        }
        const blob = await res.blob()
        const name = file.name.replace('.docx', '_fixed.docx')
        setFixedBlob(blob)
        setFixedName(name)

        const formData2 = new FormData()
        formData2.append('file', file)
        const res2 = await fetch('/analyze', { method: 'POST', body: formData2 })
        if (res2.ok) {
          setAnalyzeResult(await res2.json())
        }
      } else {
        const res = await fetch('/analyze', { method: 'POST', body: formData })
        if (!res.ok) {
          const err = await res.json().catch(() => ({ detail: 'Upload failed' }))
          throw new Error(err.detail || `Error ${res.status}`)
        }
        setAnalyzeResult(await res.json())
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'An error occurred')
    } finally {
      setLoading(false)
    }
  }, [file, mode])

  const download = useCallback(() => {
    if (!fixedBlob) return
    const url = URL.createObjectURL(fixedBlob)
    const a = document.createElement('a')
    a.href = url
    a.download = fixedName
    a.click()
    URL.revokeObjectURL(url)
  }, [fixedBlob, fixedName])

  const hasResults = fixedBlob || analyzeResult

  return (
    <div className="app">
      <header>
        <h1>CiteFix</h1>
        <p>AGLC4 citation auto-formatter</p>
      </header>

      <div className="mode-toggle">
        <button className={mode === 'fix' ? 'active' : ''} onClick={() => { setMode('fix'); reset() }}>
          Fix &amp; Download
        </button>
        <button className={mode === 'analyze' ? 'active' : ''} onClick={() => { setMode('analyze'); reset() }}>
          Analyze Only
        </button>
      </div>

      {!hasResults && !loading && (
        <div
          className={`dropzone ${dragging ? 'dragging' : ''}`}
          onDragOver={e => { e.preventDefault(); setDragging(true) }}
          onDragLeave={() => setDragging(false)}
          onDrop={handleDrop}
          onClick={() => inputRef.current?.click()}
        >
          <span className="icon">&#128196;</span>
          <p>Drop your .docx file here, or click to browse</p>
          {file && <p className="file-name">{file.name}</p>}
          <input
            ref={inputRef}
            type="file"
            accept=".docx"
            onChange={e => { const f = e.target.files?.[0]; if (f) handleFile(f) }}
          />
        </div>
      )}

      {file && !hasResults && !loading && (
        <button className="download-btn" onClick={submit} style={{ marginTop: '1rem' }}>
          {mode === 'fix' ? 'Fix Citations' : 'Analyze Citations'}
        </button>
      )}

      {loading && (
        <div className="spinner">
          <div className="loader" />
          <p>Processing footnotes...</p>
        </div>
      )}

      {error && <div className="error">{error}</div>}

      {hasResults && (
        <div className="results">
          {analyzeResult && (
            <>
              <div className="stats">
                <div className="stat">
                  <div className="value">{analyzeResult.footnote_count}</div>
                  <div className="label">Footnotes</div>
                </div>
                <div className="stat">
                  <div className="value">{analyzeResult.total_issues}</div>
                  <div className="label">Issues Found</div>
                </div>
                <div className="stat">
                  <div className="value">{analyzeResult.auto_fixable}</div>
                  <div className="label">Auto-Fixed</div>
                </div>
                <div className="stat">
                  <div className="value">{analyzeResult.needs_review}</div>
                  <div className="label">Needs Review</div>
                </div>
              </div>

              {fixedBlob && (
                <button className="download-btn" onClick={download}>
                  Download Fixed Document
                </button>
              )}

              {analyzeResult.issues.length > 0 && (
                <table className="issues-table" style={{ marginTop: '1.5rem' }}>
                  <thead>
                    <tr>
                      <th>FN</th>
                      <th>Rule</th>
                      <th>Issue</th>
                      <th>Current</th>
                      <th>Suggested</th>
                      <th>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {analyzeResult.issues.map((issue, i) => (
                      <tr key={i}>
                        <td>{issue.footnote}</td>
                        <td>{issue.rule}</td>
                        <td>
                          <span className={`badge ${issue.severity}`}>{issue.severity}</span>
                          {' '}{issue.description}
                        </td>
                        <td><code>{issue.current}</code></td>
                        <td><code>{issue.suggested}</code></td>
                        <td>
                          <span className={`badge ${issue.auto_fixable ? 'fixable' : 'manual'}`}>
                            {issue.auto_fixable ? 'Auto-fixed' : 'Manual'}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}

              {analyzeResult.issues.length === 0 && (
                <p style={{ textAlign: 'center', color: '#166534', fontWeight: 600, marginTop: '1rem' }}>
                  No issues found — your citations look correct.
                </p>
              )}
            </>
          )}

          <button className="reset-btn" onClick={reset}>Upload another file</button>
        </div>
      )}
    </div>
  )
}

export default App
