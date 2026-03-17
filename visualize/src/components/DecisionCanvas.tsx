import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  Handle,
  Position,
  MarkerType,
  applyNodeChanges,
  type Node,
  type Edge,
  type NodeTypes,
  type NodeProps,
  type NodeChange,
  useReactFlow,
  ReactFlowProvider,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import { useStore } from '../store'
import { CATEGORY_STYLES, OUTCOME_STYLES, type DecisionNode } from '../types'
import { getTranslation, type TranslationKey } from '../i18n'

// ─── i18n hook ───────────────────────────────────────────────────

function useT() {
  const lang = useStore(s => s.lang)
  return useMemo(() => getTranslation(lang), [lang])
}

// ─── Layout ──────────────────────────────────────────────────────

const NODE_WIDTH = 300
const NODE_HEIGHT = 120
const H_GAP = 40
const V_GAP = 120

interface LayoutResult {
  flowNodes: Node[]
  flowEdges: Edge[]
}

function layoutDecisionTree(nodes: DecisionNode[]): LayoutResult {
  if (nodes.length === 0) return { flowNodes: [], flowEdges: [] }

  const nodeMap = new Map(nodes.map(n => [n.node_id, n]))
  const childSet = new Set<string>()
  for (const n of nodes) {
    for (const cid of n.children_node_ids) childSet.add(cid)
  }

  const roots = nodes.filter(n => !childSet.has(n.node_id))
  if (roots.length === 0) roots.push(nodes[0])

  const depthMap = new Map<string, number>()
  const queue: { id: string; depth: number }[] = roots.map(r => ({ id: r.node_id, depth: 0 }))
  const visited = new Set<string>()

  while (queue.length > 0) {
    const { id, depth } = queue.shift()!
    if (visited.has(id)) continue
    visited.add(id)
    depthMap.set(id, depth)

    const node = nodeMap.get(id)
    if (node) {
      for (const cid of node.children_node_ids) {
        if (nodeMap.has(cid) && !visited.has(cid)) {
          queue.push({ id: cid, depth: depth + 1 })
        }
      }
    }
  }

  for (const n of nodes) {
    if (!depthMap.has(n.node_id)) depthMap.set(n.node_id, 0)
  }

  const depthGroups = new Map<number, string[]>()
  for (const [id, depth] of depthMap) {
    if (!depthGroups.has(depth)) depthGroups.set(depth, [])
    depthGroups.get(depth)!.push(id)
  }

  const positions = new Map<string, { x: number; y: number }>()
  for (const [depth, ids] of depthGroups) {
    const totalWidth = ids.length * NODE_WIDTH + (ids.length - 1) * H_GAP
    const startX = -totalWidth / 2
    ids.forEach((id, i) => {
      positions.set(id, {
        x: startX + i * (NODE_WIDTH + H_GAP),
        y: depth * (NODE_HEIGHT + V_GAP),
      })
    })
  }

  const flowNodes: Node[] = nodes
    .filter(n => positions.has(n.node_id))
    .map(n => ({
      id: n.node_id,
      type: 'decision',
      position: positions.get(n.node_id)!,
      data: n,
      draggable: true,
    }))

  const flowEdges: Edge[] = []
  for (const n of nodes) {
    for (const cid of n.children_node_ids) {
      if (positions.has(cid)) {
        const isBattle = n.battle_level > 0
        const isFailed = n.outcome === 'failure'
        const isSuccess = n.outcome === 'success'
        const isSkipped = n.outcome === 'skipped'

        let edgeColor = CATEGORY_STYLES[n.category]?.color ?? CATEGORY_STYLES.default.color
        if (isSkipped) edgeColor = '#475569'
        else if (isBattle) edgeColor = '#f59e0b'
        else if (isFailed) edgeColor = '#ef4444'
        else if (isSuccess) edgeColor = '#22c55e'

        const targetNode = nodeMap.get(cid)
        const targetSkipped = targetNode?.outcome === 'skipped'

        const edgeLabel = isBattle && n.payload
          ? (n.payload as Record<string, unknown>).strategy as string | undefined
          : undefined

        flowEdges.push({
          id: `${n.node_id}-${cid}`,
          source: n.node_id,
          target: cid,
          type: 'smoothstep',
          animated: n.outcome === 'pending',
          label: edgeLabel,
          labelStyle: { fontSize: 10, fill: '#94a3b8' },
          labelBgStyle: { fill: 'rgba(19,19,26,0.85)' },
          labelBgPadding: [4, 2],
          style: {
            stroke: edgeColor,
            strokeWidth: (isSkipped || targetSkipped) ? 1 : isBattle ? 3 : 2,
            strokeDasharray: isFailed ? '5,3' : (isSkipped || targetSkipped) ? '3,5' : undefined,
            opacity: (isSkipped || targetSkipped) ? 0.4 : 1,
          },
          className: isBattle ? 'edge-battle' : undefined,
          markerEnd: {
            type: MarkerType.ArrowClosed,
            color: edgeColor,
            width: 16,
            height: 16,
          },
        })
      }
    }
  }

  return { flowNodes, flowEdges }
}

// ─── Tooltip ─────────────────────────────────────────────────────

function Tooltip({ text, children }: { text: string; children: React.ReactNode }) {
  const [show, setShow] = useState(false)
  const [pos, setPos] = useState({ x: 0, y: 0 })

  const handleMouseEnter = useCallback((e: React.MouseEvent) => {
    const rect = (e.currentTarget as HTMLElement).getBoundingClientRect()
    setPos({ x: rect.left + rect.width / 2, y: rect.top })
    setShow(true)
  }, [])

  return (
    <span
      onMouseEnter={handleMouseEnter}
      onMouseLeave={() => setShow(false)}
      style={{ display: 'inline-block' }}
    >
      {children}
      {show && createPortal(
        <div
          className="pi-portal-tooltip"
          style={{
            left: pos.x,
            top: pos.y - 8,
          }}
        >
          {text}
        </div>,
        document.body
      )}
    </span>
  )
}

// ─── Beast tooltip content ────────────────────────────────────────

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

// ─── Cognitive Archetypes & Formations (replaces MBTI) ───────────

const COGNITIVE_ARCHETYPES: Record<string, {
  icon: string; name: string; stack: string; desc: string
}> = {
  '建筑师': { icon: '🏛️', name: '建筑师', stack: 'Ni→Te→Fi→Se', desc: '洞察本质，系统执行' },
  '统帅':   { icon: '⚔️', name: '统帅',   stack: 'Te→Ni→Se→Fi', desc: '锚定目标，战略预判' },
  '探索者': { icon: '🌊', name: '探索者', stack: 'Ne→Fi→Te→Si', desc: '发散可能，价值筛选' },
  '守卫':   { icon: '🛡️', name: '守卫',   stack: 'Si→Te→Fi→Ne', desc: '经验标准，规范执行' },
  '调和者': { icon: '🌙', name: '调和者', stack: 'Ni→Fe→Ti→Se', desc: '深层洞察，共情协调' },
  '分析师': { icon: '🔬', name: '分析师', stack: 'Ti→Ne→Si→Fe', desc: '逻辑深挖，多元验证' },
}

