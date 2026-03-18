import { useState, useMemo, useEffect } from 'react'
import { useStore } from '../store'
import { CATEGORY_STYLES, OUTCOME_STYLES } from '../types'
import MetricsPanel from './MetricsPanel'
import { getTranslation, type TranslationKey } from '../i18n'

// ─── i18n hook ───────────────────────────────────────────────────

function useT() {
  const lang = useStore(s => s.lang)
  return useMemo(() => getTranslation(lang), [lang])
}

// ─── Tooltip data (mirrors DecisionCanvas) ────────────────────────

const BEAST_TOOLTIPS: Record<string, string> = {
  '🦅鹰':    '鹰 · 洞察原型 — 高空视角，见微知著',
  '🐺🐯狼虎': '狼虎 · 团队协作 — 群体智慧，协同作战',
  '🦁狮':    '狮 · 决断原型 — 当机立断，勇往直前',
  '🐎马':    '马 · 坚韧原型 — 持续推进，不畏艰险',
  '🐂牛':    '牛 · 踏实原型 — 扎实执行，稳步推进',
  '🦈鲨':    '鲨 · 深潜原型 — 深入探索，锲而不舍',
  '🐝蜂':    '蜂 · 高效原型 — 精准高效，专注目标',
  '🦊狐':    '狐 · 灵巧原型 — 灵活变通，随机应变',
  '🐲龙':    '龙 · 全局原型 — 统揽全局，掌控大势',
  '🦄独角兽': '独角兽 · 创新原型 — 突破惯例，开辟新径',
  '🦉猫头鹰': '猫头鹰 · 观察原型 — 洞察细节，深度分析',
  '🐬海豚':   '海豚 · 沟通原型 — 高效沟通，协调协作',
}

const STRATEGY_TOOLTIPS: Record<string, string> = {
  '以正合':       '以正兵合战，正面对敌，稳扎稳打',
  '以奇胜':       '以奇兵取胜，侧翼突破，出奇制胜',
  '致人不致于人': '掌控主动权，让敌人跟着我走',
  '穷理尽性':     '穷究事物之理，发挥天赋本性',
  '搜读验交付':   '搜索→阅读→验证→交付，四步工作法',
  '截教·最小实证': '截取一线生机，以最小成本验证核心假设',
  '截教·截道三法': '截取路径三法：截工具/截思路/截方案',
  '好钢刀刃':     '将精力集中在最关键的突破点',
  '换道破局':     '遇阻换道，另辟蹊径破解困局',
  '穷搜广读':     '广泛搜索，深度阅读，建立知识地图',
  '庙算全局':     '全局思维，系统规划，知己知彼',
  '全新路线':     '放弃旧路，重新规划，置之死地而后生',
  '截取一线':     '从绝境中截取唯一可行路线',
  '协同出击':     '多路协同，整体联动，天时地利人和',
  '以正合以奇胜': '正奇结合：正面强攻+侧翼奇袭',
}

const ALLUSION_TOOLTIPS: Record<string, string> = {
  '避实击虚':   '孙子兵法·虚实篇 — 避开敌强点，攻击敌弱点',
  '先为不可胜': '孙子兵法·形篇 — 先保证自身不败，再谋求取胜',
  '知彼知己':   '孙子兵法 — 知道自己和对方的实力，百战不殆',
  '投之亡地':   '孙子兵法·九地篇 — 置之死地而后生，绝境激发潜力',
  '置之死地':   '孙子兵法·九地篇 — 陷入绝境方能爆发最大潜能',
  '庙算多胜':   '孙子兵法·计篇 — 开战前充分谋划，胜算在多',
  '天行健':     '易经·乾卦 — 天道刚健，君子自强不息',
  '截取一线生机': '截教策略 — 在最后关头截取那一线生机',
}

// ─── Tooltip Component ───────────────────────────────────────────

function Tooltip({ text, children }: { text: string; children: React.ReactNode }) {
  return (
    <span className="pi-tooltip-wrap">
      {children}
      <span className="pi-tooltip">{text}</span>
    </span>
  )
}

