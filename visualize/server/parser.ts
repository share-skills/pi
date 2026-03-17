/**
 * PI Decision Visualizer — Decision Archive Parser
 *
 * Reads ~/.pi/decisions/ directory structure and produces a DecisionArchive.
 * Handles .json (session), .events.jsonl, and .nodes.jsonl files.
 *
 * Licensed under the Apache License, Version 2.0
 */

import fs from 'fs/promises'
import path from 'path'
import type { DecisionArchive, DecisionNode, DecisionSession } from '../src/types'

// ─── Helpers ────────────────────────────────────────────────────

function extractSessionId(filename: string): string | null {
  // session-ABC123.events.jsonl → ABC123
  // session-ABC123.nodes.jsonl  → ABC123
  // session-ABC123.json         → ABC123
  const m = filename.match(/^session-(.+?)(?:\.events\.jsonl|\.nodes\.jsonl|\.json)$/)
  return m ? m[1] : null
}

function createMinimalSession(sessionId: string, date: string): DecisionSession {
  return {
    session_id: sessionId,
    date,
    created_at: new Date().toISOString(),
    summary: 'Session (auto-created from events)',
    scene: 'unknown',
    difficulty: '⚡',
    model_info: { name: 'unknown', provider: 'unknown', input_tokens: 0, output_tokens: 0 },
    agents: [],
    nodes: [],
    metrics: {
      total_tokens: 0,
      complexity_score: 0,
      deep_exploration_count: 0,
      loop_count: 0,
      quality_score: 0,
      max_battle_level: 1,
      beast_activations: 0,
    },
  }
}

async function parseJsonlFile(filePath: string): Promise<DecisionNode[]> {
  const nodes: DecisionNode[] = []
  try {
    const content = await fs.readFile(filePath, 'utf-8')
    const lines = content.split('\n')
    for (let i = 0; i < lines.length; i++) {
      const line = lines[i].trim()
      if (!line) continue
      try {
        const parsed = JSON.parse(line)
        // Normalize payload: if it's a string, try to parse it
        if (typeof parsed.payload === 'string') {
          try {
            parsed.payload = JSON.parse(parsed.payload)
          } catch {
            parsed.payload = { raw: parsed.payload }
          }
        }
        // FIX: Validate required node fields before accepting.
        // Missing children_node_ids causes "not iterable" crash in DecisionCanvas BFS layout.
        if (!parsed.node_id || typeof parsed.node_id !== 'string') {
          console.warn(`[parser] Node missing node_id at line ${i + 1} in ${path.basename(filePath)}, skipping`)
          continue
        }
        if (!Array.isArray(parsed.children_node_ids)) {
          parsed.children_node_ids = []
        }
        if (!parsed.timestamp) {
          parsed.timestamp = new Date().toISOString()
        }
        if (typeof parsed.payload !== 'object' || parsed.payload === null) {
          parsed.payload = {}
        }
        nodes.push(parsed as DecisionNode)
      } catch {
        console.warn(`[parser] Skipping malformed line ${i + 1} in ${path.basename(filePath)}`)
      }
    }
  } catch (err) {
    console.warn(`[parser] Failed to read ${filePath}:`, (err as Error).message)
  }
  return nodes
}

async function parseSessionFile(filePath: string): Promise<DecisionSession | null> {
  try {
    const content = await fs.readFile(filePath, 'utf-8')
    const parsed = JSON.parse(content)
    // FIX: Validate required fields to prevent crashes in sorting/grouping.
    // A session missing 'date' or 'created_at' would crash on b.date.localeCompare(a.date).
    if (!parsed.session_id || typeof parsed.session_id !== 'string') {
      console.warn(`[parser] Session missing session_id in ${path.basename(filePath)}, skipping`)
      return null
    }
    if (!parsed.date || typeof parsed.date !== 'string') {
      // Try to infer date from created_at or filename
      parsed.date = parsed.created_at?.slice(0, 10) ?? new Date().toISOString().slice(0, 10)
      console.warn(`[parser] Session ${parsed.session_id} missing date, inferred: ${parsed.date}`)
    }
    if (!parsed.created_at || typeof parsed.created_at !== 'string') {
      parsed.created_at = new Date().toISOString()
    }
    // FIX: Enforce runtime type checks, not just missing-field defaults.
    // Wrong-typed fields (e.g. "nodes": {}) survive and crash spread/iteration.
    parsed.model_info = (parsed.model_info && typeof parsed.model_info === 'object' && !Array.isArray(parsed.model_info))
      ? parsed.model_info
      : { name: 'unknown', provider: 'unknown', input_tokens: 0, output_tokens: 0 }
    parsed.metrics = (parsed.metrics && typeof parsed.metrics === 'object' && !Array.isArray(parsed.metrics))
      ? parsed.metrics
      : { total_tokens: 0, complexity_score: 0, deep_exploration_count: 0, loop_count: 0, quality_score: 0, max_battle_level: 0, beast_activations: 0 }
    parsed.agents = Array.isArray(parsed.agents) ? parsed.agents : []
    parsed.nodes = Array.isArray(parsed.nodes) ? parsed.nodes : []
    parsed.summary = typeof parsed.summary === 'string' ? parsed.summary : ''
    return parsed as DecisionSession
  } catch (err) {
    console.warn(`[parser] Failed to parse session ${filePath}:`, (err as Error).message)
    return null
  }
}

