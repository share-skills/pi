import { useRef, useMemo, useState, useEffect } from 'react'
import { useStore } from '../store'
import { exportSession, exportArchive, importFromJson, downloadAsFile } from '../lib/export'
import { getTranslation, type TranslationKey } from '../i18n'

// ─── i18n hook ───────────────────────────────────────────────────

function useT() {
  const lang = useStore(s => s.lang)
  return useMemo(() => getTranslation(lang), [lang])
}

// ─── Scene & difficulty options for advanced simulation ─────────
const SCENE_OPTIONS = [
  { id: 'coding', labelKey: 'scene.coding' as TranslationKey },
  { id: 'debug', labelKey: 'scene.debug' as TranslationKey },
  { id: 'creative', labelKey: 'scene.creative' as TranslationKey },
  { id: 'product', labelKey: 'scene.product' as TranslationKey },
  { id: 'testing', labelKey: 'scene.testing' as TranslationKey },
  { id: 'deployment', labelKey: 'scene.deployment' as TranslationKey },
  { id: 'collaboration', labelKey: 'scene.collaboration' as TranslationKey },
  { id: 'research', labelKey: 'scene.research' as TranslationKey },
  { id: 'review', labelKey: 'scene.review' as TranslationKey },
]

const DIFFICULTY_OPTIONS = [
  { id: 'easy', label: '⚡', descKey: 'diff.easy' as TranslationKey },
  { id: 'medium', label: '🧠', descKey: 'diff.medium' as TranslationKey },
  { id: 'hard', label: '🐲', descKey: 'diff.hard' as TranslationKey },
]

// ─── Simulation Scenarios ────────────────────────────────────────
const SIMULATION_SCENARIOS = [
  { id: 'coding', labelKey: 'scene.coding' as TranslationKey, descKey: 'simScenario.coding' as TranslationKey },
  { id: 'debug-battle', label: '🔧 调试+战势升级', descKey: 'simScenario.debug-battle' as TranslationKey },
  { id: 'multi-agent', label: '🤝 多Agent协作', descKey: 'simScenario.multi-agent' as TranslationKey },
  { id: 'extreme', label: '🐲 极限战势', descKey: 'simScenario.extreme' as TranslationKey },
  { id: 'creative', labelKey: 'scene.creative' as TranslationKey, descKey: 'simScenario.creative' as TranslationKey },
  { id: 'product', labelKey: 'scene.product' as TranslationKey, descKey: 'simScenario.product' as TranslationKey },
  { id: 'testing-jiejiao', label: '🧪 测试+截教', descKey: 'simScenario.testing-jiejiao' as TranslationKey },
  { id: 'all', label: '⚡ 全部场景', descKey: 'simScenario.all' as TranslationKey },
]

