import { create } from 'zustand'
import type { DecisionArchive, DecisionSession, DecisionNode, DateGroup } from './types'
import type { Lang } from './i18n'

export type Theme = 'dark' | 'light'

interface VisualizerState {
  archive: DecisionArchive | null
  selectedSessionId: string | null
  selectedNodeId: string | null
  sidebarOpen: boolean
  detailDrawerOpen: boolean
  timelinePosition: number
  isLive: boolean
  wsConnected: boolean
  lastUpdate: string | null
  isPlaying: boolean
  playSpeed: number
  theme: Theme
  lang: Lang
  skillPanelOpen: boolean
  helpOpen: boolean

  // Computed
  selectedSession: () => DecisionSession | undefined
  dateGroups: () => DateGroup[]
  visibleNodes: () => DecisionNode[]
  filteredNodes: () => DecisionNode[]

  // Actions
  setArchive: (archive: DecisionArchive) => void
  selectSession: (id: string | null) => void
  selectNode: (id: string | null) => void
  setTimelinePosition: (pos: number) => void
  toggleSidebar: () => void
  toggleDetailDrawer: () => void
  setLive: (live: boolean) => void
  setWsConnected: (connected: boolean) => void
  deleteSession: (id: string) => Promise<void>
  togglePlay: () => void
  setPlaySpeed: (speed: number) => void
  toggleTheme: () => void
  setTheme: (theme: Theme) => void
  toggleLang: () => void
  setLang: (lang: Lang) => void
  toggleSkillPanel: () => void
  toggleHelp: () => void
}

export const useStore = create<VisualizerState>((set, get) => ({
  archive: null,
  selectedSessionId: null,
  selectedNodeId: null,
  sidebarOpen: true,
  detailDrawerOpen: false,
  timelinePosition: 1,
  isLive: false,
  wsConnected: false,
  lastUpdate: null,
  isPlaying: false,
  playSpeed: 1,
  theme: (localStorage.getItem('pi-theme') as Theme) || 'dark',
  lang: (localStorage.getItem('pi-lang') as Lang) || 'zh',
  skillPanelOpen: false,
  helpOpen: false,

  // Computed
  selectedSession: () => {
    const { archive, selectedSessionId } = get()
    if (!archive || !selectedSessionId) return undefined
    return archive.sessions.find(s => s.session_id === selectedSessionId)
  },

  dateGroups: () => {
    const { archive } = get()
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
  },

  visibleNodes: () => {
    const { archive, selectedSessionId, timelinePosition } = get()
    if (!archive || !selectedSessionId) return []
    const session = archive.sessions.find(s => s.session_id === selectedSessionId)
    if (!session || session.nodes.length === 0) return []

    if (timelinePosition >= 1) return session.nodes

    const timestamps = session.nodes.map(n => new Date(n.timestamp).getTime()).sort((a, b) => a - b)
    const minT = timestamps[0]
    const maxT = timestamps[timestamps.length - 1]
    if (minT === maxT) return session.nodes

    const cutoff = minT + (maxT - minT) * timelinePosition
    return session.nodes.filter(n => new Date(n.timestamp).getTime() <= cutoff)
  },

  filteredNodes: () => {
    const { archive, selectedSessionId } = get()
    if (!archive || !selectedSessionId) return []
    const session = archive.sessions.find(s => s.session_id === selectedSessionId)
    return session?.nodes ?? []
  },

  // Actions
  setArchive: (archive) => {
    const { selectedSessionId } = get()
    // FIX: Auto-select first session when archive loads and nothing is selected.
    // Without this, the user sees an empty canvas ("No Session Selected") which
    // looks like a black screen on the dark theme.
    const shouldAutoSelect = !selectedSessionId && archive.sessions.length > 0
    const autoSelectedId = shouldAutoSelect ? archive.sessions[0].session_id : selectedSessionId
    set({
      archive,
      lastUpdate: new Date().toISOString(),
      ...(shouldAutoSelect ? { selectedSessionId: autoSelectedId, detailDrawerOpen: false } : {}),
    })
  },

  selectSession: (id) => set({
    selectedSessionId: id,
    selectedNodeId: null,
    detailDrawerOpen: id !== null,
  }),

  selectNode: (id) => set({
    selectedNodeId: id,
    detailDrawerOpen: id !== null,
  }),

  setTimelinePosition: (pos) => set({ timelinePosition: Math.max(0, Math.min(1, pos)) }),

  toggleSidebar: () => set(s => ({ sidebarOpen: !s.sidebarOpen })),

  toggleDetailDrawer: () => set(s => ({ detailDrawerOpen: !s.detailDrawerOpen })),

  setLive: (live) => set({ isLive: live }),

  setWsConnected: (connected) => set({ wsConnected: connected }),

  togglePlay: () => set(s => ({ isPlaying: !s.isPlaying })),

  setPlaySpeed: (speed) => set({ playSpeed: speed }),

  toggleTheme: () => {
    const next = get().theme === 'dark' ? 'light' : 'dark'
    localStorage.setItem('pi-theme', next)
    set({ theme: next })
  },

  setTheme: (theme) => {
    localStorage.setItem('pi-theme', theme)
    set({ theme })
  },

  toggleLang: () => {
    const next = get().lang === 'zh' ? 'en' : 'zh'
    localStorage.setItem('pi-lang', next)
    set({ lang: next })
  },

  setLang: (lang) => {
    localStorage.setItem('pi-lang', lang)
    set({ lang })
  },

  toggleSkillPanel: () => set(s => ({ skillPanelOpen: !s.skillPanelOpen })),

  toggleHelp: () => set(s => ({ helpOpen: !s.helpOpen })),

  deleteSession: async (id) => {
    try {
      await fetch(`/api/sessions/${id}`, { method: 'DELETE' })
    } catch {
      // Server may be unavailable; still remove locally
    }
    const { archive, selectedSessionId } = get()
    if (!archive) return
    set({
      archive: {
        ...archive,
        sessions: archive.sessions.filter(s => s.session_id !== id),
      },
      selectedSessionId: selectedSessionId === id ? null : selectedSessionId,
      selectedNodeId: selectedSessionId === id ? null : get().selectedNodeId,
      detailDrawerOpen: selectedSessionId === id ? false : get().detailDrawerOpen,
    })
  },
}))
