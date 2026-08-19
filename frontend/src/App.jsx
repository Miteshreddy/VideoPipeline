import { useEffect, useMemo, useState } from 'react'
import {
  ArrowRight, Check, ChevronDown, Clock3, Download, Film, Globe2, Headphones,
  Languages, Loader2, Play, Radio, RotateCcw, Sparkles, Timer, UploadCloud, WandSparkles, X, AlertCircle, HelpCircle
} from 'lucide-react'

const voices = [
  { id: 'en-US-AriaNeural', name: 'Aria', meta: 'Warm · Female' },
  { id: 'en-US-GuyNeural', name: 'Guy', meta: 'Confident · Male' },
  { id: 'en-US-JennyNeural', name: 'Jenny', meta: 'Conversational · Female' },
  { id: 'en-US-ChristopherNeural', name: 'Christopher', meta: 'Documentary · Male' },
]

const steps = [
  { id: 'fetch', statuses: ['downloading', 'extracting'], label: 'Fetch', icon: Download, desc: 'Download source video' },
  { id: 'transcribe', statuses: ['transcribing'], label: 'Transcribe', icon: Radio, desc: 'Convert speech to text' },
  { id: 'translate', statuses: ['translating'], label: 'Translate', icon: Languages, desc: 'Translate meaning naturally' },
  { id: 'synthesize', statuses: ['synthesizing'], label: 'Synthesize', icon: Headphones, desc: 'Generate English speech' },
  { id: 'remix', statuses: ['remixing'], label: 'Remix', icon: WandSparkles, desc: 'Replace original audio' },
]

function formatDuration(seconds) {
  if (!seconds) return '—'
  const m = Math.floor(seconds / 60)
  const s = Math.floor(seconds % 60)
  return `${m}:${String(s).padStart(2, '0')}`
}