// ─── Public API ─────────────────────────────────────────────────

/**
 * Parse the entire decisions directory and return a DecisionArchive.
 * Walks date-based subdirectories, merges events/nodes into sessions.
 */
export async function parseDecisionsDir(dir: string): Promise<DecisionArchive> {
  const sessionMap = new Map<string, DecisionSession>()
  const nodeMap = new Map<string, DecisionNode[]>()

  let entries: string[]
  try {
    entries = await fs.readdir(dir)
  } catch {
    // Directory doesn't exist yet — return empty archive
    return { sessions: [], generatedAt: new Date().toISOString(), sourceDir: dir }
  }

  // Sort date directories to process in order
  const dateDirs = entries.filter(e => /^\d{4}-\d{2}-\d{2}$/.test(e)).sort()

  for (const dateDir of dateDirs) {
    const datePath = path.join(dir, dateDir)
    let stat
    try {
      stat = await fs.stat(datePath)
    } catch { continue }
    if (!stat.isDirectory()) continue

    let files: string[]
    try {
      files = await fs.readdir(datePath)
    } catch { continue }

    for (const file of files) {
      const sessionId = extractSessionId(file)
      if (!sessionId) continue

      const filePath = path.join(datePath, file)

      if (file.endsWith('.json') && !file.endsWith('.jsonl')) {
        // Session metadata file
        const session = await parseSessionFile(filePath)
        if (session) {
          session.sourceFile = filePath
          if (!session.nodes) session.nodes = []
          sessionMap.set(sessionId, session)
        }
      } else if (file.endsWith('.events.jsonl') || file.endsWith('.nodes.jsonl')) {
        // Event or node data file
        const nodes = await parseJsonlFile(filePath)
        const existing = nodeMap.get(sessionId) ?? []
        nodeMap.set(sessionId, [...existing, ...nodes])
      }
    }
  }

  // Merge nodes into sessions; create minimal sessions for orphan events
  for (const [sessionId, nodes] of nodeMap) {
    if (!sessionMap.has(sessionId)) {
      // Infer date from first node or from directory structure
      const date = nodes[0]?.timestamp?.slice(0, 10) ?? new Date().toISOString().slice(0, 10)
      sessionMap.set(sessionId, createMinimalSession(sessionId, date))
    }
    const session = sessionMap.get(sessionId)!
    session.nodes = [...(session.nodes ?? []), ...nodes]
  }

  // Compute isActive and lastEventAt for each session
  const now = Date.now()
  const ACTIVE_THRESHOLD_MS = 30 * 60 * 1000 // 30 minutes

  for (const session of sessionMap.values()) {
    if (session.nodes.length > 0) {
      // Sort nodes by timestamp
      session.nodes.sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime())
      const lastNode = session.nodes[session.nodes.length - 1]
      session.lastEventAt = lastNode.timestamp
      session.isActive = (now - new Date(lastNode.timestamp).getTime()) < ACTIVE_THRESHOLD_MS
    } else {
      session.lastEventAt = session.created_at
      session.isActive = (now - new Date(session.created_at).getTime()) < ACTIVE_THRESHOLD_MS
    }
  }

  // Sort sessions by date (newest first), then by created_at
  const sessions = Array.from(sessionMap.values()).sort((a, b) => {
    const dateCompare = b.date.localeCompare(a.date)
    if (dateCompare !== 0) return dateCompare
    return new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
  })

  return {
    sessions,
    generatedAt: new Date().toISOString(),
    sourceDir: dir,
  }
}

/**
 * Delete all files associated with a given session ID from the decisions directory.
 */
export async function deleteSession(dir: string, sessionId: string): Promise<void> {
  const entries = await fs.readdir(dir)
  const dateDirs = entries.filter(e => /^\d{4}-\d{2}-\d{2}$/.test(e))

  for (const dateDir of dateDirs) {
    const datePath = path.join(dir, dateDir)
    let files: string[]
    try {
      files = await fs.readdir(datePath)
    } catch { continue }

    for (const file of files) {
      if (extractSessionId(file) === sessionId) {
        const filePath = path.join(datePath, file)
        try {
          await fs.unlink(filePath)
          console.log(`[parser] Deleted: ${filePath}`)
        } catch (err) {
          console.warn(`[parser] Failed to delete ${filePath}:`, (err as Error).message)
        }
      }
    }

    // Remove date directory if it's now empty
    try {
      const remaining = await fs.readdir(datePath)
      if (remaining.length === 0) {
        await fs.rmdir(datePath)
        console.log(`[parser] Removed empty directory: ${datePath}`)
      }
    } catch { /* ignore */ }
  }
}