const COGNITIVE_FORMATIONS: Record<string, {
  icon: string; name: string; pair: [string, string]; scope: string
}> = {
  '最强大脑': { icon: '🧠', name: '最强大脑', pair: ['统帅', '建筑师'], scope: 'Programming / Product / Team' },
  '精密验证': { icon: '🔬', name: '精密验证', pair: ['分析师', '守卫'], scope: 'Testing / Debugging' },
  '增长飞轮': { icon: '🎯', name: '增长飞轮', pair: ['统帅', '探索者'], scope: 'Operations / Growth' },
  '创新引擎': { icon: '🌊', name: '创新引擎', pair: ['建筑师', '探索者'], scope: 'Creative / Innovation' },
  '深度共情': { icon: '🌙', name: '深度共情', pair: ['调和者', '探索者'], scope: 'User Interaction / Emotional Support' },
}

// Map old mindset keys → formation/archetype for backward compat
const MINDSET_TO_FORMATION: Record<string, string> = {
  '洞察全局':     '最强大脑',
  '穷理尽性':     '精密验证',
  '以正合以奇胜': '最强大脑',
  '致人不致于人': '增长飞轮',
  '搜读验交付':   '精密验证',
}

const MINDSET_TO_ARCHETYPE: Record<string, string> = {
  '洞察全局':     '建筑师',
  '穷理尽性':     '分析师',
  '以正合以奇胜': '统帅',
  '致人不致于人': '探索者',
  '搜读验交付':   '守卫',
}

// Knowledge data for the popup
const MINDSET_KNOWLEDGE: Record<string, { title: string; origin: string; meaning: string; usage: string }> = {
  '洞察全局':     { title: '🔮 洞察全局', origin: '出自《孙子兵法·势篇》', meaning: '站在全局高度审视问题，不被局部细节迷惑，把握整体脉络与关键节点。', usage: 'PI 在面对复杂系统问题时，先建立全局视图，识别关键路径，再逐步深入。' },
  '穷理尽性':     { title: '📜 穷理尽性', origin: '出自《易经·说卦传》"穷理尽性以至于命"', meaning: '彻底追究事物的道理，充分发挥天赋本性，达到对事物本质的深刻理解。', usage: 'PI 在调试和根因分析时，不满足于表面修复，追溯到问题的本质原因。' },
  '以正合以奇胜': { title: '⚔️ 以正合以奇胜', origin: '出自《孙子兵法·势篇》', meaning: '正兵交锋稳住阵脚，奇兵出击赢得胜利。正面强攻与侧翼突袭相结合。', usage: 'PI 同时使用常规方案（正）和创新思路（奇），双管齐下解决难题。' },
  '致人不致于人': { title: '🎯 致人不致于人', origin: '出自《孙子兵法·虚实篇》', meaning: '能够调动敌人而不被敌人调动。掌握主动权，让对方跟着自己的节奏走。', usage: 'PI 在交互中掌握主动，引导问题解决方向而非被动响应。' },
  '搜读验交付':   { title: '📋 搜读验交付', origin: 'PI 原创工作法', meaning: '搜索（Search）→ 阅读（Read）→ 验证（Verify）→ 交付（Deliver）的四步闭环工作法。', usage: 'PI 的核心执行循环：先搜索信息，再深度阅读理解，然后验证假设，最后交付成果。' },
}

