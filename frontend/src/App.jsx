import { useState, useCallback } from 'react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'

const API_BASE = import.meta.env.VITE_API_URL ?? (import.meta.env.DEV ? '' : '')

export default function App() {
  const [file, setFile] = useState(null)
  const [drag, setDrag] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [result, setResult] = useState(null)
  const [activeTab, setActiveTab] = useState('video')

  const onDrop = useCallback((e) => {
    e.preventDefault()
    setDrag(false)
    const f = e.dataTransfer?.files?.[0]
    if (f && f.type.startsWith('video/')) {
      setFile(f)
      setError(null)
      setResult(null)
    } else if (f) {
      setError('Please drop a video file (e.g. MP4).')
    }
  }, [])

  const onDragOver = useCallback((e) => {
    e.preventDefault()
    setDrag(true)
  }, [])

  const onDragLeave = useCallback(() => setDrag(false), [])

  const onFileSelect = useCallback((e) => {
    const f = e.target?.files?.[0]
    if (f) {
      setFile(f)
      setError(null)
      setResult(null)
    }
  }, [])

  const runVideoAnalysis = async () => {
    if (!file) return
    setLoading(true)
    setError(null)
    setResult(null)
    const form = new FormData()
    form.append('video', file)
    try {
      const r = await fetch(`${API_BASE}/api/analyze-video`, {
        method: 'POST',
        body: form,
      })
      const data = await r.json().catch(() => ({}))
      if (!r.ok) throw new Error(data.detail || data.message || r.statusText)
      setResult({ type: 'video', ...data })
    } catch (e) {
      setError(e.message || 'Analysis failed.')
    } finally {
      setLoading(false)
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
          Upload a video to analyze elbow angles per frame, or use IMU quaternion CSVs.
        </p>
      </header>

      <nav style={{ display: 'flex', gap: '0.5rem', marginBottom: '1.5rem' }}>
        <button
          type="button"
          onClick={() => setActiveTab('video')}
          style={{
            padding: '0.5rem 1rem',
            background: activeTab === 'video' ? 'var(--accent)' : 'var(--surface)',
            color: activeTab === 'video' ? 'var(--bg)' : 'var(--text)',
            border: '1px solid var(--border)',
            borderRadius: 'var(--radius)',
          }}
        >
          Video analysis
        </button>
        <button
          type="button"
          onClick={() => setActiveTab('imu')}
          style={{
            padding: '0.5rem 1rem',
            background: activeTab === 'imu' ? 'var(--accent)' : 'var(--surface)',
            color: activeTab === 'imu' ? 'var(--bg)' : 'var(--text)',
            border: '1px solid var(--border)',
            borderRadius: 'var(--radius)',
          }}
        >
          IMU (quaternion)
        </button>
      </nav>

      {activeTab === 'video' && (
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
              accept="video/*"
              onChange={onFileSelect}
              style={{ display: 'none' }}
              id="video-input"
            />
            <label htmlFor="video-input" style={{ cursor: 'pointer' }}>
              {file ? (
                <span style={{ color: 'var(--success)' }}>{file.name}</span>
              ) : (
                <span style={{ color: 'var(--muted)' }}>
                  Drop a video here or click to choose
                </span>
              )}
            </label>
          </div>

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
      )}

      {activeTab === 'imu' && (
        <IMUTab />
      )}

      {error && (
        <p style={{ color: 'var(--error)', marginTop: '1rem' }}>{error}</p>
      )}

      {result?.type === 'video' && result?.frames?.length > 0 && (
        <section style={{ marginTop: '2rem' }}>
          <h2 style={{ fontSize: '1.25rem', marginBottom: '0.5rem' }}>Elbow angle over time</h2>
          <p style={{ color: 'var(--muted)', fontSize: '0.9rem', marginBottom: '1rem' }}>
            {result.total_frames} frames
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

function IMUTab() {
  const [sensor1, setSensor1] = useState(null)
  const [sensor2, setSensor2] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [result, setResult] = useState(null)

  const runImuAnalysis = async () => {
    if (!sensor1 || !sensor2) return
    setLoading(true)
    setError(null)
    setResult(null)
    const form = new FormData()
    form.append('sensor1', sensor1)
    form.append('sensor2', sensor2)
    try {
      const r = await fetch(`${API_BASE}/api/analyze-imu`, { method: 'POST', body: form })
      const data = await r.json().catch(() => ({}))
      if (!r.ok) throw new Error(data.detail || data.message || r.statusText)
      setResult(data)
    } catch (e) {
      setError(e.message || 'IMU analysis failed.')
    } finally {
      setLoading(false)
    }
  }

  const chartData = result?.angles?.map((a) => ({ timestamp: a.timestamp, 'Angle (°)': a.angle_deg })) ?? []

  return (
    <>
      <p style={{ color: 'var(--muted)', marginBottom: '1rem' }}>
        Upload two tab-delimited quaternion CSVs (timestamp, w, x, y, z). First 3 rows are skipped as header.
      </p>
      <div style={{ display: 'grid', gap: '1rem', marginBottom: '1rem' }}>
        <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <span style={{ minWidth: 120 }}>Sensor 1 (reference):</span>
          <input
            type="file"
            accept=".csv,.txt"
            onChange={(e) => { setSensor1(e.target.files?.[0] ?? null); setError(null) }}
          />
          {sensor1 && <span style={{ color: 'var(--success)' }}>{sensor1.name}</span>}
        </label>
        <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <span style={{ minWidth: 120 }}>Sensor 2 (segment):</span>
          <input
            type="file"
            accept=".csv,.txt"
            onChange={(e) => { setSensor2(e.target.files?.[0] ?? null); setError(null) }}
          />
          {sensor2 && <span style={{ color: 'var(--success)' }}>{sensor2.name}</span>}
        </label>
      </div>
      <button
        type="button"
        onClick={runImuAnalysis}
        disabled={!sensor1 || !sensor2 || loading}
        style={{
          padding: '0.6rem 1.2rem',
          background: sensor1 && sensor2 && !loading ? 'var(--accent)' : 'var(--border)',
          color: sensor1 && sensor2 && !loading ? 'var(--bg)' : 'var(--muted)',
          border: 'none',
          borderRadius: 'var(--radius)',
          fontWeight: 600,
        }}
      >
        {loading ? 'Analyzing…' : 'Analyze IMU'}
      </button>
      {error && <p style={{ color: 'var(--error)', marginTop: '1rem' }}>{error}</p>}
      {result?.angles?.length > 0 && (
        <section style={{ marginTop: '2rem' }}>
          <h2 style={{ fontSize: '1.25rem', marginBottom: '0.5rem' }}>Elbow angle from IMU</h2>
          <div style={{ height: 320 }}>
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                <XAxis dataKey="timestamp" stroke="var(--muted)" fontSize={12} tick={{ fontSize: 10 }} />
                <YAxis stroke="var(--muted)" fontSize={12} />
                <Tooltip contentStyle={{ background: 'var(--surface)', border: '1px solid var(--border)' }} />
                <Line type="monotone" dataKey="Angle (°)" stroke="var(--accent)" dot={false} strokeWidth={2} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </section>
      )}
    </>
  )
}