export default function DetailDrawer() {
  const t = useT()
  const detailDrawerOpen = useStore(s => s.detailDrawerOpen)
  const toggleDetailDrawer = useStore(s => s.toggleDetailDrawer)
  const selectedNodeId = useStore(s => s.selectedNodeId)
  const archive = useStore(s => s.archive)
  const selectedSessionId = useStore(s => s.selectedSessionId)

  const session = useMemo(() => {
    if (!archive || !selectedSessionId) return undefined
    return archive.sessions.find(s => s.session_id === selectedSessionId)
  }, [archive, selectedSessionId])

  const [payloadOpen, setPayloadOpen] = useState(false)
  const [chainModalOpen, setChainModalOpen] = useState(false)
  const lang = useStore(s => s.lang)

  // ESC closes chain modal
  useEffect(() => {
    if (!chainModalOpen) return
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') setChainModalOpen(false) }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [chainModalOpen])

  if (!detailDrawerOpen) return null
  if (!session) return null

  const node = selectedNodeId ? session.nodes.find(n => n.node_id === selectedNodeId) : null

  return (
    <div className="absolute right-4 top-4 w-80 max-w-[calc(100vw-2rem)] max-h-[calc(100%-2rem)] glass rounded-xl z-20 flex flex-col animate-slide-in-right glow-indigo overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-pi-border shrink-0">
        <span className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
          {node ? t('detail.decisionDetails' as TranslationKey) : t('detail.sessionOverview' as TranslationKey)}
        </span>
        <button
          onClick={toggleDetailDrawer}
          className="text-slate-500 hover:text-slate-300 transition-colors text-sm"
        >
          ✕
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto min-h-0 p-4 space-y-4">
        {node ? <NodeDetail node={node} payloadOpen={payloadOpen} setPayloadOpen={setPayloadOpen} t={t} chainModalOpen={chainModalOpen} setChainModalOpen={setChainModalOpen} lang={lang} /> : <SessionDetail session={session} t={t} />}
      </div>
    </div>
  )
}

// ─── Section Header ──────────────────────────────────────────────

function SectionHeader({ title }: { title: string }) {
  return (
    <div className="flex items-center gap-2 mt-3 mb-1">
      <span className="text-[10px] font-bold text-indigo-400 uppercase tracking-widest">{title}</span>
      <div className="flex-1 h-px bg-pi-border" />
    </div>
  )
}

// ─── Confidence Bar ──────────────────────────────────────────────

function ConfidenceBar({ level }: { level: string }) {
  const color = level === 'high' ? '#22c55e' : level === 'medium' ? '#f59e0b' : '#ef4444'
  const width = level === 'high' ? '85%' : level === 'medium' ? '55%' : '25%'
  return (
    <div className="flex items-center gap-2 mt-1">
      <div className="flex-1 h-1.5 bg-pi-surface-light rounded-full overflow-hidden">
        <div className="h-full rounded-full transition-all" style={{ width, backgroundColor: color }} />
      </div>
      <span className="text-[10px] font-mono" style={{ color }}>{level}</span>
    </div>
  )
}

// ─── Node Detail ─────────────────────────────────────────────────

type TFn = (key: TranslationKey) => string

function NodeDetail({
  node,
  payloadOpen,
  setPayloadOpen,
  t,
  chainModalOpen,
  setChainModalOpen,
  lang,
}: {
  node: { node_id: string; session_id: string; category: string; decision_point: string; scene: string; difficulty: string; battle_level: number; outcome: string; timestamp: string; failure_count: number; agent_id?: string; payload: Record<string, unknown> }
  payloadOpen: boolean
  setPayloadOpen: (v: boolean) => void
  t: TFn
  chainModalOpen: boolean
  setChainModalOpen: (v: boolean) => void
  lang: string
}) {
  const archive = useStore(s => s.archive)
  const style = CATEGORY_STYLES[node.category] ?? CATEGORY_STYLES.default
  const outcomeStyle = OUTCOME_STYLES[node.outcome] ?? OUTCOME_STYLES.pending

  const p = node.payload
  const beast = p.beast as string | undefined
  const strategy = p.strategy as string | undefined
  const confidence = p.confidence as string | undefined
  const mindset = p.mindset as string | undefined
  const allusion = (p.allusion ?? p.classic) as string | undefined
  const modelOutput = p.model_output as string | undefined
  const userPrompt = p.user_prompt as string | undefined
  const tokens = p.tokens as { input?: number; output?: number } | undefined
  const interactionChain = p.interaction_chain as { role: string; content: string }[] | undefined
  const reasoning = p.reasoning as string | undefined

  const beastTooltip = beast ? BEAST_TOOLTIPS[beast] : undefined
  const strategyTooltip = strategy ? STRATEGY_TOOLTIPS[strategy] : undefined
  const allusionTooltip = allusion ? ALLUSION_TOOLTIPS[allusion] : undefined

  return (
    <>
      {/* Category & Decision Point */}
      <div>
        <div className="flex items-center gap-2 mb-2">
          <span className="text-lg">{style.icon}</span>
          <span className="text-xs font-medium text-slate-200">{style.label}</span>
          <span
            className="text-[10px] font-mono px-1.5 py-0.5 rounded-full ml-auto"
            style={{ color: outcomeStyle.color, backgroundColor: outcomeStyle.bg }}
          >
            {node.outcome}
          </span>
        </div>
        <p className="text-sm text-slate-300 font-mono">{node.decision_point}</p>
      </div>

      {/* Details grid */}
      <div className="grid grid-cols-2 gap-2 text-xs">
        <DetailField label={t('detail.scene' as TranslationKey)} value={node.scene} />
        <DetailField label={t('detail.difficulty' as TranslationKey)} value={node.difficulty} />
        <DetailField label={t('detail.battleLevel' as TranslationKey)} value={`L${node.battle_level}`} />
        <DetailField label={t('detail.failures' as TranslationKey)} value={String(node.failure_count)} />
        <DetailField
          label={t('detail.time' as TranslationKey)}
          value={new Date(node.timestamp).toLocaleTimeString()}
        />
        {node.agent_id && (
          <div className="flex items-start gap-2">
            <span className="text-[10px] text-slate-500 uppercase tracking-wider w-16 shrink-0 pt-0.5">{t('detail.agent' as TranslationKey)}</span>
            <div className="flex-1">
              {(() => {
                const session = archive?.sessions.find(s => s.session_id === node.session_id)
                const agentProfile = session?.agents?.find(a => a.agent_id === node.agent_id)
                if (!agentProfile) return <span className="text-xs text-slate-300">{node.agent_id}</span>
                const roleColors: Record<string, string> = { leader: 'text-amber-400', teammate: 'text-blue-400', coach: 'text-green-400' }
                return (
                  <div>
                    <span className={`text-xs font-medium ${roleColors[agentProfile.role] ?? 'text-slate-300'}`}>
                      {agentProfile.name}
                    </span>
                    <span className="text-[10px] text-slate-500 ml-2">
                      {agentProfile.role === 'leader' ? '👑 Leader' : agentProfile.role === 'coach' ? '🧭 Coach' : '🤝 Teammate'}
                    </span>
                    {agentProfile.model && (
                      <span className="text-[10px] text-slate-600 block">{agentProfile.model}</span>
                    )}
                  </div>
                )
              })()}
            </div>
          </div>
        )}
      </div>

      {/* ── PI认知状态 ─────────────────────────────────────────── */}
      <SectionHeader title={t('detail.cogState' as TranslationKey)} />

      {beast && (
        <div className="flex items-start gap-2">
          <span className="text-[10px] text-slate-500 uppercase tracking-wider w-16 shrink-0 pt-0.5">{t('detail.beast' as TranslationKey)}</span>
          <div className="flex-1">
            <Tooltip text={beastTooltip ?? beast}>
              <span className="text-sm cursor-help">{beast}</span>
            </Tooltip>
            {beastTooltip && (
              <p className="text-[10px] text-slate-500 mt-0.5">{beastTooltip}</p>
            )}
          </div>
        </div>
      )}

      {mindset && (
        <div className="flex items-start gap-2">
          <span className="text-[10px] text-slate-500 uppercase tracking-wider w-16 shrink-0 pt-0.5">{t('detail.mindset' as TranslationKey)}</span>
          <span className="text-xs text-slate-300">{mindset}</span>
        </div>
      )}

      {confidence && (
        <div>
          <span className="text-[10px] text-slate-500 uppercase tracking-wider block">{t('detail.confidence' as TranslationKey)}</span>
          <ConfidenceBar level={confidence} />
        </div>
      )}

      {/* ── 战势信息 ──────────────────────────────────────────── */}
      <SectionHeader title={t('detail.battleInfo' as TranslationKey)} />

      {strategy && (
        <div className="flex items-start gap-2">
          <span className="text-[10px] text-slate-500 uppercase tracking-wider w-16 shrink-0 pt-0.5">{t('detail.strategy' as TranslationKey)}</span>
          <div className="flex-1">
            <Tooltip text={strategyTooltip ?? strategy}>
              <span className="text-xs text-indigo-400 cursor-help">{strategy}</span>
            </Tooltip>
            {strategyTooltip && (
              <p className="text-[10px] text-slate-500 mt-0.5">{strategyTooltip}</p>
            )}
          </div>
        </div>
      )}

      {allusion && (
        <div className="flex items-start gap-2">
          <span className="text-[10px] text-slate-500 uppercase tracking-wider w-16 shrink-0 pt-0.5">{t('detail.allusion' as TranslationKey)}</span>
          <div className="flex-1">
            <Tooltip text={allusionTooltip ?? allusion}>
              <span className="text-xs text-amber-400 italic cursor-help">《{allusion}》</span>
            </Tooltip>
            {allusionTooltip && (
              <p className="text-[10px] text-slate-500 mt-0.5">{allusionTooltip}</p>
            )}
          </div>
        </div>
      )}

      {tokens && (
        <div className="flex items-center gap-3 text-[10px]">
          <span className="text-slate-500 uppercase tracking-wider">{t('detail.tokens' as TranslationKey)}</span>
          <span className="text-green-400 font-mono">↑{tokens.input?.toLocaleString()}</span>
          <span className="text-blue-400 font-mono">↓{tokens.output?.toLocaleString()}</span>
        </div>
      )}

      {/* ── 交互记录 ──────────────────────────────────────────── */}
      {(userPrompt || modelOutput || reasoning || (interactionChain && interactionChain.length > 0)) && (
        <SectionHeader title={t('detail.interaction' as TranslationKey)} />
      )}

      {userPrompt && (
        <div>
          <span className="text-[10px] text-slate-500 uppercase tracking-wider block mb-1">{t('detail.userPrompt' as TranslationKey)}</span>
          <p className="text-xs text-slate-300 bg-pi-bg rounded-lg p-2.5 font-mono leading-relaxed">
            {userPrompt}
          </p>
        </div>
      )}

      {reasoning && (
        <div>
          <span className="text-[10px] text-slate-500 uppercase tracking-wider block mb-1">{t('detail.reasoning' as TranslationKey)}</span>
          <p className="text-xs text-slate-400 bg-pi-bg rounded-lg p-2.5 italic leading-relaxed max-h-24 overflow-y-auto">
            {reasoning}
          </p>
        </div>
      )}

      {modelOutput && (
        <div>
          <span className="text-[10px] text-slate-500 uppercase tracking-wider block mb-1">{t('detail.modelOutput' as TranslationKey)}</span>
          <p className="text-xs text-slate-300 bg-pi-bg rounded-lg p-2.5 font-mono leading-relaxed max-h-32 overflow-y-auto">
            {modelOutput}
          </p>
        </div>
      )}

      {interactionChain && interactionChain.length > 0 && (
        <div>
          <button
            onClick={() => setChainModalOpen(true)}
            className="flex items-center gap-2 text-[11px] text-indigo-400 hover:text-indigo-300 transition-colors cursor-pointer group"
          >
            <span className="text-lg">🔗</span>
            <span className="group-hover:underline font-medium">
              {t('detail.dialogChain' as TranslationKey)} ({interactionChain.length})
            </span>
            <span className="text-[10px] text-slate-500">
              {lang === 'zh' ? '点击放大' : 'Click to expand'}
            </span>
          </button>
        </div>
      )}

      {/* Interaction chain modal — centered popup */}
      {chainModalOpen && interactionChain && (
        <div
          className="fixed inset-0 z-[200] flex items-center justify-center"
          style={{ background: 'rgba(0,0,0,0.6)', backdropFilter: 'blur(4px)' }}
          onClick={() => setChainModalOpen(false)}
        >
          <div
            className="w-[90vw] max-w-2xl max-h-[80vh] rounded-xl shadow-2xl overflow-hidden flex flex-col"
            style={{ background: 'var(--pi-surface)', border: '1px solid var(--pi-border-hover)' }}
            onClick={e => e.stopPropagation()}
          >
            {/* Header */}
            <div className="flex items-center justify-between px-5 py-3" style={{ borderBottom: '1px solid var(--pi-border)' }}>
              <span className="text-sm font-semibold" style={{ color: 'var(--pi-text)' }}>
                🔗 {t('detail.dialogChain' as TranslationKey)} ({interactionChain.length})
              </span>
              <button
                onClick={() => setChainModalOpen(false)}
                className="text-slate-400 hover:text-slate-200 transition-colors text-lg"
              >
                ✕
              </button>
            </div>
            {/* Content */}
            <div className="flex-1 overflow-y-auto p-5 space-y-3">
              {interactionChain.map((step, i) => (
                <div
                  key={i}
                  className="rounded-lg p-4 leading-relaxed text-sm"
                  style={{
                    background: step.role === 'user'
                      ? 'var(--pi-accent-dim)'
                      : 'rgba(34, 197, 94, 0.08)',
                    borderLeft: `3px solid ${step.role === 'user' ? '#6366f1' : '#22c55e'}`,
                  }}
                >
                  <div className="flex items-center gap-2 mb-2">
                    <span
                      className="text-xs font-bold uppercase tracking-wider px-2 py-0.5 rounded"
                      style={{
                        color: step.role === 'user' ? '#818cf8' : '#4ade80',
                        background: step.role === 'user' ? 'rgba(99,102,241,0.15)' : 'rgba(34,197,94,0.12)',
                      }}
                    >
                      {step.role === 'user' ? '👤 USER' : '🤖 AI'}
                    </span>
                    <span className="text-[10px]" style={{ color: 'var(--pi-text-dim)' }}>#{i + 1}</span>
                  </div>
                  <p className="whitespace-pre-wrap" style={{ color: 'var(--pi-text-secondary)' }}>{step.content}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Collapsible raw payload */}
      <div>
        <button
          onClick={() => setPayloadOpen(!payloadOpen)}
          className="flex items-center gap-1.5 text-[10px] text-slate-500 hover:text-slate-300 transition-colors uppercase tracking-wider"
        >
          <span>{payloadOpen ? '▼' : '▶'}</span>
          {t('detail.rawPayload' as TranslationKey)}
        </button>
        {payloadOpen && (
          <pre className="mt-2 text-[10px] text-slate-400 bg-pi-bg rounded-lg p-3 overflow-x-auto max-h-48 overflow-y-auto font-mono">
            {JSON.stringify(node.payload, null, 2)}
          </pre>
        )}
      </div>
    </>
  )
}

function SessionDetail({ session, t }: { session: { session_id: string; summary: string; model_info: { name: string; provider: string; input_tokens: number; output_tokens: number }; agents: { agent_id: string; name: string; role: string }[]; metrics: import('../types').SessionMetrics; created_at: string; scene: string; difficulty: string }; t: TFn }) {
  return (
    <>
      <div>
        <p className="text-sm text-slate-300 mb-1">{session.summary || t('detail.noSummary' as TranslationKey)}</p>
        <p className="text-[10px] text-slate-500 font-mono">{session.session_id}</p>
      </div>

      <div className="grid grid-cols-2 gap-2 text-xs">
        <DetailField label={t('detail.scene' as TranslationKey)} value={session.scene} />
        <DetailField label={t('detail.difficulty' as TranslationKey)} value={session.difficulty} />
        <DetailField label={t('detail.model' as TranslationKey)} value={session.model_info.name} />
        <DetailField label={t('detail.provider' as TranslationKey)} value={session.model_info.provider} />
        <DetailField label={t('detail.created' as TranslationKey)} value={new Date(session.created_at).toLocaleString()} />
      </div>

      {session.agents.length > 0 && (
        <div>
          <span className="text-[10px] text-slate-500 uppercase tracking-wider block mb-1.5">{t('detail.agents' as TranslationKey)}</span>
          <div className="space-y-1">
            {session.agents.map(a => (
              <div key={a.agent_id} className="flex items-center gap-2 text-xs">
                <span className="text-slate-400">🤖</span>
                <span className="text-slate-300">{a.name}</span>
                <span className="text-slate-500">({a.role})</span>
              </div>
            ))}
          </div>
        </div>
      )}

      <div>
        <span className="text-[10px] text-slate-500 uppercase tracking-wider block mb-2">{t('detail.metrics' as TranslationKey)}</span>
        <MetricsPanel metrics={session.metrics} />
      </div>
    </>
  )
}

function DetailField({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <span className="text-[10px] text-slate-500 uppercase tracking-wider block">{label}</span>
      <span className="text-slate-300">{value}</span>
    </div>
  )
}
