/**
 * PI Decision Visualizer — Shared Types
 *
 * These types match the JSON format produced by PI hooks in ~/.pi/decisions/.
 * The server reads these files and serves them to the frontend via API/WebSocket.
 *
 * Licensed under the Apache License, Version 2.0
 */

// ─── Model & Metrics ────────────────────────────────────────────

export interface ModelInfo {
  name: string
  provider: string
  input_tokens: number
  output_tokens: number
}

export interface SessionMetrics {
  total_tokens: number
  complexity_score: number
  deep_exploration_count: number
  loop_count: number
  quality_score: number
  max_battle_level: number
  beast_activations: number
}

// ─── Agents ─────────────────────────────────────────────────────

export interface AgentProfile {
  agent_id: string
  name: string
  role: string
  model?: string
}

// ─── Decision Nodes ─────────────────────────────────────────────

export interface DecisionNode {
  node_id: string
  session_id: string
  timestamp: string
  label?: string
  category: string           // 'exec' | 'battle' | 'external'
  decision_point: string     // 'tool.execution' | 'session.stop' | 'event.capture' ...
  scene: string              // 'execution' | 'debug' | 'external' ...
  difficulty: string         // '⚡' | '🧠' | '🔥' ...
  battle_level: number       // 0-5 escalation level
  failure_count: number
  payload: Record<string, unknown>
  outcome: string            // 'success' | 'failure' | 'pending' | 'captured'
  children_node_ids: string[]
  agent_id?: string
  privacy_level?: string
  // Index signature required by React Flow's Node<Record<string, unknown>> constraint
  [key: string]: unknown
}

// ─── Sessions ───────────────────────────────────────────────────

export interface DecisionSession {
  session_id: string
  date: string               // YYYY-MM-DD
  created_at: string         // ISO 8601
  updated_at?: string        // ISO 8601
  summary: string
  scene: string
  difficulty: string
  model_info: ModelInfo
  agents: AgentProfile[]
  nodes: DecisionNode[]
  metrics: SessionMetrics
  // Computed fields (added by server/frontend)
  isActive?: boolean
  lastEventAt?: string
  sourceFile?: string        // stripped for privacy in exports
}

// ─── Archive ────────────────────────────────────────────────────

export interface DecisionArchive {
  sessions: DecisionSession[]
  generatedAt: string
  sourceDir?: string
}

// ─── WebSocket Messages ─────────────────────────────────────────

export type WSMessage =
  | { type: 'archive'; data: DecisionArchive }
  | { type: 'session_update'; data: DecisionSession }
  | { type: 'new_event'; data: DecisionNode }
  | { type: 'connected'; data: { sourceDir: string; sessionCount: number } }
  | { type: 'ping' }
  | { type: 'pong' }

// ─── UI State Types ─────────────────────────────────────────────

export interface DateGroup {
  date: string
  sessions: DecisionSession[]
}

/**
 * Category colors and icons for decision nodes.
 * Maps category string → visual properties for the graph canvas.
 */
export const CATEGORY_STYLES: Record<string, { color: string; icon: string; label: string }> = {
  exec:     { color: '#22c55e', icon: '⚡', label: 'Execution' },
  battle:   { color: '#f59e0b', icon: '⚔️', label: 'Battle' },
  external: { color: '#6366f1', icon: '🔮', label: 'External' },
  decision: { color: '#06b6d4', icon: '🧠', label: 'Decision' },
  retry:    { color: '#ef4444', icon: '🔄', label: 'Retry' },
  default:  { color: '#64748b', icon: '●',  label: 'Unknown' },
}

/**
 * Outcome badge colors for decision nodes.
 */
export const OUTCOME_STYLES: Record<string, { color: string; bg: string }> = {
  success:  { color: '#22c55e', bg: 'rgba(34, 197, 94, 0.15)' },
  failure:  { color: '#ef4444', bg: 'rgba(239, 68, 68, 0.15)' },
  pending:  { color: '#f59e0b', bg: 'rgba(245, 158, 11, 0.15)' },
  captured: { color: '#6366f1', bg: 'rgba(99, 102, 241, 0.15)' },
  skipped:  { color: '#64748b', bg: 'rgba(100, 116, 139, 0.10)' },
}