function SimulationMenu({ onClose }: { onClose: () => void }) {
  const t = useT()
  const setArchive = useStore(s => s.setArchive)
  const [loading, setLoading] = useState(false)
  const [tab, setTab] = useState<'quick' | 'advanced'>('quick')

  const [advScene, setAdvScene] = useState('coding')
  const [advDifficulty, setAdvDifficulty] = useState('medium')
  const [advBattleLevel, setAdvBattleLevel] = useState(0)
  const [advAgentCount, setAdvAgentCount] = useState(1)
  const [advNodeCount, setAdvNodeCount] = useState(8)

  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [onClose])

  const handleGenerate = async (scenarioId: string) => {
    setLoading(true)
    try {
      const res = await fetch(`/api/mock?scenario=${scenarioId}`)
      if (res.ok) {
        const data = await res.json()
        setArchive(data)
        onClose()
      } else {
        alert(t('sim.failMsg' as TranslationKey))
      }
    } catch {
      alert(t('sim.noServer' as TranslationKey))
    } finally {
      setLoading(false)
    }
  }

  const handleAdvancedGenerate = async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams({
        scenario: 'advanced',
        scene: advScene,
        difficulty: advDifficulty,
        battleLevel: String(advBattleLevel),
        agentCount: String(advAgentCount),
        nodeCount: String(advNodeCount),
      })
      const res = await fetch(`/api/mock?${params}`)
      if (res.ok) {
        const data = await res.json()
        setArchive(data)
        onClose()
      } else {
        alert(t('sim.failMsg' as TranslationKey))
      }
    } catch {
      alert(t('sim.noServer' as TranslationKey))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-end pt-14 pr-4" onClick={onClose}>
      <div className="glass rounded-xl p-3 w-80 animate-slide-in-right glow-indigo shadow-2xl" onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-3 px-1">
          <span className="text-xs font-semibold text-slate-200 uppercase tracking-wider">{t('sim.title' as TranslationKey)}</span>
          <button onClick={onClose} className="text-slate-500 hover:text-white text-sm">✕</button>
        </div>

        <div className="flex gap-1 mb-3 px-1">
          <button
            onClick={() => setTab('quick')}
            className={`text-[10px] px-2.5 py-1 rounded-md transition-colors ${tab === 'quick' ? 'bg-pi-accent text-white' : 'text-slate-400 hover:text-slate-200 hover:bg-pi-surface-light'}`}
          >
            {t('sim.quick' as TranslationKey)}
          </button>
          <button
            onClick={() => setTab('advanced')}
            className={`text-[10px] px-2.5 py-1 rounded-md transition-colors ${tab === 'advanced' ? 'bg-pi-accent text-white' : 'text-slate-400 hover:text-slate-200 hover:bg-pi-surface-light'}`}
          >
            {t('sim.advanced' as TranslationKey)}
          </button>
        </div>

        {tab === 'quick' ? (
          <>
            <div className="space-y-1">
              {SIMULATION_SCENARIOS.map(s => (
                <button
                  key={s.id}
                  onClick={() => handleGenerate(s.id)}
                  disabled={loading}
                  className="w-full text-left px-3 py-2 rounded-lg hover:bg-pi-surface-light transition-colors group disabled:opacity-50"
                >
                  <div className="text-xs text-slate-200 group-hover:text-white">{s.label ?? t(s.labelKey!)}</div>
                  <div className="text-[10px] text-slate-500">{t(s.descKey)}</div>
                </button>
              ))}
            </div>
            <div className="mt-2 pt-2 border-t border-pi-border px-1">
              <p className="text-[9px] text-slate-600">{t('sim.footer' as TranslationKey)}</p>
            </div>
          </>
        ) : (
          <div className="space-y-3 px-1">
            <div>
              <label className="text-[10px] text-slate-400 uppercase tracking-wider block mb-1">{t('sim.scene' as TranslationKey)}</label>
              <select
                value={advScene}
                onChange={e => setAdvScene(e.target.value)}
                className="w-full text-xs bg-pi-surface-light text-slate-200 border border-pi-border rounded-lg px-2 py-1.5 focus:outline-none focus:border-pi-accent"
              >
                {SCENE_OPTIONS.map(s => (
                  <option key={s.id} value={s.id}>{t(s.labelKey)}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="text-[10px] text-slate-400 uppercase tracking-wider block mb-1">{t('sim.difficulty' as TranslationKey)}</label>
              <div className="flex gap-1">
                {DIFFICULTY_OPTIONS.map(d => (
                  <button
                    key={d.id}
                    onClick={() => setAdvDifficulty(d.id)}
                    className={`flex-1 text-center py-1 rounded-lg text-xs transition-colors ${advDifficulty === d.id ? 'bg-pi-accent text-white' : 'bg-pi-surface-light text-slate-400 hover:text-slate-200'}`}
                    title={t(d.descKey)}
                  >
                    {d.label} {t(d.descKey)}
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label className="text-[10px] text-slate-400 uppercase tracking-wider block mb-1">{t('sim.battleLevel' as TranslationKey)}: <span className="text-slate-200">{advBattleLevel}</span></label>
              <input
                type="range" min={0} max={6} step={1}
                value={advBattleLevel}
                onChange={e => setAdvBattleLevel(parseInt(e.target.value))}
                className="w-full h-1 accent-pi-accent bg-pi-surface-light rounded-full cursor-pointer"
              />
              <div className="flex justify-between text-[9px] text-slate-600 mt-0.5">
                <span>0</span><span>3</span><span>6</span>
              </div>
            </div>

            <div>
              <label className="text-[10px] text-slate-400 uppercase tracking-wider block mb-1">{t('sim.agentCount' as TranslationKey)}</label>
              <div className="flex gap-1">
                {[1, 2, 4].map(n => (
                  <button
                    key={n}
                    onClick={() => setAdvAgentCount(n)}
                    className={`flex-1 text-center py-1 rounded-lg text-xs transition-colors ${advAgentCount === n ? 'bg-pi-accent text-white' : 'bg-pi-surface-light text-slate-400 hover:text-slate-200'}`}
                  >
                    {n}
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label className="text-[10px] text-slate-400 uppercase tracking-wider block mb-1">{t('sim.nodeCount' as TranslationKey)}: <span className="text-slate-200">{advNodeCount}</span></label>
              <input
                type="range" min={3} max={20} step={1}
                value={advNodeCount}
                onChange={e => setAdvNodeCount(parseInt(e.target.value))}
                className="w-full h-1 accent-pi-accent bg-pi-surface-light rounded-full cursor-pointer"
              />
              <div className="flex justify-between text-[9px] text-slate-600 mt-0.5">
                <span>3</span><span>10</span><span>20</span>
              </div>
            </div>

            <button
              onClick={handleAdvancedGenerate}
              disabled={loading}
              className="w-full py-2 rounded-lg bg-pi-accent hover:bg-indigo-500 text-white text-xs font-medium transition-colors disabled:opacity-50"
            >
              {loading ? t('sim.generating' as TranslationKey) : t('sim.generate' as TranslationKey)}
            </button>
          </div>
        )}
      </div>
    </div>
  )
}

export default function TopBar() {
  const t = useT()
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [simMenuOpen, setSimMenuOpen] = useState(false)

  const toggleSidebar = useStore(s => s.toggleSidebar)
  const sidebarOpen = useStore(s => s.sidebarOpen)
  const timelinePosition = useStore(s => s.timelinePosition)
  const setTimelinePosition = useStore(s => s.setTimelinePosition)
  const isLive = useStore(s => s.isLive)
  const wsConnected = useStore(s => s.wsConnected)
  const archive = useStore(s => s.archive)
  const selectedSessionId = useStore(s => s.selectedSessionId)
  const setArchive = useStore(s => s.setArchive)
  const isPlaying = useStore(s => s.isPlaying)
  const togglePlay = useStore(s => s.togglePlay)
  const playSpeed = useStore(s => s.playSpeed)
  const setPlaySpeed = useStore(s => s.setPlaySpeed)
  const theme = useStore(s => s.theme)
  const toggleTheme = useStore(s => s.toggleTheme)
  const lang = useStore(s => s.lang)
  const toggleLang = useStore(s => s.toggleLang)
  const toggleSkillPanel = useStore(s => s.toggleSkillPanel)
  const toggleHelp = useStore(s => s.toggleHelp)

  const session = useMemo(() => {
    if (!archive || !selectedSessionId) return undefined
    return archive.sessions.find(s => s.session_id === selectedSessionId)
  }, [archive, selectedSessionId])
  const sessionCount = archive?.sessions.length ?? 0

  const stepBack = () => setTimelinePosition(Math.max(0, timelinePosition - 0.05))
  const stepForward = () => setTimelinePosition(Math.min(1, timelinePosition + 0.05))

  const timeLabel = timelinePosition >= 0.999 ? 'Now' : `${Math.round(timelinePosition * 100)}%`

  const handleExport = () => {
    if (session) {
      const json = exportSession(session)
      downloadAsFile(json, `pi-session-${session.session_id.slice(-8)}.json`)
    } else if (archive) {
      const json = exportArchive(archive)
      downloadAsFile(json, `pi-archive-${new Date().toISOString().slice(0, 10)}.json`)
    }
  }

  const handleImport = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    const reader = new FileReader()
    reader.onload = () => {
      const imported = importFromJson(reader.result as string)
      if (imported) {
        setArchive(imported)
      } else {
        alert('Invalid PI decision archive file.')
      }
    }
    reader.readAsText(file)
    e.target.value = ''
  }

  return (
    <div className="h-12 flex items-center px-4 gap-4 glass border-b border-pi-border shrink-0 z-30">
      {/* Left */}
      <div className="flex items-center gap-3 min-w-0">
        <button
          onClick={toggleSidebar}
          className="text-slate-400 hover:text-slate-200 transition-colors text-sm"
          title={sidebarOpen ? t('topbar.hideSidebar' as TranslationKey) : t('topbar.showSidebar' as TranslationKey)}
        >
          {sidebarOpen ? '◀' : '▶'}
        </button>
        <div className="flex items-center gap-1.5">
          <span className="text-base">⚡</span>
          <span className="text-sm font-semibold text-slate-200 tracking-tight hidden sm:inline">
            {t('topbar.title' as TranslationKey)}
          </span>
        </div>
      </div>

      {/* Center — Timeline */}
      <div className="flex-1 flex items-center justify-center gap-2 max-w-md mx-auto">
        <button onClick={stepBack} className="text-slate-400 hover:text-slate-200 text-xs p-1 transition-colors" title={t('topbar.stepBack' as TranslationKey)}>
          ⏮
        </button>
        <button
          onClick={togglePlay}
          className="text-slate-400 hover:text-slate-200 text-xs p-1 transition-colors"
          title={isPlaying ? t('topbar.pause' as TranslationKey) : t('topbar.play' as TranslationKey)}
        >
          {isPlaying ? '⏸' : '▶'}
        </button>
        <button onClick={stepForward} className="text-slate-400 hover:text-slate-200 text-xs p-1 transition-colors" title={t('topbar.stepForward' as TranslationKey)}>
          ⏭
        </button>
        <input
          type="range"
          min={0}
          max={1}
          step={0.001}
          value={timelinePosition}
          onChange={e => setTimelinePosition(parseFloat(e.target.value))}
          className="flex-1 h-1 accent-pi-accent bg-pi-surface-light rounded-full cursor-pointer"
          aria-label="Session timeline"
        />
        <span className="text-[10px] text-slate-500 font-mono w-8 text-right">{timeLabel}</span>
        <select
          value={playSpeed}
          onChange={e => setPlaySpeed(parseFloat(e.target.value))}
          className="text-[10px] bg-pi-surface-light text-slate-400 border border-pi-border rounded px-1 py-0.5 focus:outline-none focus:border-pi-accent cursor-pointer"
          title={t('topbar.speed' as TranslationKey)}
        >
          <option value={0.5}>0.5x</option>
          <option value={1}>1x</option>
          <option value={2}>2x</option>
          <option value={4}>4x</option>
        </select>
      </div>

      {/* Right — Tools + Live status */}
      <div className="flex items-center gap-2 min-w-0">
        {session && (
          <span className="text-[10px] text-slate-500 font-mono hidden lg:inline truncate max-w-[120px]">
            {session.model_info.name}
          </span>
        )}

        {/* Theme toggle */}
        <button
          onClick={toggleTheme}
          className="text-[10px] text-slate-400 hover:text-slate-200 transition-colors px-1 py-0.5 rounded hover:bg-pi-surface-light"
          title={theme === 'dark' ? 'Light mode' : 'Dark mode'}
        >
          {theme === 'dark' ? '☀️' : '🌙'}
        </button>

        {/* Language toggle */}
        <button
          onClick={toggleLang}
          className="text-[10px] text-slate-400 hover:text-slate-200 transition-colors px-1 py-0.5 rounded hover:bg-pi-surface-light font-mono"
          title={lang === 'zh' ? 'Switch to English' : '切换中文'}
        >
          {lang === 'zh' ? 'EN' : '中'}
        </button>

        {/* SKILL panel */}
        <button
          onClick={toggleSkillPanel}
          className="text-[10px] text-slate-400 hover:text-slate-200 transition-colors px-1.5 py-0.5 rounded hover:bg-pi-surface-light"
          title="SKILL Knowledge"
        >
          {t('topbar.skillPanel' as TranslationKey)}
        </button>

        {/* Help */}
        <button
          onClick={toggleHelp}
          className="text-[10px] text-slate-400 hover:text-slate-200 transition-colors px-1.5 py-0.5 rounded hover:bg-pi-surface-light"
          title="Help"
        >
          {t('topbar.helpGuide' as TranslationKey)}
        </button>

        <button
          onClick={() => setSimMenuOpen(!simMenuOpen)}
          className="text-[10px] text-slate-400 hover:text-slate-200 transition-colors px-1.5 py-0.5 rounded hover:bg-pi-surface-light"
          title={t('topbar.genSimData' as TranslationKey)}
        >
          {t('topbar.simulate' as TranslationKey)}
        </button>
        <button
          onClick={handleExport}
          className="text-[10px] text-slate-400 hover:text-slate-200 transition-colors px-1.5 py-0.5 rounded hover:bg-pi-surface-light"
          title={session ? t('topbar.exportSession' as TranslationKey) : t('topbar.exportAll' as TranslationKey)}
        >
          {t('topbar.export' as TranslationKey)}
        </button>
        <button
          onClick={() => fileInputRef.current?.click()}
          className="text-[10px] text-slate-400 hover:text-slate-200 transition-colors px-1.5 py-0.5 rounded hover:bg-pi-surface-light"
          title={t('topbar.importArchive' as TranslationKey)}
        >
          {t('topbar.import' as TranslationKey)}
        </button>
        <input
          ref={fileInputRef}
          type="file"
          accept=".json"
          onChange={handleImport}
          className="hidden"
          aria-label="Import archive file"
        />
        <div className="flex items-center gap-1.5">
          <span className={`inline-block w-2 h-2 rounded-full ${wsConnected ? 'bg-green-500 animate-pulse-dot' : 'bg-slate-600'}`} />
          <span className={`text-xs ${wsConnected ? 'text-green-400' : 'text-slate-500'}`}>
            {wsConnected ? t('topbar.live' as TranslationKey) : isLive ? t('topbar.reconnecting' as TranslationKey) : t('topbar.offline' as TranslationKey)}
          </span>
        </div>
        {sessionCount > 0 && (
          <span className="text-[10px] bg-pi-accent-dim text-pi-accent-bright px-1.5 py-0.5 rounded-full font-medium">
            {sessionCount}
          </span>
        )}
      </div>
      {simMenuOpen && <SimulationMenu onClose={() => setSimMenuOpen(false)} />}
    </div>
  )
}