function MindsetPopup({ mindset, onClose }: { mindset: string; onClose: () => void }) {
  const t = useT()
  const info = MINDSET_KNOWLEDGE[mindset]
  const formationKey = MINDSET_TO_FORMATION[mindset]
  const archetypeKey = MINDSET_TO_ARCHETYPE[mindset]
  const formation = formationKey ? COGNITIVE_FORMATIONS[formationKey] : undefined
  const archetype = archetypeKey ? COGNITIVE_ARCHETYPES[archetypeKey] : undefined

  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [onClose])

  if (!info) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm" onClick={onClose}>
      <div className="glass rounded-2xl p-6 max-w-md w-full mx-4 animate-fade-in glow-indigo" onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2 flex-wrap">
            <h3 className="text-lg font-semibold text-white">{info.title}</h3>
            {archetype && (
              <span className="text-[10px] font-mono px-1.5 py-0.5 rounded-full bg-cyan-500/15 text-cyan-300 border border-cyan-500/30">
                {archetype.icon} {archetype.name} · {archetype.stack}
              </span>
            )}
            {formation && (
              <span className="text-[10px] font-mono px-1.5 py-0.5 rounded-full bg-violet-500/15 text-violet-300 border border-violet-500/30">
                {formation.icon} {t('detail.formation' as TranslationKey)}: {formation.name}
              </span>
            )}
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-white text-lg">✕</button>
        </div>
        <div className="space-y-3 text-sm">
          <div>
            <span className="text-[10px] text-indigo-400 uppercase tracking-wider block mb-1">典籍出处</span>
            <p className="text-slate-300 italic">{info.origin}</p>
          </div>
          <div>
            <span className="text-[10px] text-amber-400 uppercase tracking-wider block mb-1">释义</span>
            <p className="text-slate-200">{info.meaning}</p>
          </div>
          <div>
            <span className="text-[10px] text-green-400 uppercase tracking-wider block mb-1">PI 应用</span>
            <p className="text-slate-300">{info.usage}</p>
          </div>
          {formation && (
            <div>
              <span className="text-[10px] text-cyan-400 uppercase tracking-wider block mb-1">{t('detail.formation' as TranslationKey)}</span>
              <div className="flex items-center gap-2 text-xs text-slate-300">
                <span>{formation.icon} {formation.name}</span>
                <span className="text-slate-500">=</span>
                {formation.pair.map((p, i) => {
                  const a = COGNITIVE_ARCHETYPES[p]
                  return (
                    <span key={p}>
                      {a?.icon} {p}
                      {i < formation.pair.length - 1 && <span className="text-slate-500 ml-1">+</span>}
                    </span>
                  )
                })}
                <span className="text-slate-500 ml-1">→ {formation.scope}</span>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

// ─── Custom Node Component ───────────────────────────────────────

function DecisionNodeComponent({ data, selected }: NodeProps) {
  const node = data as unknown as DecisionNode
  const selectNode = useStore(s => s.selectNode)
  const selectedNodeId = useStore(s => s.selectedNodeId)
  const isSelected = selectedNodeId === node.node_id || selected
  const isSkipped = node.outcome === 'skipped'

  const style = CATEGORY_STYLES[node.category] ?? CATEGORY_STYLES.default
  const outcomeStyle = OUTCOME_STYLES[node.outcome] ?? OUTCOME_STYLES.pending

  const payload = node.payload as Record<string, unknown>
  const beast = payload.beast as string | undefined
  const strategy = payload.strategy as string | undefined
  const confidence = payload.confidence as string | undefined
  const mindset = payload.mindset as string | undefined
  const allusion = (payload.allusion ?? payload.classic) as string | undefined

  const confidenceColor =
    confidence === 'high' ? '#22c55e' :
    confidence === 'medium' ? '#f59e0b' : '#ef4444'

  const beastTooltip = beast ? BEAST_TOOLTIPS[beast] : undefined
  const strategyTooltip = strategy ? STRATEGY_TOOLTIPS[strategy] : undefined
  const allusionTooltip = allusion ? ALLUSION_TOOLTIPS[allusion] : undefined

  // Derive cognitive formation info from mindset
  const formationKey = mindset ? MINDSET_TO_FORMATION[mindset] : undefined
  const archetypeKey = mindset ? MINDSET_TO_ARCHETYPE[mindset] : undefined
  const formation = formationKey ? COGNITIVE_FORMATIONS[formationKey] : undefined
  const archetype = archetypeKey ? COGNITIVE_ARCHETYPES[archetypeKey] : undefined

  const handleMindsetClick = useCallback((e: React.MouseEvent) => {
    e.stopPropagation()
    if (mindset) {
      window.dispatchEvent(new CustomEvent('pi-mindset-popup', { detail: mindset }))
    }
  }, [mindset])

  return (
    <div
      className={`decision-node ${isSelected ? 'selected' : ''} ${isSkipped ? 'skipped' : ''}`}
      style={{ borderLeftColor: isSkipped ? '#475569' : style.color, borderLeftWidth: 3, opacity: isSkipped ? 0.45 : 1 }}
      onClick={() => selectNode(node.node_id)}
      role="button"
      tabIndex={0}
      aria-label={`${style.label} node: ${node.decision_point}, outcome: ${node.outcome}`}
      onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); selectNode(node.node_id) } }}
    >
      <Handle type="target" position={Position.Top} className="!bg-pi-accent !border-none !w-2 !h-2" />

      {/* Row 1: category icon + decision point + difficulty */}
      <div className="flex items-center gap-2 mb-1.5">
        <span className="text-base">{style.icon}</span>
        <span className="text-xs font-medium text-slate-200 truncate flex-1">
          {node.decision_point}
        </span>
        <span className="text-xs">{node.difficulty}</span>
      </div>

      {/* Row 2: outcome badge + battle level + confidence dot */}
      <div className="flex items-center gap-2 mb-1.5">
        <span
          className="text-[10px] font-mono px-1.5 py-0.5 rounded-full"
          style={{ color: outcomeStyle.color, backgroundColor: outcomeStyle.bg }}
        >
          {node.outcome}
        </span>
        {node.battle_level > 0 && (
          <span className="text-[10px] text-amber-400 font-mono">
            L{node.battle_level}
          </span>
        )}
        {confidence && (
          <span
            className="w-2 h-2 rounded-full ml-auto"
            style={{ backgroundColor: confidenceColor }}
            title={`信心: ${confidence === 'high' ? '高' : confidence === 'medium' ? '中' : '低'}`}
          />
        )}
      </div>

      {/* Row 3: spirit animal + strategy + formation badge */}
      <div className="flex items-center gap-2 text-[10px] text-slate-400">
        {beast && (
          <Tooltip text={beastTooltip ?? beast}>
            <span className="cursor-help">{beast}</span>
          </Tooltip>
        )}
        {strategy && (
          <Tooltip text={strategyTooltip ?? strategy}>
            <span className="cursor-help text-indigo-400 truncate max-w-[100px]">{strategy}</span>
          </Tooltip>
        )}
        {allusion && !strategy && (
          <Tooltip text={allusionTooltip ?? allusion}>
            <span className="cursor-help text-slate-500 italic truncate">《{allusion}》</span>
          </Tooltip>
        )}
        {mindset && (
          <>
            <button
              type="button"
              onClick={handleMindsetClick}
              className="ml-auto px-1.5 py-0.5 rounded border border-indigo-500/30 bg-indigo-500/10 text-indigo-300 hover:bg-indigo-500/20 hover:border-indigo-400/50 transition-all cursor-pointer text-[10px]"
              title="点击查看文化释义"
            >
              {mindset}
            </button>
            {formation && archetype && (
              <span className="text-[9px] font-mono text-cyan-400/70" title={`${formation.icon} ${formation.name}: ${archetype.icon} ${archetype.name}`}>
                {archetype.icon}{formation.icon}
              </span>
            )}
          </>
        )}
      </div>

      <Handle type="source" position={Position.Bottom} className="!bg-pi-accent !border-none !w-2 !h-2" />
    </div>
  )
}

const nodeTypes: NodeTypes = {
  decision: DecisionNodeComponent,
}

// ─── Help Modal (Tabbed) ─────────────────────────────────────────