function formatBytes(bytes) {
  if (!bytes) return ''
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function isValidYoutubeUrl(string) {
  if (!string) return false
  const regex = /^(https?:\/\/)?(www\.|m\.)?(youtube\.com\/(watch\?v=|embed\/|v\/|shorts\/)|youtu\.be\/)([\w-]{11})/i
  return regex.test(string.trim())
}

function App() {
  const [url, setUrl] = useState('')
  const [voice, setVoice] = useState(voices[0].id)
  const [model, setModel] = useState('small')
  const [job, setJob] = useState(null)
  const [error, setError] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [dragActive, setDragActive] = useState(false)

  // Poll active jobs
  useEffect(() => {
    if (!job || ['completed', 'failed'].includes(job.status)) return
    const timer = setInterval(async () => {
      try {
        const res = await fetch(`/api/jobs/${job.id}`)
        if (res.ok) {
          const updated = await res.json()
          setJob(updated)
        }
      } catch (err) {
        console.error('Polling error:', err)
      }
    }, 1000)
    return () => clearInterval(timer)
  }, [job?.id, job?.status])

  const activeStepIndex = useMemo(() => {
    if (!job) return -1
    if (job.status === 'completed') return steps.length
    return steps.findIndex((s) => s.statuses.includes(job.status))
  }, [job])

  const startJob = async () => {
    setError('')
    const trimmed = url.trim()
    if (!trimmed) {
      setError('Please enter a YouTube video URL.')
      return
    }
    if (!isValidYoutubeUrl(trimmed)) {
      setError('Invalid YouTube link format. Example: https://www.youtube.com/watch?v=...')
      return
    }

    setIsSubmitting(true)
    try {
      const res = await fetch('/api/jobs', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: trimmed, voice, whisper_model: model }),
      })
      if (!res.ok) {
        const body = await res.json().catch(() => ({}))
        setError(body.detail || 'Could not initiate the dubbing job. Please try again.')
        setIsSubmitting(false)
        return
      }
      const data = await res.json()
      setJob(data)
    } catch (err) {
      setError('Network connection error: Unable to reach backend server.')
    } finally {
      setIsSubmitting(false)
    }
  }

  const reset = () => {
    setJob(null)
    setError('')
    setUrl('')
  }

  const retryCurrentJob = () => {
    if (url) {
      setJob(null)
      setError('')
      startJob()
    } else {
      reset()
    }
  }

  const isFormDisabled = isSubmitting || !url.trim() || !isValidYoutubeUrl(url)

  return (
    <div className="app-shell">
      <div className="ambient ambient-one" />
      <div className="ambient ambient-two" />

      <header className="topbar">
        <div className="brand">
          <div className="brand-mark"><Sparkles size={16} /></div>
          <div>
            <div className="brand-name">DUBFLOW</div>
            <div className="brand-sub">AI VIDEO DUBBING</div>
          </div>
        </div>
        <div className="header-status"><span className="pulse-dot" /> SYSTEM ONLINE</div>
      </header>

      <main>
        <section className="hero">
          <div className="eyebrow"><Sparkles size={14} /> From any language to natural English</div>
          <h1>Keep the video.<br /><span>Change the voice.</span></h1>
          <p className="hero-copy">Paste a YouTube link and DubFlow handles the complete pipeline — fetch, transcription, translation, speech synthesis, and final audio remix.</p>
        </section>

        {!job ? (
          <section className="workspace-grid">
            <div className={`panel source-panel ${dragActive ? 'drag-active' : ''}`}
              onDragEnter={(e) => { e.preventDefault(); setDragActive(true) }}
              onDragOver={(e) => e.preventDefault()}
              onDragLeave={() => setDragActive(false)}
              onDrop={(e) => {
                e.preventDefault(); setDragActive(false)
                const text = e.dataTransfer.getData('text')
                if (text) {
                  setUrl(text)
                  setError('')
                }
              }}
            >
              <div className="panel-kicker"><Film size={15} /> SOURCE VIDEO</div>
              <div className="input-wrap">
                <div className="input-icon"><Play size={17} /></div>
                <input
                  id="youtube-url-input"
                  value={url}
                  onChange={(e) => { setUrl(e.target.value); if (error) setError('') }}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      e.preventDefault()
                      if (!isFormDisabled) startJob()
                      else if (!url.trim()) setError('Please enter a YouTube video URL.')
                      else if (!isValidYoutubeUrl(url)) setError('Invalid YouTube link format. Example: https://www.youtube.com/watch?v=...')
                    }
                  }}
                  placeholder="https://www.youtube.com/watch?v=..."
                  autoComplete="off"
                />
                {url && <button className="icon-btn" onClick={() => { setUrl(''); setError('') }}><X size={16} /></button>}
              </div>
              <div className="dropzone">
                <UploadCloud size={20} />
                <span>Paste a YouTube URL above</span>
                <small>Supports any spoken language · Public YouTube videos</small>
              </div>
              {error && (
                <div className="error-line">
                  <AlertCircle size={15} style={{ flexShrink: 0 }} />
                  <span>{error}</span>
                </div>
              )}
            </div>

            <div className="panel settings-panel">
              <div className="panel-kicker"><WandSparkles size={15} /> DUB SETTINGS</div>
              <label htmlFor="voice-select">English voice</label>
              <div className="select-wrap">
                <select id="voice-select" value={voice} onChange={(e) => setVoice(e.target.value)}>
                  {voices.map(v => <option key={v.id} value={v.id}>{v.name} — {v.meta}</option>)}
                </select>
                <ChevronDown size={16} />
              </div>
              <label>Whisper model</label>
              <div className="model-row">
                {['tiny', 'base', 'small', 'medium'].map(m => (
                  <button
                    key={m}
                    type="button"
                    className={model === m ? 'model active' : 'model'}
                    onClick={() => setModel(m)}
                  >
                    {m}
                  </button>
                ))}
              </div>
              <div className="settings-note"><Globe2 size={14} /> Auto-detect source language → English</div>
            </div>

            <div className="panel pipeline-panel">
              <div className="pipeline-heading"><span>PIPELINE</span><span>5 STAGES</span></div>
              <div className="pipeline-list">
                {steps.map((s, i) => {
                  const Icon = s.icon
                  return (
                    <div className="pipeline-item" key={s.id}>
                      <div className="pipeline-num">0{i + 1}</div>
                      <div className="pipeline-icon"><Icon size={17} /></div>
                      <div className="pipeline-copy">
                        <strong>{s.label}</strong>
                        <span>{s.desc}</span>
                      </div>
                      <Check size={15} className="check-muted" />
                    </div>
                  )
                })}
              </div>
              <button
                id="start-dubbing-btn"
                className="primary-btn"
                onClick={startJob}
                disabled={isFormDisabled}
              >
                {isSubmitting ? (
                  <>
                    <Loader2 size={17} className="spin-icon" />
                    <span>Initiating job…</span>
                  </>
                ) : (
                  <>
                    <span>Start dubbing</span>
                    <ArrowRight size={17} />
                  </>
                )}
              </button>
            </div>
          </section>
        ) : (
          <section className="job-card">
            <div className="job-head">
              <div>
                <div className="panel-kicker">
                  {job.status === 'completed' ? 'OUTPUT READY' : job.status === 'failed' ? 'JOB FAILED' : 'PROCESSING VIDEO'}
                </div>
                <h2>{job.source_title || 'Preparing your video…'}</h2>
                <p>{job.message}</p>
              </div>
              <div className="job-percent">{job.progress}%</div>
            </div>

            <div className="progress-track">
              <div style={{ width: `${job.progress}%` }} />
            </div>

            <div className="progress-steps">
              {steps.map((s, i) => {
                const Icon = s.icon
                const isDone = job.status === 'completed' || i < activeStepIndex
                const isActive = s.statuses.includes(job.status)
                const isFailed = job.status === 'failed' && (job.stage === s.id || (job.stage === 'fetch' && s.id === 'fetch'))

                return (
                  <div
                    key={s.id}
                    className={`progress-step ${isDone ? 'done' : ''} ${isActive ? 'active' : ''} ${isFailed ? 'step-failed' : ''}`}
                  >
                    <div className="progress-icon">
                      {isDone ? <Check size={15} /> : isActive ? <Loader2 size={15} className="spin-icon" /> : isFailed ? <X size={15} /> : <Icon size={15} />}
                    </div>
                    <span>{s.label}</span>
                  </div>
                )
              })}
            </div>

            {job.status === 'completed' && (
              <div className="result-card">
                <div className="result-icon"><Check size={20} /></div>
                <div className="result-info">
                  <strong>{job.source_title}</strong>
                  <span>
                    {job.detected_language ? `Detected: ${job.detected_language.toUpperCase()} → ENGLISH` : 'ENGLISH'} · {formatDuration(job.duration_seconds)} · {job.metrics?.segments || 0} segments
                    {job.metrics?.processing_time_seconds ? ` · ${job.metrics.processing_time_seconds}s total` : ''}
                    {job.metrics?.output_size_bytes ? ` (${formatBytes(job.metrics.output_size_bytes)})` : ''}
                  </span>
                </div>
                <a
                  id="download-dubbed-mp4-btn"
                  className="download-btn"
                  href={`/api/jobs/${job.id}/download`}
                  download
                >
                  <Download size={17} /> Download MP4
                </a>
              </div>
            )}

            {job.status === 'failed' && (
              <div className="failure-container">
                <div className="failure">
                  <div className="failure-header">
                    <AlertCircle size={18} />
                    <strong>Dubbing Failed during {job.stage ? job.stage.toUpperCase() : 'PROCESSING'} stage</strong>
                  </div>
                  <p className="failure-error">{job.error || 'An unexpected error occurred during processing.'}</p>
                  {job.suggested_action && (
                    <div className="failure-suggestion">
                      <HelpCircle size={15} />
                      <span><strong>Suggested Action:</strong> {job.suggested_action}</span>
                    </div>
                  )}
                </div>
              </div>
            )}

            <div className="job-actions">
              {job.status === 'failed' && (
                <button className="secondary-btn retry-btn" onClick={retryCurrentJob}>
                  <RotateCcw size={15} /> Retry Dubbing
                </button>
              )}
              <button className="secondary-btn" onClick={reset}>
                {job.status === 'completed' ? 'Dub Another Video' : 'Try Another Video'}
              </button>
            </div>
          </section>
        )}

        <section className="feature-strip">
          <div><Timer size={17} /><span><strong>Timed to the original</strong> Segment placement preserves the source pacing.</span></div>
          <div><Languages size={17} /><span><strong>Meaning-first translation</strong> English phrasing is translated for natural delivery.</span></div>
          <div><Headphones size={17} /><span><strong>Natural TTS</strong> Multiple English voices are ready for the final mix.</span></div>
          <div><Clock3 size={17} /><span><strong>Terminal + web progress</strong> Every stage reports its current status.</span></div>
        </section>
      </main>

      <footer>
        <span>DubFlow · Idealabs Digital assignment build</span>
        <span>Built with React · FastAPI · Whisper · FFmpeg</span>
      </footer>
    </div>
  )
}

export default App
