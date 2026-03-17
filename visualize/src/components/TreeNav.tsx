import { useMemo, useState } from 'react'
import { useStore } from '../store'
import { format, parseISO } from 'date-fns'
import type { DecisionSession } from '../types'

export default function TreeNav() {
  // FIX: Subscribe to raw state, not the dateGroups getter function (stable ref → no re-render).
  // Compute groups locally with useMemo so we re-render when archive changes.
  const sidebarOpen = useStore(s => s.sidebarOpen)
  const archive = useStore(s => s.archive)
  const selectedSessionId = useStore(s => s.selectedSessionId)
  const selectSession = useStore(s => s.selectSession)
  const deleteSession = useStore(s => s.deleteSession)

  const [collapsedDates, setCollapsedDates] = useState<Set<string>>(new Set())
  const [confirmDelete, setConfirmDelete] = useState<string | null>(null)

  // Derive date groups from archive (same logic as store.dateGroups but reactive)
  const groups = useMemo(() => {
    if (!archive) return []
    const grouped = new Map<string, DecisionSession[]>()
    for (const session of archive.sessions) {
      const date = session.date
      if (!grouped.has(date)) grouped.set(date, [])
      grouped.get(date)!.push(session)
    }
    return Array.from(grouped.entries())
      .sort(([a], [b]) => b.localeCompare(a))
      .map(([date, sessions]) => ({ date, sessions }))
  }, [archive])

  const toggleDate = (date: string) => {
    setCollapsedDates(prev => {
      const next = new Set(prev)
      if (next.has(date)) next.delete(date)
      else next.add(date)
      return next
    })
  }

  const handleDelete = async (sessionId: string) => {
    if (confirmDelete === sessionId) {
      await deleteSession(sessionId)
      setConfirmDelete(null)
    } else {
      setConfirmDelete(sessionId)
      setTimeout(() => setConfirmDelete(null), 3000)
    }
  }

  if (!sidebarOpen) {
    return (
      <div className="w-10 border-r border-pi-border bg-pi-surface flex flex-col items-center py-3 gap-2 shrink-0">
        <span className="text-xs text-slate-500" title="Sessions">📋</span>
        {groups.slice(0, 5).map(g => (
          <span key={g.date} className="text-[10px] text-slate-500" title={g.date}>📅</span>
        ))}
      </div>
    )
  }

  return (
    <div className="w-64 border-r border-pi-border bg-pi-surface flex flex-col shrink-0 overflow-hidden">
      {/* Header */}
      <div className="h-10 flex items-center justify-between px-3 border-b border-pi-border shrink-0">
        <span className="text-xs font-semibold text-slate-300 uppercase tracking-wider">Sessions</span>
        <span className="text-[10px] text-slate-500 font-mono">
          {groups.reduce((sum, g) => sum + g.sessions.length, 0)}
        </span>
      </div>

      {/* Scrollable list */}
      <div className="flex-1 overflow-y-auto min-h-0 py-1">
        {groups.length === 0 ? (
          <div className="px-3 py-8 text-center">
            <div className="text-2xl mb-2">📭</div>
            <p className="text-xs text-slate-500">No sessions yet</p>
          </div>
        ) : (
          groups.map(group => {
            const isCollapsed = collapsedDates.has(group.date)
            let dateLabel: string
            try {
              dateLabel = format(parseISO(group.date), 'MMM d')
            } catch {
              dateLabel = group.date
            }

            return (
              <div key={group.date}>
                {/* Date header */}
                <button
                  onClick={() => toggleDate(group.date)}
                  className="w-full flex items-center gap-2 px-3 py-1.5 text-xs text-slate-400 hover:text-slate-200 transition-colors"
                  aria-expanded={!isCollapsed}
                >
                  <span className="text-[10px]">{isCollapsed ? '▶' : '▼'}</span>
                  <span>📅 {dateLabel}</span>
                  <span className="text-[10px] text-slate-600 ml-auto">{group.sessions.length}</span>
                </button>

                {/* Sessions */}
                {!isCollapsed && group.sessions.map(session => {
                  const isSelected = session.session_id === selectedSessionId
                  const shortId = session.session_id.slice(-6)
                  const isDeleting = confirmDelete === session.session_id

                  return (
                    <div
                      key={session.session_id}
                      className={`tree-item flex items-start gap-2 px-3 py-1.5 group ${isSelected ? 'active' : ''}`}
                    >
                      <button
                        type="button"
                        className="flex items-start gap-2 flex-1 min-w-0 cursor-pointer text-left bg-transparent border-0 p-0"
                        onClick={() => selectSession(session.session_id)}
                        aria-label={`Session ${shortId}: ${session.summary || 'No summary'}`}
                      >
                        <span className={`mt-1 inline-block w-2 h-2 rounded-full shrink-0 ${session.isActive ? 'bg-green-500 animate-pulse-dot' : 'bg-slate-600'}`} />
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-1.5">
                            <span className="text-[11px] font-mono text-slate-300">{shortId}</span>
                            <span className="text-xs">{session.difficulty}</span>
                          </div>
                          <p className="text-[10px] text-slate-500 truncate">{session.summary || 'No summary'}</p>
                        </div>
                      </button>
                      <button
                        type="button"
                        onClick={() => handleDelete(session.session_id)}
                        className={`text-[10px] opacity-0 group-hover:opacity-100 focus:opacity-100 transition-opacity shrink-0 mt-0.5 ${isDeleting ? 'text-red-400' : 'text-slate-500 hover:text-red-400'}`}
                        title={isDeleting ? 'Click again to confirm' : 'Delete session'}
                        aria-label={isDeleting ? 'Confirm delete' : `Delete session ${shortId}`}
                      >
                        {isDeleting ? '⚠️' : '✕'}
                      </button>
                    </div>
                  )
                })}
              </div>
            )
          })
        )}
      </div>
    </div>
  )
}