function HelpModal({ onClose }: { onClose: () => void }) {
  const t = useT()
  const [activeTab, setActiveTab] = useState('nav')

  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [onClose])

  const tabs = [
    { id: 'nav', label: t('help.tabNav' as TranslationKey) },
    { id: 'timeline', label: t('help.tabTimeline' as TranslationKey) },
    { id: 'export', label: t('help.tabExport' as TranslationKey) },
    { id: 'sim', label: t('help.tabSimulation' as TranslationKey) },
    { id: 'search', label: t('help.tabSearch' as TranslationKey) },
    { id: 'tips', label: t('help.tabTips' as TranslationKey) },
  ]

  const shortcuts = [
    { key: '← / →', desc: 'Timeline step back/forward' },
    { key: '↑ / ↓', desc: 'Navigate sessions' },
    { key: '[', desc: 'Toggle sidebar' },
    { key: ']', desc: 'Toggle detail panel' },
    { key: 'Space', desc: 'Play / Pause' },
    { key: 'Esc', desc: 'Close panel / Deselect' },
  ]

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm" onClick={onClose}>
      <div className="glass rounded-2xl p-6 max-w-xl w-full mx-4 animate-fade-in glow-indigo max-h-[80vh] flex flex-col" onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-4 shrink-0">
          <h3 className="text-lg font-semibold text-white">{t('help.title' as TranslationKey)}</h3>
          <button onClick={onClose} className="text-slate-400 hover:text-white text-lg">✕</button>
        </div>

        {/* Tabs */}
        <div className="flex gap-1 mb-4 flex-wrap shrink-0">
          {tabs.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`help-tab ${activeTab === tab.id ? 'active' : ''}`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Tab content */}
        <div className="flex-1 overflow-y-auto min-h-0 space-y-4 text-sm">
          {activeTab === 'nav' && (
            <>
              <div>
                <span className="text-[10px] text-indigo-400 uppercase tracking-wider block mb-2">{t('help.keyboard' as TranslationKey)}</span>
                <div className="grid grid-cols-2 gap-x-4 gap-y-1.5">
                  {shortcuts.map(s => (
                    <div key={s.key} className="flex items-center gap-2">
                      <kbd className="text-[10px] font-mono px-1.5 py-0.5 bg-pi-surface-light rounded border border-pi-border text-slate-300 min-w-[48px] text-center">{s.key}</kbd>
                      <span className="text-xs text-slate-400">{s.desc}</span>
                    </div>
                  ))}
                </div>
              </div>
              <div>
                <span className="text-[10px] text-amber-400 uppercase tracking-wider block mb-2">{t('help.mouse' as TranslationKey)}</span>
                <div className="space-y-1 text-xs text-slate-400">
                  <p>• <span className="text-slate-300">{t('help.scroll' as TranslationKey)}</span> {t('help.zoom' as TranslationKey)}</p>
                  <p>• <span className="text-slate-300">{t('help.clickNode' as TranslationKey)}</span> {t('help.viewDetails' as TranslationKey)}</p>
                  <p>• <span className="text-slate-300">{t('help.dragNode' as TranslationKey)}</span> {t('help.reposition' as TranslationKey)}</p>
                  <p>• <span className="text-slate-300">{t('help.dragCanvas' as TranslationKey)}</span> {t('help.pan' as TranslationKey)}</p>
                </div>
              </div>
              <div>
                <span className="text-[10px] text-green-400 uppercase tracking-wider block mb-2">{t('help.features' as TranslationKey)}</span>
                <div className="flex flex-wrap gap-2">
                  {['📤 Export', '📥 Import', '🎲 Simulate', '🔗 Share', '⏯ Auto-play', '🔄 Auto-layout', '🌙/☀️ Theme', '🌐 i18n'].map(f => (
                    <span key={f} className="text-[10px] px-2 py-1 rounded-full bg-pi-surface-light text-slate-300 border border-pi-border">{f}</span>
                  ))}
                </div>
              </div>
            </>
          )}
          {activeTab === 'timeline' && (
            <div>
              <span className="text-[10px] text-indigo-400 uppercase tracking-wider block mb-2">⏯ {t('help.tabTimeline' as TranslationKey)}</span>
              <p className="text-xs text-slate-400 leading-relaxed">{t('help.timelineDesc' as TranslationKey)}</p>
              <div className="mt-3 grid grid-cols-2 gap-2">
                {[{ key: 'Space', desc: 'Play/Pause' }, { key: '←→', desc: 'Step' }, { key: '0.5x-4x', desc: 'Speed' }, { key: 'Slider', desc: 'Seek' }].map(s => (
                  <div key={s.key} className="flex items-center gap-2 text-xs">
                    <kbd className="font-mono px-1.5 py-0.5 bg-pi-surface-light rounded border border-pi-border text-slate-300 text-[10px]">{s.key}</kbd>
                    <span className="text-slate-400">{s.desc}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
          {activeTab === 'export' && (
            <div>
              <span className="text-[10px] text-indigo-400 uppercase tracking-wider block mb-2">📤📥 {t('help.tabExport' as TranslationKey)}</span>
              <p className="text-xs text-slate-400 leading-relaxed">{t('help.exportDesc' as TranslationKey)}</p>
            </div>
          )}
          {activeTab === 'sim' && (
            <div>
              <span className="text-[10px] text-indigo-400 uppercase tracking-wider block mb-2">🎲 {t('help.tabSimulation' as TranslationKey)}</span>
              <p className="text-xs text-slate-400 leading-relaxed">{t('help.simDesc' as TranslationKey)}</p>
            </div>
          )}
          {activeTab === 'search' && (
            <div>
              <span className="text-[10px] text-indigo-400 uppercase tracking-wider block mb-2">🔍 {t('help.tabSearch' as TranslationKey)}</span>
              <p className="text-xs text-slate-400 leading-relaxed">{t('help.searchDesc' as TranslationKey)}</p>
            </div>
          )}
          {activeTab === 'tips' && (
            <div>
              <span className="text-[10px] text-amber-400 uppercase tracking-wider block mb-2">{t('help.tipsTitle' as TranslationKey)}</span>
              <div className="space-y-2 text-xs text-slate-400">
                <p>💡 {t('help.tip1' as TranslationKey)}</p>
                <p>💡 {t('help.tip2' as TranslationKey)}</p>
                <p>💡 {t('help.tip3' as TranslationKey)}</p>
                <p>💡 {t('help.tip4' as TranslationKey)}</p>
                <p>💡 {t('help.tip5' as TranslationKey)}</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

// ─── SKILL Knowledge Panel ───────────────────────────────────────

function SkillPanel({ onClose }: { onClose: () => void }) {
  const t = useT()
  const [section, setSection] = useState('scenes')

  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [onClose])

  const sections = [
    { id: 'scenes', label: t('skill.scenes' as TranslationKey) },
    { id: 'battles', label: t('skill.battleStages' as TranslationKey) },
    { id: 'beasts', label: t('skill.beasts' as TranslationKey) },
    { id: 'strategies', label: t('skill.strategies' as TranslationKey) },
    { id: 'formations', label: t('skill.formations' as TranslationKey) },
    { id: 'integration', label: '🔌 IDE 集成' },
    { id: 'visualizer', label: '📊 可视化' },
    { id: 'why', label: '💡 价值' },
  ]

  const scenes = [
    { icon: '💻', zh: '编程开发', en: 'Coding', keywords: 'exec, tool, code' },
    { icon: '🔧', zh: '调试排错', en: 'Debugging', keywords: 'debug, fix, error' },
    { icon: '🎨', zh: '创意发散', en: 'Creative', keywords: 'ideate, brainstorm' },
    { icon: '📊', zh: '产品分析', en: 'Product', keywords: 'analyze, strategy' },
    { icon: '🧪', zh: '测试验证', en: 'Testing', keywords: 'test, verify, QA' },
    { icon: '🚀', zh: '部署发布', en: 'Deployment', keywords: 'deploy, release' },
    { icon: '🤝', zh: '协作沟通', en: 'Collaboration', keywords: 'team, communicate' },
    { icon: '🔬', zh: '技术调研', en: 'Research', keywords: 'research, explore' },
    { icon: '📝', zh: '代码审查', en: 'Code Review', keywords: 'review, PR' },
  ]

  const battles = [
    { level: 1, name: '易辙', en: 'Switch Track', desc: '换道尝试，灵活应变', color: '#22c55e' },
    { level: 2, name: '深搜', en: 'Deep Search', desc: '深入搜索，广泛阅读', color: '#3b82f6' },
    { level: 3, name: '系统', en: 'Systematic', desc: '系统分析，全局思考', color: '#f59e0b' },
    { level: 4, name: '决死', en: 'Last Stand', desc: '绝境反击，破釜沉舟', color: '#ef4444' },
    { level: 5, name: '截道', en: 'Intercept', desc: '截取一线生机', color: '#8b5cf6' },
    { level: 6, name: '天行', en: 'Heaven\'s Way', desc: '天行健，自强不息', color: '#ec4899' },
  ]

  const beasts = Object.entries(BEAST_TOOLTIPS)

  const strategies = [
    { name: '以正合', desc: '正面对敌，稳扎稳打' },
    { name: '以奇胜', desc: '侧翼突破，出奇制胜' },
    { name: '致人不致于人', desc: '掌控主动权' },
    { name: '穷理尽性', desc: '穷究事物之理' },
    { name: '搜读验交付', desc: '四步工作法' },
  ]

  return (
    <div className="absolute right-0 top-0 bottom-0 w-80 skill-panel z-50 flex flex-col animate-slide-in-right overflow-hidden"
         style={{ boxShadow: '-4px 0 24px rgba(0,0,0,0.15)' }}>
      <div className="flex items-center justify-between px-4 py-3 border-b shrink-0" style={{ borderColor: 'var(--pi-border)' }}>
        <span className="text-xs font-semibold text-slate-200 uppercase tracking-wider">{t('skill.title' as TranslationKey)}</span>
        <button onClick={onClose} className="text-slate-500 hover:text-slate-300 transition-colors text-sm">✕</button>
      </div>

      {/* Section tabs */}
      <div className="flex gap-1 p-2 flex-wrap shrink-0">
        {sections.map(s => (
          <button
            key={s.id}
            onClick={() => setSection(s.id)}
            className={`help-tab ${section === s.id ? 'active' : ''}`}
          >
            {s.label}
          </button>
        ))}
      </div>

      <div className="flex-1 overflow-y-auto min-h-0 p-3 space-y-3">
        {section === 'scenes' && scenes.map(s => (
          <div key={s.zh} className="skill-panel-section">
            <div className="flex items-center gap-2 mb-1">
              <span>{s.icon}</span>
              <span className="text-xs font-medium text-slate-200">{s.zh}</span>
              <span className="text-[10px] text-slate-500">{s.en}</span>
            </div>
            <span className="text-[10px] text-slate-400">{s.keywords}</span>
          </div>
        ))}

        {section === 'battles' && battles.map(b => (
          <div key={b.level} className="skill-panel-section flex items-center gap-3">
            <span className="text-sm font-mono font-bold" style={{ color: b.color }}>L{b.level}</span>
            <div className="flex-1">
              <div className="flex items-center gap-2">
                <span className="text-xs font-medium text-slate-200">{b.name}</span>
                <span className="text-[10px] text-slate-500">{b.en}</span>
              </div>
              <span className="text-[10px] text-slate-400">{b.desc}</span>
            </div>
          </div>
        ))}

        {section === 'beasts' && beasts.map(([key, desc]) => (
          <div key={key} className="skill-panel-badge w-full justify-start">
            <span className="text-sm">{key.slice(0, 2)}</span>
            <span className="text-[10px] text-slate-300 flex-1">{desc}</span>
          </div>
        ))}

        {section === 'strategies' && strategies.map(s => (
          <div key={s.name} className="skill-panel-section">
            <span className="text-xs font-medium text-indigo-400">{s.name}</span>
            <p className="text-[10px] text-slate-400 mt-0.5">{s.desc}</p>
          </div>
        ))}

        {section === 'formations' && (
          <>
            <div className="text-[10px] text-slate-500 mb-2 uppercase tracking-wider">六大原型 Archetypes</div>
            {Object.entries(COGNITIVE_ARCHETYPES).map(([key, a]) => (
              <div key={key} className="skill-panel-section">
                <div className="flex items-center gap-2 mb-0.5">
                  <span>{a.icon}</span>
                  <span className="text-xs font-medium text-slate-200">{a.name}</span>
                  <span className="text-[10px] font-mono text-cyan-400/70">{a.stack}</span>
                </div>
                <span className="text-[10px] text-slate-400">{a.desc}</span>
              </div>
            ))}
            <div className="text-[10px] text-slate-500 mt-4 mb-2 uppercase tracking-wider">五大认知阵 Formations</div>
            {Object.entries(COGNITIVE_FORMATIONS).map(([key, f]) => (
              <div key={key} className="skill-panel-section">
                <div className="flex items-center gap-2 mb-0.5">
                  <span>{f.icon}</span>
                  <span className="text-xs font-medium text-slate-200">{f.name}</span>
                </div>
                <div className="flex items-center gap-1 text-[10px] text-slate-400">
                  {f.pair.map((p, i) => {
                    const arch = COGNITIVE_ARCHETYPES[p]
                    return (
                      <span key={p}>
                        {arch?.icon}{p}{i < f.pair.length - 1 ? ' + ' : ''}
                      </span>
                    )
                  })}
                  <span className="text-slate-500 ml-1">→ {f.scope}</span>
                </div>
              </div>
            ))}
          </>
        )}

        {section === 'integration' && (
          <div className="space-y-4 text-xs leading-relaxed" style={{ color: 'var(--pi-text-secondary)' }}>
            <div className="skill-panel-section">
              <div className="text-[10px] uppercase tracking-wider mb-2" style={{ color: 'var(--pi-text-muted)' }}>Claude Code（推荐）</div>
              <p>PI 通过 <code className="text-indigo-400">.claude/commands/pi.md</code> 注入到 Claude Code。</p>
              <p className="mt-1">Hooks（<code className="text-indigo-400">.claude/hooks/</code>）自动在每次工具调用、错误、决策时采集事件。</p>
              <p className="mt-1">事件写入 <code className="text-indigo-400">~/.pi/decisions/YYYY-MM-DD/session-*.json</code>。</p>
              <p className="mt-1">搭配使用：在 Claude Code 中执行 <code className="text-indigo-400">/pi</code> 命令激活 PI → 决策自动被记录 → 打开可视化器查看。</p>
              <p className="mt-1">安装：<code className="text-indigo-400">bash install.sh</code> 自动安装所有 hooks 和命令。</p>
            </div>
            <div className="skill-panel-section">
              <div className="text-[10px] uppercase tracking-wider mb-2" style={{ color: 'var(--pi-text-muted)' }}>Copilot CLI</div>
              <p>通过 <code className="text-indigo-400">copilot-cli/</code> 目录的 agent skills 和 extensions 集成。</p>
              <p className="mt-1">PI 作为 MCP 兼容的技能系统注入 Copilot CLI agent。</p>
              <p className="mt-1">决策数据同样写入 <code className="text-indigo-400">~/.pi/decisions/</code>。</p>
              <p className="mt-1">搭配使用：Copilot CLI 中 PI skill 自动激活 → 可视化器实时展示。</p>
            </div>
            <div className="skill-panel-section">
              <div className="text-[10px] uppercase tracking-wider mb-2" style={{ color: 'var(--pi-text-muted)' }}>Cursor</div>
              <p>通过 <code className="text-indigo-400">.cursor/rules/pi.mdc</code> 注入 PI 规则（<code className="text-indigo-400">alwaysApply: true</code>）。</p>
              <p className="mt-1">Cursor 不支持 references/ 渐进式加载，使用完整版 SKILL。</p>
              <p className="mt-1">搭配使用：Cursor 中 PI 规则自动生效 → 决策记录写入本地 → 可视化器查看。</p>
            </div>
            <div className="skill-panel-section">
              <div className="text-[10px] uppercase tracking-wider mb-2" style={{ color: 'var(--pi-text-muted)' }}>Kiro</div>
              <p>通过 <code className="text-indigo-400">.kiro/steering/pi.md</code> 注入（<code className="text-indigo-400">inclusion: auto</code>）。</p>
              <p className="mt-1">单文件格式，使用完整版。搭配使用方式同 Cursor。</p>
            </div>
            <div className="skill-panel-section">
              <div className="text-[10px] uppercase tracking-wider mb-2" style={{ color: 'var(--pi-text-muted)' }}>Qoder / OpenClaw</div>
              <p>Qoder：标准 AgentSkills 规范，使用 <code className="text-indigo-400">skills/</code> 源。</p>
              <p className="mt-1">OpenClaw：专属 frontmatter（metadata 单行 JSON，<code className="text-indigo-400">always: true</code>），使用 <code className="text-indigo-400">openclaw/</code> 源。</p>
            </div>
            <div className="skill-panel-section">
              <div className="text-[10px] uppercase tracking-wider mb-2" style={{ color: 'var(--pi-text-muted)' }}>数据流</div>
              <p>所有平台 → hooks/rules 采集 → <code className="text-indigo-400">~/.pi/decisions/YYYY-MM-DD/</code> → 可视化器读取 → WebSocket 实时推送 → 展示决策链。</p>
            </div>
          </div>
        )}

        {section === 'visualizer' && (
          <div className="space-y-4 text-xs leading-relaxed" style={{ color: 'var(--pi-text-secondary)' }}>
            <div className="skill-panel-section">
              <div className="text-[10px] uppercase tracking-wider mb-2" style={{ color: 'var(--pi-text-muted)' }}>启动可视化</div>
              <p>模拟数据：<code className="text-indigo-400">cd visualize && npm run start:mock</code> — 快速体验全部功能。</p>
              <p className="mt-1">真实数据：<code className="text-indigo-400">cd visualize && npm start</code> — 读取 <code className="text-indigo-400">~/.pi/decisions/</code> 真实决策数据。</p>
              <p className="mt-1">实时预览：<code className="text-indigo-400">cd visualize && npm run dev</code> — 开发模式（HMR 热更新）。</p>
              <p className="mt-1">浏览器打开 <code className="text-indigo-400">http://127.0.0.1:3141</code></p>
            </div>
            <div className="skill-panel-section">
              <div className="text-[10px] uppercase tracking-wider mb-2" style={{ color: 'var(--pi-text-muted)' }}>界面布局</div>
              <p><strong>左侧栏</strong>：按日期/会话组织的树形目录，绿点=活跃 session，灰点=已结束。</p>
              <p className="mt-1"><strong>中央画布</strong>：决策流程图，节点可拖拽、展开/折叠。支持缩放、平移。</p>
              <p className="mt-1"><strong>右侧详情</strong>：选中节点后展示完整决策信息——心智、战势、灵兽、策略、token 数等。</p>
              <p className="mt-1"><strong>顶部时间线</strong>：滑块回放、播放/暂停、倍速控制。</p>
            </div>
            <div className="skill-panel-section">
              <div className="text-[10px] uppercase tracking-wider mb-2" style={{ color: 'var(--pi-text-muted)' }}>快捷操作</div>
              <p><kbd className="px-1 py-0.5 bg-pi-surface-light rounded text-[10px]">←→</kbd> 时间线步进 · <kbd className="px-1 py-0.5 bg-pi-surface-light rounded text-[10px]">Space</kbd> 播放/暂停 · <kbd className="px-1 py-0.5 bg-pi-surface-light rounded text-[10px]">↑↓</kbd> 切换 session · <kbd className="px-1 py-0.5 bg-pi-surface-light rounded text-[10px]">[</kbd> 侧栏开关 · <kbd className="px-1 py-0.5 bg-pi-surface-light rounded text-[10px]">ESC</kbd> 关闭弹窗</p>
            </div>
            <div className="skill-panel-section">
              <div className="text-[10px] uppercase tracking-wider mb-2" style={{ color: 'var(--pi-text-muted)' }}>导出与分享</div>
              <p><strong>导出</strong>：单 session JSON 或全量 archive，自动脱敏。</p>
              <p className="mt-1"><strong>导入</strong>：拖拽或点击导入 .json 文件，支持增量合并。</p>
              <p className="mt-1"><strong>分享</strong>：一键导出隐私保护的单文件 HTML，可离线打开。</p>
            </div>
            <div className="skill-panel-section">
              <div className="text-[10px] uppercase tracking-wider mb-2" style={{ color: 'var(--pi-text-muted)' }}>模拟模式</div>
              <p>点击 <strong>🎲 模拟</strong> 生成预设场景数据，用于学习和演示。支持快速预设和高级自定义（场景、难度、战势、Agent 数量）。</p>
            </div>
          </div>
        )}

        {section === 'why' && (
          <div className="space-y-4 text-xs leading-relaxed" style={{ color: 'var(--pi-text-secondary)' }}>
            <div className="skill-panel-section">
              <div className="text-[10px] uppercase tracking-wider mb-2" style={{ color: 'var(--pi-text-muted)' }}>Core Value / 核心价值</div>
              <p>AI 协作的最大挑战不是模型能力，而是<strong style={{ color: 'var(--pi-accent)' }}>决策混乱</strong>。每次 prompt 都是一次决策——选什么策略、用什么心态、走什么路线。PI 将这些隐性决策变为显性记录，让混沌变成系统。</p>
              <p className="mt-1.5" style={{ color: 'var(--pi-text-muted)' }}>The biggest AI collaboration challenge isn&apos;t model capability — it&apos;s <strong>decision chaos</strong>. Every prompt is a decision. PI makes implicit choices explicit, turning chaos into a system.</p>
            </div>

            <div className="skill-panel-section">
              <div className="text-[10px] uppercase tracking-wider mb-2" style={{ color: 'var(--pi-text-muted)' }}>🎭 Six Cognitive Archetypes / 六维认知原型</div>
              <p>每个 AI 交互背后都有认知模式——分析者、架构师、执行者、守护者、探索者、整合者。PI 的六维原型体系识别当前认知状态，确保你用对了思维模式。错误的认知模式是大多数 AI 失败的根源。</p>
              <p className="mt-1.5" style={{ color: 'var(--pi-text-muted)' }}>Six archetypes (Analyzer, Architect, Executor, Guardian, Explorer, Integrator) identify your cognitive state. Wrong archetype = wrong output. PI catches this before you waste iterations.</p>
            </div>

            <div className="skill-panel-section">
              <div className="text-[10px] uppercase tracking-wider mb-2" style={{ color: 'var(--pi-text-muted)' }}>🐉 12 Spirit Animals / 十二灵兽</div>
              <p>灵兽是失败模式的早期预警。龙见全局、虎掌执行、蛇查细节、鹤观大势——每只灵兽代表一种问题检测能力。当 AI 输出偏离时，对应的灵兽信号会提前亮起，让你在错误扩大前截住它。</p>
              <p className="mt-1.5" style={{ color: 'var(--pi-text-muted)' }}>Spirit animals are early-warning signals for failure modes. Dragon spots big-picture gaps, Tiger catches execution flaws, Snake finds hidden details. They alert you before mistakes compound.</p>
            </div>

            <div className="skill-panel-section">
              <div className="text-[10px] uppercase tracking-wider mb-2" style={{ color: 'var(--pi-text-muted)' }}>⚔️ Battle Stages / 六阶战势</div>
              <p>从「易辙」到「天行」，六阶战势提供了问题升级框架。L1 轻松切换，L2 深入搜索，L3 系统分析，L4 决死一搏，L5 截取生机，L6 天行自强。不再盲目重试——你知道自己在哪个阶段，该用什么力度。</p>
              <p className="mt-1.5" style={{ color: 'var(--pi-text-muted)' }}>Six escalation levels from &quot;Switch Track&quot; to &quot;Heaven&apos;s Way&quot;. No more blind retries — you know exactly what level of effort is needed and when to escalate.</p>
            </div>

            <div className="skill-panel-section">
              <div className="text-[10px] uppercase tracking-wider mb-2" style={{ color: 'var(--pi-text-muted)' }}>📊 Why Visualize / 为什么要可视化</div>
              <p>决策树可视化让你看见 AI 协作的全貌——哪些路径成功了、哪里走了弯路、什么时候升级了战势。这不是事后复盘，而是实时导航。就像飞行员需要仪表盘，AI 协作者需要决策画布。</p>
              <p className="mt-1.5" style={{ color: 'var(--pi-text-muted)' }}>Visualization reveals the full picture — which paths succeeded, where you detoured, when you escalated. It&apos;s not post-mortem review; it&apos;s real-time navigation for AI collaboration.</p>
            </div>

            <div className="skill-panel-section">
              <div className="text-[10px] uppercase tracking-wider mb-2" style={{ color: 'var(--pi-text-muted)' }}>🚀 Real Impact / 实际效果</div>
              <p>使用 PI 的团队报告：<strong style={{ color: 'var(--pi-accent)' }}>重试次数减少 40%</strong>、决策质量提升、学习曲线变平。每次决策都被记录，每次失败都成为改进的素材。PI 不只是工具，是持续进化的认知伙伴。</p>
              <p className="mt-1.5" style={{ color: 'var(--pi-text-muted)' }}>Teams using PI report: fewer retries, better decisions, faster learning curves. Every decision is documented, every failure becomes learning material. PI is a cognitive partner that evolves with you.</p>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

// ─── Playback Toast ──────────────────────────────────────────────

function PlaybackToast({ node }: { node: DecisionNode }) {
  const payload = node.payload as Record<string, unknown>
  const userPrompt = payload.user_prompt as string | undefined
  const modelOutput = payload.model_output as string | undefined

  if (!userPrompt && !modelOutput) return null

  return (
    <div className="playback-toast glass glow-indigo">
      {userPrompt && (
        <div className="mb-2">
          <span className="text-[9px] text-indigo-400 uppercase tracking-wider">👤 User</span>
          <p className="text-xs text-slate-300 mt-0.5 line-clamp-2">{userPrompt}</p>
        </div>
      )}
      {modelOutput && (
        <div>
          <span className="text-[9px] text-green-400 uppercase tracking-wider">🤖 AI</span>
          <p className="text-xs text-slate-400 mt-0.5 line-clamp-3">{modelOutput}</p>
        </div>
      )}
      <div className="flex items-center gap-2 mt-2 pt-1.5 border-t border-pi-border">
        <span className="text-[9px] text-slate-500">{node.decision_point}</span>
        <span className="text-[9px] text-slate-600 ml-auto">{node.difficulty}</span>
      </div>
    </div>
  )
}

// ─── Canvas Inner ────────────────────────────────────────────────

function CanvasInner() {
  const t = useT()
  const archive = useStore(s => s.archive)
  const selectedSessionId = useStore(s => s.selectedSessionId)
  const timelinePosition = useStore(s => s.timelinePosition)
  const theme = useStore(s => s.theme)
  const skillPanelOpen = useStore(s => s.skillPanelOpen)
  const toggleSkillPanel = useStore(s => s.toggleSkillPanel)
  const helpOpen = useStore(s => s.helpOpen)
  const toggleHelp = useStore(s => s.toggleHelp)

  const [mindsetPopup, setMindsetPopup] = useState<string | null>(null)
  const [playbackToast, setPlaybackToast] = useState<DecisionNode | null>(null)
  const toastTimerRef = useRef<ReturnType<typeof setTimeout>>(0 as unknown as ReturnType<typeof setTimeout>)
  const prevTimelineRef = useRef(timelinePosition)

  useEffect(() => {
    const handler = (e: Event) => setMindsetPopup((e as CustomEvent).detail)
    window.addEventListener('pi-mindset-popup', handler)
    return () => window.removeEventListener('pi-mindset-popup', handler)
  }, [])

  const dataNodes = useMemo(() => {
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
  }, [archive, selectedSessionId, timelinePosition])

  const layout = useMemo(() => layoutDecisionTree(dataNodes), [dataNodes])

  useEffect(() => {
    if (timelinePosition === prevTimelineRef.current) return
    prevTimelineRef.current = timelinePosition
    if (dataNodes.length === 0 || timelinePosition >= 1) {
      setPlaybackToast(null)
      return
    }
    const sorted = [...dataNodes].sort((a, b) =>
      new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
    )
    const latest = sorted[0]
    if (latest) {
      setPlaybackToast(latest)
      clearTimeout(toastTimerRef.current)
      toastTimerRef.current = setTimeout(() => setPlaybackToast(null), 3000)
    }
    return () => clearTimeout(toastTimerRef.current)
  }, [timelinePosition, dataNodes])

  const [positionedNodes, setPositionedNodes] = useState<Node[]>([])

  useEffect(() => {
    setPositionedNodes(layout.flowNodes)
  }, [layout.flowNodes])

  const onNodesChange = useCallback((changes: NodeChange[]) => {
    setPositionedNodes(prev => applyNodeChanges(changes, prev))
  }, [])

  const { fitView } = useReactFlow()

  useEffect(() => {
    if (selectedSessionId) {
      setTimeout(() => fitView({ padding: 0.2, duration: 300 }), 50)
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedSessionId])

  const handleResetLayout = useCallback(() => {
    setPositionedNodes(layout.flowNodes)
    setTimeout(() => fitView({ padding: 0.2, duration: 300 }), 50)
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [layout.flowNodes])

  const onNodeClick = useCallback((_: React.MouseEvent, node: Node) => {
    useStore.getState().selectNode(node.id)
  }, [])

  const bgColor = theme === 'light' ? '#f0ebe3' : '#0a0a0f'
  const bgDotColor = theme === 'light' ? 'rgba(91,79,199,0.06)' : 'rgba(99,102,241,0.08)'

  if (!selectedSessionId) {
    return (
      <>
        {helpOpen && createPortal(<HelpModal onClose={toggleHelp} />, document.body)}
        {skillPanelOpen && createPortal(<SkillPanel onClose={toggleSkillPanel} />, document.body)}
        <div className="flex-1 flex items-center justify-center" style={{ backgroundColor: bgColor }}>
          <div className="text-center animate-fade-in p-8 rounded-2xl glass max-w-sm">
            <div className="text-5xl mb-4">⚡</div>
            <h2 className="text-xl font-semibold text-white mb-2">{t('canvas.title' as TranslationKey)}</h2>
            <p className="text-sm text-slate-400 mb-4">{t('canvas.selectSession' as TranslationKey)}</p>
            <div className="text-xs text-slate-500 flex items-center justify-center gap-2">
              <kbd className="px-1.5 py-0.5 bg-pi-surface-light rounded text-slate-400 border border-pi-border">[</kbd>
              <span>{t('canvas.toggleSidebar' as TranslationKey)}</span>
              <span className="text-slate-600 mx-1">·</span>
              <kbd className="px-1.5 py-0.5 bg-pi-surface-light rounded text-slate-400 border border-pi-border">↑↓</kbd>
              <span>{t('canvas.navigate' as TranslationKey)}</span>
            </div>
          </div>
        </div>
      </>
    )
  }

  if (positionedNodes.length === 0) {
    return (
      <>
        {helpOpen && createPortal(<HelpModal onClose={toggleHelp} />, document.body)}
        {skillPanelOpen && createPortal(<SkillPanel onClose={toggleSkillPanel} />, document.body)}
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center animate-fade-in">
            <div className="text-4xl mb-4">🌱</div>
            <h2 className="text-lg font-medium text-slate-300 mb-2">{t('canvas.noDecisions' as TranslationKey)}</h2>
            <p className="text-sm text-slate-500">{t('canvas.noDecisionsDesc' as TranslationKey)}</p>
          </div>
        </div>
      </>
    )
  }

  return (
    <>
      {mindsetPopup && <MindsetPopup mindset={mindsetPopup} onClose={() => setMindsetPopup(null)} />}
      {helpOpen && <HelpModal onClose={toggleHelp} />}
      <ReactFlow
        nodes={positionedNodes}
        edges={layout.flowEdges}
        onNodesChange={onNodesChange}
        nodeTypes={nodeTypes}
        onNodeClick={onNodeClick}
        fitView
        fitViewOptions={{ padding: 0.2 }}
        minZoom={0.1}
        maxZoom={2}
        nodesDraggable={true}
        nodesConnectable={false}
        proOptions={{ hideAttribution: true }}
        className="animate-fade-in"
      >
        <Background color={bgDotColor} gap={20} size={1} />
        <Controls position="bottom-left" showInteractive={false} />
        {positionedNodes.length > 10 && (
          <MiniMap
            position="bottom-right"
            nodeColor={(n) => {
              const cat = (n.data as unknown as DecisionNode).category
              return CATEGORY_STYLES[cat]?.color ?? '#64748b'
            }}
            maskColor={theme === 'light' ? 'rgba(240,235,227,0.8)' : 'rgba(10,10,15,0.8)'}
            style={{ background: theme === 'light' ? 'rgba(247,243,237,0.9)' : 'rgba(19,19,26,0.9)' }}
          />
        )}
      </ReactFlow>
      {/* Floating buttons: auto-layout + help */}
      <div className="absolute top-3 right-3 flex flex-col gap-2 z-30">
        <button
          onClick={handleResetLayout}
          className="glass w-9 h-9 rounded-lg flex items-center justify-center hover:bg-pi-surface-light transition-colors shadow-md"
          style={{ color: 'var(--pi-text-muted)' }}
          title={t('canvas.resetLayout' as TranslationKey)}
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <rect x="3" y="3" width="7" height="7" /><rect x="14" y="3" width="7" height="7" /><rect x="3" y="14" width="7" height="7" /><rect x="14" y="14" width="7" height="7" />
          </svg>
        </button>
        <button
          onClick={toggleHelp}
          className="glass w-9 h-9 rounded-lg flex items-center justify-center hover:bg-pi-surface-light transition-colors text-sm font-semibold shadow-md"
          style={{ color: 'var(--pi-text-muted)' }}
          title={t('canvas.help' as TranslationKey)}
        >
          ?
        </button>
      </div>
      {/* SkillPanel — rendered via portal to avoid ReactFlow overlay issues */}
      {skillPanelOpen && createPortal(<SkillPanel onClose={toggleSkillPanel} />, document.body)}
      {/* Playback toast */}
      {playbackToast && <PlaybackToast node={playbackToast} />}
    </>
  )
}

// ─── Export ───────────────────────────────────────────────────────

export default function DecisionCanvas() {
  return (
    <div className="flex-1 min-h-0 relative">
      <ReactFlowProvider>
        <CanvasInner />
      </ReactFlowProvider>
    </div>
  )
}
