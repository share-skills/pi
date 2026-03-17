import type { DecisionArchive, DecisionSession } from '../types'

const SENSITIVE_KEYS = /token|secret|key|password|credential|auth/i
// FIX: Broadened to catch ALL absolute paths (Unix and Windows), not just /Users|/home|/root.
// Non-home paths like /tmp/, /var/, /opt/ were previously exported verbatim.
const PATH_PATTERN = /(?:\/(?:[a-zA-Z][a-zA-Z0-9._-]*\/){2,}[^\s"',}]*|[A-Z]:\\[^\s"',}]+)/gi

function redactPaths(value: unknown): unknown {
  if (typeof value === 'string') {
    return value.replace(PATH_PATTERN, '[REDACTED]')
  }
  if (Array.isArray(value)) {
    return value.map(redactPaths)
  }
  if (value && typeof value === 'object') {
    const result: Record<string, unknown> = {}
    for (const [k, v] of Object.entries(value)) {
      if (SENSITIVE_KEYS.test(k)) {
        result[k] = '[REDACTED]'
      } else {
        result[k] = redactPaths(v)
      }
    }
    return result
  }
  return value
}

export function sanitizeForExport(session: DecisionSession): DecisionSession {
  const sanitized = { ...session }
  delete sanitized.sourceFile

  // FIX: Apply path redaction to ALL string fields on nodes, not just payload.
  // decision_point and label can contain file paths (e.g., "tool.execution: /Users/.../main.ts")
  sanitized.nodes = sanitized.nodes.map(node => {
    const payload = redactPaths(node.payload) as Record<string, unknown>
    return {
      ...node,
      payload,
      decision_point: redactPaths(node.decision_point) as string,
      label: node.label ? redactPaths(node.label) as string : node.label,
    }
  })

  sanitized.summary = (redactPaths(sanitized.summary) as string)

  return sanitized
}

export function exportSession(session: DecisionSession): string {
  return JSON.stringify(sanitizeForExport(session), null, 2)
}

export function exportArchive(archive: DecisionArchive): string {
  const sanitized: DecisionArchive = {
    ...archive,
    sessions: archive.sessions.map(sanitizeForExport),
  }
  delete sanitized.sourceDir
  return JSON.stringify(sanitized, null, 2)
}

/**
 * Import supports both single-session and full-archive JSON formats.
 * FIX: Previously only accepted archive format, so files exported via
 * exportSession() were rejected by the import button — broken round-trip.
 * Also normalizes imported sessions through defaulting logic to prevent
 * crashes from missing fields (date, model_info, etc.).
 */
export function importFromJson(json: string): DecisionArchive | null {
  try {
    const data = JSON.parse(json)

    // Case 1: Full archive format { sessions: [...], generatedAt: "..." }
    if (data.sessions && Array.isArray(data.sessions)) {
      if (!data.generatedAt || typeof data.generatedAt !== 'string') return null
      const normalized = data.sessions.map(normalizeImportedSession).filter(Boolean)
      if (normalized.length === 0) return null
      return { sessions: normalized, generatedAt: data.generatedAt } as DecisionArchive
    }

    // Case 2: Single session format { session_id: "...", nodes: [...] }
    if (data.session_id && typeof data.session_id === 'string') {
      const session = normalizeImportedSession(data)
      if (!session) return null
      return {
        sessions: [session],
        generatedAt: new Date().toISOString(),
      } as DecisionArchive
    }

    return null
  } catch {
    return null
  }
}

/** Normalize an imported session with safe defaults for all required fields.
 *  Mirrors the validation logic in server/parser.ts:parseSessionFile. */
function normalizeImportedSession(s: Record<string, unknown>): DecisionSession | null {
  if (!s || typeof s !== 'object') return null
  if (!s.session_id || typeof s.session_id !== 'string') return null
  if (!Array.isArray(s.nodes)) s.nodes = []

  // Default required fields that the UI assumes exist
  if (!s.date || typeof s.date !== 'string') {
    s.date = (typeof s.created_at === 'string') ? (s.created_at as string).slice(0, 10) : new Date().toISOString().slice(0, 10)
  }
  if (!s.created_at || typeof s.created_at !== 'string') {
    s.created_at = new Date().toISOString()
  }
  if (!s.model_info || typeof s.model_info !== 'object' || Array.isArray(s.model_info)) {
    s.model_info = { name: 'unknown', provider: 'unknown', input_tokens: 0, output_tokens: 0 }
  }
  if (!s.metrics || typeof s.metrics !== 'object' || Array.isArray(s.metrics)) {
    s.metrics = { total_tokens: 0, complexity_score: 0, deep_exploration_count: 0, loop_count: 0, quality_score: 0, max_battle_level: 0, beast_activations: 0 }
  }
  if (!Array.isArray(s.agents)) s.agents = []
  if (typeof s.summary !== 'string') s.summary = ''

  return s as unknown as DecisionSession
}

export function downloadAsFile(content: string, filename: string) {
  const blob = new Blob([content], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}
