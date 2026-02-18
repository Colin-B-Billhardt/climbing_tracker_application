import { useState, useCallback, useRef, useEffect } from 'react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'

const API_BASE = import.meta.env.VITE_API_URL ?? (import.meta.env.DEV ? '' : '')

// MediaPipe pose skeleton connections (pairs of landmark indices)
const POSE_CONNECTIONS = [
  [11, 12], [11, 13], [13, 15], [15, 17], [15, 19], [15, 21], [17, 19],
  [12, 14], [14, 16], [16, 18], [16, 20], [16, 22], [18, 20],
  [11, 23], [12, 24], [23, 24], [23, 25], [25, 27], [27, 29], [27, 31], [29, 31],
  [24, 26], [26, 28], [28, 30], [28, 32], [30, 32],
  [0, 1], [1, 2], [2, 3], [3, 7], [0, 4], [4, 5], [5, 6], [6, 8], [9, 10],
]

export default function App() {
  const [file, setFile] = useState(null)
  const [drag, setDrag] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [result, setResult] = useState(null)
  const [frameSkip, setFrameSkip] = useState(2)
  const [progressTotal, setProgressTotal] = useState(0)
  const [progressCurrent, setProgressCurrent] = useState(0)

  const isVideoFile = useCallback((file) => {
    if (!file) return false
    const t = (file.type || '').toLowerCase()
    const name = (file.name || '').toLowerCase()
    const videoTypes = ['.mov', '.mp4', '.webm', '.m4v', '.avi']
    return t.startsWith('video/') || videoTypes.some((ext) => name.endsWith(ext))
  }, [])

  const onDrop = useCallback((e) => {
    e.preventDefault()
    setDrag(false)
    const f = e.dataTransfer?.files?.[0]
    if (f && isVideoFile(f)) {
      setFile(f)
      setError(null)
      setResult(null)
    } else if (f) {
      setError('Please drop a video file (e.g. .mov, .mp4).')
    }
  }, [isVideoFile])

  const onDragOver = useCallback((e) => {
    e.preventDefault()
    setDrag(true)
  }, [])

  const onDragLeave = useCallback(() => setDrag(false), [])

  const onFileSelect = useCallback((e) => {
    const f = e.target?.files?.[0]
    if (f) {
      if (!isVideoFile(f)) {
        setError('Please choose a video file (.mov, .mp4, .webm, etc.).')
        return
      }
      setFile(f)
      setError(null)
      setResult(null)
    }
  }, [isVideoFile])

  const runVideoAnalysis = async () => {
    if (!file) return
    setLoading(true)
    setError(null)
    setResult(null)
    setProgressTotal(0)
    setProgressCurrent(0)
    const form = new FormData()
    form.append('video', file)
    form.append('frame_skip', String(frameSkip))
    try {
      const r = await fetch(`${API_BASE}/api/analyze-video?stream=1`, {
        method: 'POST',
        body: form,
      })
      if (!r.ok) {
        const data = await r.json().catch(() => ({}))
        const msg = Array.isArray(data.detail) ? data.detail.map((d) => d.msg).join(' ') : (data.detail || data.message || r.statusText)
        throw new Error(msg || 'Analysis failed.')
      }
      const contentType = r.headers.get('content-type') || ''
      if (contentType.includes('ndjson') || contentType.includes('x-ndjson')) {
        const reader = r.body.getReader()
        const decoder = new TextDecoder()
        let buffer = ''
        while (true) {
          const { value, done } = await reader.read()
          if (done) break
          buffer += decoder.decode(value, { stream: true })
          const lines = buffer.split('\n')
          buffer = lines.pop() || ''
          for (const line of lines) {
            const trimmed = line.trim()
            if (!trimmed) continue
            try {
              const data = JSON.parse(trimmed)
              if (data.event === 'start') setProgressTotal(data.total_frames ?? 0)
              if (data.event === 'progress') setProgressCurrent(data.frame_index ?? 0)
              if (data.event === 'done') setResult({ type: 'video', frames: data.frames, total_frames: data.total_frames, truncated: data.truncated })
              if (data.event === 'error') throw new Error(data.message || 'Analysis failed.')
            } catch (parseErr) {
              if (parseErr instanceof SyntaxError) continue
              throw parseErr
            }
          }
        }
        if (buffer.trim()) {
          try {
            const data = JSON.parse(buffer.trim())
            if (data.event === 'done') setResult({ type: 'video', frames: data.frames, total_frames: data.total_frames, truncated: data.truncated })
            if (data.event === 'error') throw new Error(data.message || 'Analysis failed.')
          } catch (parseErr) {
            if (!(parseErr instanceof SyntaxError)) throw parseErr
          }
        }
      } else {
        const data = await r.json().catch(() => ({}))
        setResult({ type: 'video', ...data })
      }
    } catch (e) {
      const msg = e.message || 'Analysis failed.'
      if (msg === 'Failed to fetch' || msg.includes('fetch')) {
        setError(
          'Request failed. Try: (1) Wait 30s and retry (server may be waking up). ' +
          '(2) In Render, set the backend env var CORS_ORIGINS to your frontend URL (e.g. https://climbing-tracker-frontend.onrender.com). ' +
          '(3) Use a shorter video or choose "Every 3rd/4th frame" for speed.'
        )
      } else {
        setError(msg)
      }
    } finally {
      setLoading(false)
      setProgressTotal(0)
      setProgressCurrent(0)
    }
  }

  const chartData = result?.frames?.map((f) => ({
    time_s: f.time_s,
    'Left elbow (°)': f.left_elbow_deg,
    'Right elbow (°)': f.right_elbow_deg,
  })) ?? []

  const downloadCsv = () => {
    if (!result?.frames?.length) return
    const headers = ['frame_index', 'time_s', 'left_elbow_deg', 'right_elbow_deg']
    const rows = result.frames.map((f) =>
      [f.frame_index, f.time_s, f.left_elbow_deg ?? '', f.right_elbow_deg ?? ''].join(',')
    )
    const blob = new Blob([headers.join(',') + '\n' + rows.join('\n')], { type: 'text/csv' })
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = `elbow_angles_${file?.name?.replace(/\.[^.]+$/, '') || 'export'}.csv`
    a.click()
    URL.revokeObjectURL(a.href)
  }

  return (
    <div style={{ minHeight: '100vh', padding: '2rem', maxWidth: 960, margin: '0 auto' }}>
      <header style={{ marginBottom: '2rem' }}>
        <h1 style={{ fontSize: '1.75rem', fontWeight: 700, margin: 0, color: 'var(--text)' }}>
          Climbing Technique Tracker
        </h1>
        <p style={{ color: 'var(--muted)', marginTop: '0.5rem' }}>
          Upload a video to analyze elbow angles per frame with pose overlay.
        </p>
      </header>

      <>
          <div
            onDrop={onDrop}
            onDragOver={onDragOver}
            onDragLeave={onDragLeave}
            style={{
              border: `2px dashed ${drag ? 'var(--accent)' : 'var(--border)'}`,
              borderRadius: 'var(--radius)',
              padding: '2rem',
              textAlign: 'center',
              background: drag ? 'rgba(196, 165, 116, 0.08)' : 'var(--surface)',
              marginBottom: '1rem',
            }}
          >
            <input
              type="file"
              onChange={onFileSelect}
              style={{ display: 'none' }}
              id="video-input"
            />
            <label htmlFor="video-input" style={{ cursor: 'pointer' }}>
              {file ? (
                <span style={{ color: 'var(--success)' }}>{file.name}</span>
              ) : (
                <span style={{ color: 'var(--muted)' }}>
                  Drop a video here or click to choose (.mov, .mp4, etc.)
                </span>
              )}
            </label>
            <p style={{ fontSize: '0.8rem', color: 'var(--muted)', marginTop: '0.5rem' }}>
              Pick a video file; if you don’t see .mov, choose “All Files” in the picker or drag the file in.
            </p>
          </div>

          <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.75rem' }}>
            <span style={{ fontSize: '0.9rem' }}>Speed:</span>
            <select
              value={frameSkip}
              onChange={(e) => setFrameSkip(Number(e.target.value))}
              style={{ padding: '0.25rem 0.5rem', background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius)', color: 'var(--text)' }}
            >
              <option value={1}>Every frame (slowest, smoothest)</option>
              <option value={2}>Every 2nd frame — good balance</option>
              <option value={3}>Every 3rd frame — faster</option>
              <option value={4}>Every 4th frame — fastest</option>
            </select>
          </label>
          {loading && (
            <div style={{ marginBottom: '0.75rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem', color: 'var(--muted)', marginBottom: '0.25rem' }}>
                <span>{progressTotal > 0 ? `Processing frame ${progressCurrent} / ${progressTotal}` : 'Analyzing…'}</span>
                {progressTotal > 0 && (
                  <span>{Math.round((progressCurrent / progressTotal) * 100)}%</span>
                )}
              </div>
              {progressTotal > 0 ? (
                <div style={{ height: 6, background: 'var(--border)', borderRadius: 3, overflow: 'hidden' }}>
                  <div
                    style={{
                      height: '100%',
                      width: `${Math.min(100, (progressCurrent / progressTotal) * 100)}%`,
                      background: 'var(--accent)',
                      transition: 'width 0.2s ease',
                    }}
                  />
                </div>
              ) : (
                <div style={{ height: 6, background: 'var(--border)', borderRadius: 3, overflow: 'hidden' }}>
                  <div style={{ height: '100%', width: '100%', background: 'var(--accent)', transformOrigin: 'left', animation: 'progress-indeterminate 1.2s ease-in-out infinite' }} />
                </div>
              )}
            </div>
          )}
          <button
            type="button"
            onClick={runVideoAnalysis}
            disabled={!file || loading}
            style={{
              padding: '0.6rem 1.2rem',
              background: file && !loading ? 'var(--accent)' : 'var(--border)',
              color: file && !loading ? 'var(--bg)' : 'var(--muted)',
              border: 'none',
              borderRadius: 'var(--radius)',
              fontWeight: 600,
            }}
          >
            {loading ? 'Analyzing…' : 'Analyze video'}
          </button>
      </>

      {error && (
        <p style={{ color: 'var(--error)', marginTop: '1rem' }}>{error}</p>
      )}

      {result?.type === 'video' && result?.frames?.length > 0 && file && (
        <VideoOverlayWithMetrics file={file} frames={result.frames} />
      )}

      {result?.type === 'video' && result?.frames?.length > 0 && (
        <section style={{ marginTop: '2rem' }}>
          <h2 style={{ fontSize: '1.25rem', marginBottom: '0.5rem' }}>Elbow angle over time</h2>
          <p style={{ color: 'var(--muted)', fontSize: '0.9rem', marginBottom: '1rem' }}>
            {result.total_frames} frames
            {result.truncated && (
              <span style={{ color: 'var(--accent)', marginLeft: '0.5rem' }}>
                (first ~15–30s only on hosted server)
              </span>
            )}
          </p>
          <div style={{ height: 320, marginBottom: '1rem' }}>
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                <XAxis dataKey="time_s" stroke="var(--muted)" fontSize={12} />
                <YAxis stroke="var(--muted)" fontSize={12} label={{ value: '°', position: 'insideTopRight' }} />
                <Tooltip
                  contentStyle={{ background: 'var(--surface)', border: '1px solid var(--border)' }}
                  labelStyle={{ color: 'var(--text)' }}
                />
                <Legend />
                <Line type="monotone" dataKey="Left elbow (°)" stroke="#7cb083" dot={false} strokeWidth={2} />
                <Line type="monotone" dataKey="Right elbow (°)" stroke="#c4a574" dot={false} strokeWidth={2} />
              </LineChart>
            </ResponsiveContainer>
          </div>
          <button
            type="button"
            onClick={downloadCsv}
            style={{
              padding: '0.5rem 1rem',
              background: 'var(--surface)',
              color: 'var(--accent)',
              border: '1px solid var(--border)',
              borderRadius: 'var(--radius)',
            }}
          >
            Download CSV
          </button>
        </section>
      )}
    </div>
  )
}

function VideoOverlayWithMetrics({ file, frames }) {
  const videoRef = useRef(null)
  const canvasRef = useRef(null)
  const [videoUrl, setVideoUrl] = useState(null)
  const [currentFrame, setCurrentFrame] = useState(null)

  useEffect(() => {
    if (!file) return
    const url = URL.createObjectURL(file)
    setVideoUrl(url)
    return () => URL.revokeObjectURL(url)
  }, [file])

  useEffect(() => {
    if (!videoRef.current || !canvasRef.current || !frames?.length || !videoUrl) return
    const video = videoRef.current
    const canvas = canvasRef.current
    const ctx = canvas.getContext('2d')

    const drawFrame = () => {
      if (video.readyState < 2) return
      const t = video.currentTime
      const idx = Math.min(
        Math.round((t / (video.duration || 1)) * (frames.length - 1)),
        frames.length - 1
      )
      const frame = frames[Math.max(0, idx)]
      setCurrentFrame(frame)
      if (!frame?.landmarks?.length) {
        ctx.clearRect(0, 0, canvas.width, canvas.height)
        return
      }
      const w = video.videoWidth
      const h = video.videoHeight
      if (canvas.width !== w || canvas.height !== h) {
        canvas.width = w
        canvas.height = h
      }
      ctx.clearRect(0, 0, w, h)
      const scaleX = w
      const scaleY = h
      const toX = (lm) => lm.x * scaleX
      const toY = (lm) => lm.y * scaleY
      ctx.strokeStyle = 'rgba(124, 176, 131, 0.9)'
      ctx.lineWidth = Math.max(2, w / 300)
      ctx.beginPath()
      for (const [i, j] of POSE_CONNECTIONS) {
        if (frame.landmarks[i] && frame.landmarks[j]) {
          ctx.moveTo(toX(frame.landmarks[i]), toY(frame.landmarks[i]))
          ctx.lineTo(toX(frame.landmarks[j]), toY(frame.landmarks[j]))
        }
      }
      ctx.stroke()
      ctx.fillStyle = 'rgba(196, 165, 116, 0.95)'
      for (const lm of frame.landmarks) {
        ctx.beginPath()
        ctx.arc(toX(lm), toY(lm), Math.max(3, w / 150), 0, Math.PI * 2)
        ctx.fill()
      }
    }

    const onTimeUpdate = () => drawFrame()
    const onLoadedData = () => {
      canvas.width = video.videoWidth
      canvas.height = video.videoHeight
      drawFrame()
    }
    video.addEventListener('timeupdate', onTimeUpdate)
    video.addEventListener('loadeddata', onLoadedData)
    if (video.readyState >= 2) drawFrame()
    return () => {
      video.removeEventListener('timeupdate', onTimeUpdate)
      video.removeEventListener('loadeddata', onLoadedData)
    }
  }, [frames, videoUrl])

  if (!videoUrl) return null

  return (
    <section style={{ marginTop: '2rem' }}>
      <h2 style={{ fontSize: '1.25rem', marginBottom: '0.5rem' }}>Video with pose overlay</h2>
      <div style={{ display: 'flex', gap: '1.5rem', flexWrap: 'wrap', alignItems: 'flex-start' }}>
        <div style={{ position: 'relative', lineHeight: 0, maxWidth: '100%' }}>
          <video
            ref={videoRef}
            src={videoUrl}
            controls
            playsInline
            style={{ display: 'block', maxWidth: '100%', maxHeight: 400 }}
          />
          <canvas
            ref={canvasRef}
            style={{
              position: 'absolute',
              left: 0,
              top: 0,
              width: '100%',
              height: '100%',
              pointerEvents: 'none',
            }}
          />
        </div>
        <div
          style={{
            minWidth: 200,
            padding: '1rem',
            background: 'var(--surface)',
            border: '1px solid var(--border)',
            borderRadius: 'var(--radius)',
          }}
        >
          <div style={{ fontSize: '0.85rem', color: 'var(--muted)', marginBottom: '0.5rem' }}>
            Current frame
          </div>
          <div style={{ fontSize: '1.5rem', fontWeight: 600, color: 'var(--success)' }}>
            Left elbow: {currentFrame?.left_elbow_deg != null ? `${currentFrame.left_elbow_deg}°` : '—'}
          </div>
          <div style={{ fontSize: '1.5rem', fontWeight: 600, color: 'var(--accent)', marginTop: '0.25rem' }}>
            Right elbow: {currentFrame?.right_elbow_deg != null ? `${currentFrame.right_elbow_deg}°` : '—'}
          </div>
        </div>
      </div>
    </section>
  )
}
