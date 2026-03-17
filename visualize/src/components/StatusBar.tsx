import { useMemo } from 'react'
import { useStore } from '../store'

export default function StatusBar() {
  // FIX: Subscribe to raw state, not the selectedSession getter (stable ref → no re-render).
  const archive = useStore(s => s.archive)
  const selectedSessionId = useStore(s => s.selectedSessionId)
  const wsConnected = useStore(s => s.wsConnected)
  const lastUpdate = useStore(s => s.lastUpdate)

  // Derive selected session reactively from raw state
  const session = useMemo(() => {
    if (!archive || !selectedSessionId) return undefined
    return archive.sessions.find(s => s.session_id === selectedSessionId)
  }, [archive, selectedSessionId])

  const totalSessions = archive?.sessions.length ?? 0

  return (
    <div className="h-8 flex items-center px-4 text-[11px] bg-pi-surface border-t border-pi-border shrink-0 z-30 gap-4">
      {/* Left — Session info */}
      <div className="flex items-center gap-2 min-w-0 flex-1">
        {session ? (
          <>
            <span className="text-slate-500">Session:</span>
            <span className="text-slate-400 font-mono truncate">{session.session_id.slice(-8)}</span>
            <span className="text-slate-600">|</span>
            <span className="text-slate-500">{new Date(session.created_at).toLocaleDateString()}</span>
          </>
        ) : (
          <span className="text-slate-500">{totalSessions} session{totalSessions !== 1 ? 's' : ''} loaded</span>
        )}
      </div>

      {/* Center — Metrics badges */}
      {session && (
        <div className="flex items-center gap-3">
          <MetricBadge label="tokens" value={session.metrics.total_tokens > 1000 ? `${(session.metrics.total_tokens / 1000).toFixed(1)}k` : String(session.metrics.total_tokens)} />
          <MetricBadge label="complexity" value={`${session.metrics.complexity_score}/5`} />
          <MetricBadge label="depth" value={String(session.metrics.deep_exploration_count)} />
          <MetricBadge label="score" value={String(session.metrics.quality_score)} />
        </div>
      )}

      {/* Right — Connection */}
      <div className="flex items-center gap-2 min-w-0">
        <span className={`inline-block w-1.5 h-1.5 rounded-full ${wsConnected ? 'bg-green-500' : 'bg-slate-600'}`} />
        <span className="text-slate-500">
          {wsConnected ? 'Connected' : 'Disconnected'}
        </span>
        {lastUpdate && (
          <>
            <span className="text-slate-600">|</span>
            <span className="text-slate-500">
              {new Date(lastUpdate).toLocaleTimeString()}
            </span>
          </>
        )}
      </div>
    </div>
  )
}

function MetricBadge({ label, value }: { label: string; value: string }) {
  return (
    <span className="text-slate-500">
      {label}: <span className="text-slate-300 font-mono">{value}</span>
    </span>
  )
}
