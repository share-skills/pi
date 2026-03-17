/**
 * PI Decision Visualizer — Mock Data Generator
 *
 * Generates comprehensive mock sessions covering all SKILL.md scenarios:
 * - 9 scenes (编程/调试/测试/产品/运营/创意/协作/交互/陪伴)
 * - 6 battle stages (易辙/深搜/系统/决死/截道/天行)
 * - 12 spirit animals
 * - Multiple difficulty levels (⚡/🧠/🐲)
 * - Multi-agent interactions (Leader/Teammate/Coach)
 * - Decision tree with parent-child edges
 *
 * Licensed under the Apache License, Version 2.0
 */

import type { DecisionSession, DecisionNode, DecisionArchive, AgentProfile, SessionMetrics, ModelInfo } from '../src/types.js'

// ─── Constants from SKILL_META.md ──────────────────────────────

const SCENES = [
  { name: '编程', label: 'coding', icon: '💻' },
  { name: '调试', label: 'debug', icon: '🔧' },
  { name: '测试', label: 'testing', icon: '🧪' },
  { name: '产品', label: 'product', icon: '📊' },
  { name: '运营', label: 'ops', icon: '🚀' },
  { name: '创意发散', label: 'creative', icon: '🎨' },
  { name: '协作', label: 'collab', icon: '🤝' },
  { name: '交互', label: 'interaction', icon: '💬' },
  { name: '陪伴', label: 'companion', icon: '🌟' },
]

const BATTLE_STAGES = [
  { level: 1, name: '易辙', strategy: '换道破局', classic: '避实击虚', icon: '⚡' },
  { level: 2, name: '深搜', strategy: '穷搜广读', classic: '知彼知己', icon: '🦈' },
  { level: 3, name: '系统', strategy: '庙算全局', classic: '庙算多胜', icon: '🐲' },
  { level: 4, name: '决死', strategy: '全新路线', classic: '置之死地', icon: '🦁' },
  { level: 5, name: '截道', strategy: '截取一线', classic: '截取一线生机', icon: '☯️' },
  { level: 6, name: '天行', strategy: '协同出击', classic: '天行健', icon: '🐝' },
]

const BEASTS = ['🦅鹰', '🐺🐯狼虎', '🦁狮', '🐎马', '🐂牛', '🦈鲨', '🐝蜂', '🦊狐', '🐲龙', '🦄独角兽', '🦉猫头鹰', '🐬海豚']

const STRATEGIES = ['以正合', '以奇胜', '致人不致于人', '穷理尽性', '搜读验交付', '截教·最小实证', '截教·截道三法', '好钢刀刃']

const DIFFICULTIES = ['⚡', '🧠', '🐲']

const MODELS: ModelInfo[] = [
  { name: 'Claude Opus 4.6', provider: 'Anthropic', input_tokens: 0, output_tokens: 0 },
  { name: 'GPT-5.4', provider: 'OpenAI', input_tokens: 0, output_tokens: 0 },
  { name: 'Gemini 3 Pro', provider: 'Google', input_tokens: 0, output_tokens: 0 },
  { name: 'Claude Sonnet 4.6', provider: 'Anthropic', input_tokens: 0, output_tokens: 0 },
]

const CATEGORIES = ['exec', 'battle', 'external', 'decision', 'retry']
const OUTCOMES = ['success', 'failure', 'pending', 'captured', 'skipped']

let nodeCounter = 0
function makeId(): string {
  nodeCounter++
  return `mock-${Date.now().toString(36)}-${nodeCounter.toString(36).padStart(4, '0')}`
}

function rand<T>(arr: T[]): T {
  return arr[Math.floor(Math.random() * arr.length)]
}

function randInt(min: number, max: number): number {
  return Math.floor(Math.random() * (max - min + 1)) + min
}

function makeTimestamp(base: Date, offsetMinutes: number): string {
  return new Date(base.getTime() + offsetMinutes * 60000).toISOString()
}

/**
 * Creates a decision tree with edges (parent-child relationships).
 * The tree has a root node, with branches for each major decision.
 */
function makeDecisionTree(
  sessionId: string,
  scene: typeof SCENES[number],
  difficulty: string,
  baseTime: Date,
  battleLevel: number,
  nodeCount: number,
): DecisionNode[] {
  const nodes: DecisionNode[] = []
  const ids: string[] = []

  for (let i = 0; i < nodeCount; i++) {
    const id = makeId()
    ids.push(id)
    
    // First node is root, subsequent nodes are children of previous nodes
    const children: string[] = []
    
    const isLeaf = i >= nodeCount - Math.ceil(nodeCount / 3)
    const category = i === 0 ? 'decision' : rand(CATEGORIES)
    const bl = Math.min(i, battleLevel)
    const stage = bl > 0 ? BATTLE_STAGES[Math.min(bl - 1, 5)] : null
    
    const outcomes: string[] = isLeaf
      ? (battleLevel >= 4 ? ['failure', 'failure', 'success'] : ['success', 'success', 'failure'])
      : ['pending', 'success']

    const node: DecisionNode = {
      node_id: id,
      session_id: sessionId,
      timestamp: makeTimestamp(baseTime, i * 2 + randInt(0, 3)),
      label: i === 0 ? `🧠 PI · ${scene.name}` : undefined,
      category,
      decision_point: i === 0
        ? `场景启动·${scene.name}`
        : category === 'battle'
          ? `战势${bl}阶·${stage?.name ?? ''}·${stage?.strategy ?? ''}`
          : category === 'exec'
            ? rand(['tool.execution', 'code.generation', 'code.review', 'build.verify'])
            : category === 'retry'
              ? `重试·第${randInt(1, 3)}次`
              : rand(['event.capture', 'external.search', 'user.feedback', 'session.checkpoint']),
      scene: scene.label,
      difficulty,
      battle_level: bl,
      failure_count: Math.max(0, bl - 1),
      payload: {
        strategy: stage?.strategy ?? rand(STRATEGIES),
        beast: bl > 0 ? rand(BEASTS) : undefined,
        classic: stage?.classic ?? undefined,
        mindset: rand(['洞察全局', '穷理尽性', '以正合以奇胜', '致人不致于人', '搜读验交付']),
        confidence: rand(['high', 'medium', 'low']),
        allusion: stage?.classic ?? rand(['避实击虚', '先为不可胜', '知彼知己', '投之亡地']),
        user_prompt: rand([
          `帮我重构这个认证模块，提升安全性`,
          `分析 ${scene.name} 场景下的主要瓶颈`,
          `优化这段代码的性能，减少内存分配`,
          `调试为什么这个 API 在高并发下会超时`,
          `设计一个支持多租户的数据库方案`,
          `给这个函数写全面的单元测试`,
          `代码 review 这个 PR 并指出潜在问题`,
        ]),
        model_output: rand([
          `分析代码结构发现3个潜在问题：\n1. 认证 token 未设置过期时间\n2. 密码哈希使用了弱算法 MD5\n3. SQL 查询存在注入风险\n建议按优先级逐项修复。`,
          `经过深度搜索，发现根本原因是连接池配置不当。当前 maxConnections=10，建议调整为 50，并启用连接预热机制。`,
          `重构方案：将单体 service 拆分为 3 个职责单一的模块，预计减少代码耦合度 60%，测试覆盖率提升至 85%+。`,
          `性能分析结果：主要瓶颈在第 47 行的 N+1 查询问题。引入 DataLoader 批量加载后，响应时间从 800ms 降至 120ms。`,
          `已识别 5 个边界情况需要处理：空值传递、并发写入、网络超时重试、权限越界、数据一致性校验。`,
        ]),
        tokens: {
          input: randInt(200, 3000),
          output: randInt(300, 6000),
        },
        reasoning: bl > 2 ? rand([
          `问题复杂度超过预期，标准路径不可行。需要重新评估假设，尝试截教策略——以最小实证验证核心路径。`,
          `前两次尝试均失败，根本原因在于对问题本质理解不够深入。切换到深搜模式，穷举所有可能的失败原因。`,
          `系统性问题，单点修复无效。需要从架构层面重新设计，确保全局一致性。`,
        ]) : undefined,
        interaction_chain: i < 3 ? [
          { role: 'user', content: `请分析 ${scene.name} 场景下的核心问题` },
          { role: 'assistant', content: `收到，正在分析中...识别到 ${randInt(2, 5)} 个关键节点` },
          ...(bl > 0 ? [
            { role: 'user', content: `战势升级，需要更深入的策略` },
            { role: 'assistant', content: `启动 ${stage?.name ?? '战势'} 模式，采用${stage?.strategy ?? '截教'}策略` },
          ] : []),
        ] : undefined,
        tool_calls: category === 'exec' ? [
          { tool: rand(['bash', 'read_file', 'write_file', 'search', 'grep']), args: `${scene.name} 相关操作`, result: rand(['success', 'error']) },
        ] : undefined,
      },
      outcome: rand(outcomes),
      children_node_ids: children, // will be filled below
      agent_id: undefined,
    }
    nodes.push(node)
  }

  // Build tree structure: each non-leaf parent gets 1-3 children
  // Simple approach: linear chain with branches
  for (let i = 0; i < nodes.length; i++) {
    const children: string[] = []
    // Each node except the last few gets children
    if (i < nodes.length - 1) {
      // Always connect to the next node (main chain)
      children.push(ids[i + 1])
      // Sometimes add a branch (if there's a node further ahead)
      if (i + 2 < nodes.length && Math.random() > 0.6) {
        children.push(ids[i + 2])
      }
    }
    nodes[i].children_node_ids = children
  }

  return nodes
}

/**
 * Session 1: Simple coding task — linear chain, no battles
 */
function makeCodingSession(date: string): DecisionSession {
  const id = `mock-coding-${date}`
  const baseTime = new Date(`${date}T09:00:00Z`)
  const nodes = makeDecisionTree(id, SCENES[0], '⚡', baseTime, 0, 5)
  // Mark all as success
  nodes.forEach(n => n.outcome = 'success')
  nodes[nodes.length - 1].decision_point = '交付·自检三令'
  
  return {
    session_id: id,
    date,
    created_at: baseTime.toISOString(),
    summary: '实现用户认证模块 — JWT + bcrypt',
    scene: 'coding',
    difficulty: '⚡',
    model_info: { ...MODELS[0], input_tokens: 2400, output_tokens: 3600 },
    agents: [{ agent_id: 'main', name: 'PI Leader', role: 'leader' }],
    nodes,
    metrics: { total_tokens: 6000, complexity_score: 2, deep_exploration_count: 0, loop_count: 0, quality_score: 4, max_battle_level: 0, beast_activations: 0 },
    isActive: false,
  }
}

/**
 * Session 2: Debug with battle escalation (易辙→深搜→系统)
 */
function makeDebugBattleSession(date: string): DecisionSession {
  const id = `mock-debug-battle-${date}`
  const baseTime = new Date(`${date}T10:30:00Z`)
  const nodes = makeDecisionTree(id, SCENES[1], '🧠', baseTime, 3, 12)
  
  // Make the battle escalation visible
  nodes[0].decision_point = '调试启动·六步法'
  nodes[1].category = 'exec'
  nodes[1].decision_point = '调试·读错误信息'
  nodes[1].outcome = 'failure'
  nodes[2].category = 'retry'
  nodes[2].decision_point = '第1次失败·分析根因'
  nodes[2].outcome = 'failure'
  nodes[3].category = 'battle'
  nodes[3].decision_point = '战势1阶·易辙·换道破局'
  nodes[3].battle_level = 1
  nodes[3].payload = { strategy: '以正合以奇胜', beast: '🦅鹰', classic: '避实击虚', mindset: '换道破局' }
  nodes[4].category = 'exec'
  nodes[4].decision_point = '新方案·重构接口'
  nodes[4].outcome = 'failure'
  nodes[5].category = 'battle'
  nodes[5].decision_point = '战势2阶·深搜·穷搜广读'
  nodes[5].battle_level = 2
  nodes[5].payload = { strategy: '穷理尽性', beast: '🦈鲨', classic: '知彼知己', mindset: '穷搜广读' }
  nodes[6].category = 'external'
  nodes[6].decision_point = '外部搜索·GitHub Issues'
  nodes[6].outcome = 'captured'
  nodes[7].category = 'battle'
  nodes[7].decision_point = '战势3阶·系统·九令洞鉴'
  nodes[7].battle_level = 3
  nodes[7].payload = { strategy: '庙算全局', beast: '🐲龙', classic: '庙算多胜', mindset: '庙算全局' }
  nodes[8].category = 'exec'
  nodes[8].decision_point = '系统方案·全局重构'
  nodes[8].outcome = 'success'
  nodes[nodes.length - 2].decision_point = '验证·build + test 通过'
  nodes[nodes.length - 2].outcome = 'success'
  nodes[nodes.length - 1].decision_point = '交付·明约确认'
  nodes[nodes.length - 1].outcome = 'success'

  return {
    session_id: id,
    date,
    created_at: baseTime.toISOString(),
    summary: 'WebSocket 连接泄漏修复 — 战势三阶后成功',
    scene: 'debug',
    difficulty: '🧠',
    model_info: { ...MODELS[1], input_tokens: 15000, output_tokens: 22000 },
    agents: [{ agent_id: 'main', name: 'PI Leader', role: 'leader' }],
    nodes,
    metrics: { total_tokens: 37000, complexity_score: 4, deep_exploration_count: 2, loop_count: 3, quality_score: 3, max_battle_level: 3, beast_activations: 3 },
    isActive: false,
  }
}

/**
 * Session 3: Multi-agent team — Leader + 2 Teammates + Coach
 */
function makeMultiAgentSession(date: string): DecisionSession {
  const id = `mock-team-${date}`
  const baseTime = new Date(`${date}T14:00:00Z`)
  
  const agents: AgentProfile[] = [
    { agent_id: 'leader', name: 'PI Leader', role: 'leader', model: 'Claude Opus 4.6' },
    { agent_id: 'tm-alpha', name: 'Alpha Reviewer', role: 'teammate', model: 'GPT-5.4' },
    { agent_id: 'tm-beta', name: 'Beta Tester', role: 'teammate', model: 'Gemini 3 Pro' },
    { agent_id: 'coach', name: 'PI Coach', role: 'coach', model: 'Claude Opus 4.6' },
  ]

  const nodes: DecisionNode[] = []
  const rootId = makeId()
  const reviewId = makeId()
  const testId = makeId()
  const coachId = makeId()
  const mergeId = makeId()
  const deliverId = makeId()

  nodes.push({
    node_id: rootId, session_id: id, timestamp: makeTimestamp(baseTime, 0),
    category: 'decision', decision_point: '团队任务分派·Leader决策', scene: 'collab',
    difficulty: '🐲', battle_level: 0, failure_count: 0, outcome: 'success',
    payload: { strategy: '致人不致于人', mindset: '全局统帅', confidence: 'high' },
    children_node_ids: [reviewId, testId, coachId], agent_id: 'leader',
  })

  nodes.push({
    node_id: reviewId, session_id: id, timestamp: makeTimestamp(baseTime, 5),
    category: 'exec', decision_point: '代码审查·Alpha Reviewer', scene: 'collab',
    difficulty: '🧠', battle_level: 0, failure_count: 0, outcome: 'success',
    payload: { strategy: '审码四维', beast: '🐺🐯狼虎', mindset: '消除确认偏差', confidence: 'high' },
    children_node_ids: [mergeId], agent_id: 'tm-alpha',
  })

  nodes.push({
    node_id: testId, session_id: id, timestamp: makeTimestamp(baseTime, 5),
    category: 'exec', decision_point: '方向性测试·Beta Tester', scene: 'testing',
    difficulty: '🧠', battle_level: 0, failure_count: 0, outcome: 'success',
    payload: { strategy: '验证矩阵', beast: '🦊狐', mindset: '审视产出', confidence: 'medium' },
    children_node_ids: [mergeId], agent_id: 'tm-beta',
  })

  nodes.push({
    node_id: coachId, session_id: id, timestamp: makeTimestamp(baseTime, 3),
    category: 'external', decision_point: 'Coach巡检·松懈检测', scene: 'collab',
    difficulty: '⚡', battle_level: 0, failure_count: 0, outcome: 'captured',
    payload: { strategy: '反模式十戒检测', mindset: '巡检无阻塞', confidence: 'high' },
    children_node_ids: [mergeId], agent_id: 'coach',
  })

  nodes.push({
    node_id: mergeId, session_id: id, timestamp: makeTimestamp(baseTime, 15),
    category: 'decision', decision_point: 'Leader综合·对向验证结论', scene: 'collab',
    difficulty: '🐲', battle_level: 0, failure_count: 0, outcome: 'success',
    payload: { strategy: '决策三权·综合', mindset: '全局收敛' },
    children_node_ids: [deliverId], agent_id: 'leader',
  })

  nodes.push({
    node_id: deliverId, session_id: id, timestamp: makeTimestamp(baseTime, 20),
    category: 'exec', decision_point: '交付·善始善终', scene: 'collab',
    difficulty: '⚡', battle_level: 0, failure_count: 0, outcome: 'success',
    payload: { strategy: '交付六令', mindset: '明约确认' },
    children_node_ids: [], agent_id: 'leader',
  })

  return {
    session_id: id,
    date,
    created_at: baseTime.toISOString(),
    summary: '多Agent协作·代码审查+方向性测试+Coach巡检',
    scene: 'collab',
    difficulty: '🐲',
    model_info: { ...MODELS[0], input_tokens: 45000, output_tokens: 62000 },
    agents,
    nodes,
    metrics: { total_tokens: 107000, complexity_score: 5, deep_exploration_count: 3, loop_count: 0, quality_score: 5, max_battle_level: 0, beast_activations: 2 },
    isActive: false,
  }
}

/**
 * Session 4: Extreme battle — all 6 stages, ending at 天行
 */
function makeExtremeBattleSession(date: string): DecisionSession {
  const id = `mock-extreme-${date}`
  const baseTime = new Date(`${date}T16:00:00Z`)
  const nodes: DecisionNode[] = []
  const ids: string[] = []
  
  // Root
  const rootId = makeId()
  ids.push(rootId)
  nodes.push({
    node_id: rootId, session_id: id, timestamp: makeTimestamp(baseTime, 0),
    category: 'decision', decision_point: '场景启动·编程·极难任务', scene: 'coding',
    difficulty: '🐲', battle_level: 0, failure_count: 0, outcome: 'pending',
    payload: { strategy: '穷理尽性', mindset: '迎难而上', confidence: 'medium' },
    children_node_ids: [], // filled later
  })

  // Create each battle stage
  for (const stage of BATTLE_STAGES) {
    const stageId = makeId()
    ids.push(stageId)
    
    // Attempt node
    const attemptId = makeId()
    ids.push(attemptId)
    
    nodes.push({
      node_id: stageId, session_id: id, timestamp: makeTimestamp(baseTime, stage.level * 10),
      category: 'battle', decision_point: `战势${stage.level}阶·${stage.name}·${stage.strategy}`,
      scene: 'coding', difficulty: '🐲', battle_level: stage.level,
      failure_count: stage.level, outcome: stage.level < 6 ? 'failure' : 'success',
      payload: {
        strategy: stage.strategy, beast: BEASTS[stage.level - 1],
        classic: stage.classic, mindset: stage.strategy, confidence: stage.level >= 5 ? 'low' : 'medium',
        allusion: stage.classic,
      },
      children_node_ids: [attemptId],
    })

    nodes.push({
      node_id: attemptId, session_id: id, timestamp: makeTimestamp(baseTime, stage.level * 10 + 5),
      category: stage.level === 6 ? 'exec' : 'retry',
      decision_point: stage.level === 6 ? '天行·全认知原型协同·突破!' : `尝试·${stage.strategy}·失败`,
      scene: 'coding', difficulty: '🐲', battle_level: stage.level,
      failure_count: stage.level, outcome: stage.level === 6 ? 'success' : 'failure',
      payload: { strategy: stage.strategy, beast: BEASTS[stage.level], confidence: stage.level >= 5 ? 'low' : 'medium' },
      children_node_ids: [],
    })
  }

  // Connect the chain: root → stage1 → attempt1 → stage2 → attempt2 → ...
  nodes[0].children_node_ids = [ids[1]]
  for (let i = 1; i < ids.length - 1; i++) {
    const node = nodes.find(n => n.node_id === ids[i])
    if (node && node.children_node_ids.length === 0) {
      node.children_node_ids = [ids[i + 1]]
    }
  }

  // Final delivery
  const finalId = makeId()
  nodes.push({
    node_id: finalId, session_id: id, timestamp: makeTimestamp(baseTime, 75),
    category: 'exec', decision_point: '交付·历经六阶战势·终于突破', scene: 'coding',
    difficulty: '🐲', battle_level: 6, failure_count: 6, outcome: 'success',
    payload: { strategy: '善始善终', mindset: '绝境重生', beast: '🐝蜂', confidence: 'high' },
    children_node_ids: [],
  })
  // Connect last attempt to delivery
  nodes[nodes.length - 2].children_node_ids = [finalId]

  return {
    session_id: id,
    date,
    created_at: baseTime.toISOString(),
    summary: '极限调试·六阶战势全部触发·天行突破',
    scene: 'coding',
    difficulty: '🐲',
    model_info: { ...MODELS[0], input_tokens: 85000, output_tokens: 120000 },
    agents: [{ agent_id: 'main', name: 'PI Leader', role: 'leader' }],
    nodes,
    metrics: { total_tokens: 205000, complexity_score: 5, deep_exploration_count: 6, loop_count: 7, quality_score: 4, max_battle_level: 6, beast_activations: 6 },
    isActive: false,
  }
}

/**
 * Session 5: Creative brainstorm — wide tree
 */
function makeCreativeSession(date: string): DecisionSession {
  const id = `mock-creative-${date}`
  const baseTime = new Date(`${date}T11:00:00Z`)
  
  const rootId = makeId()
  const branch1 = makeId()
  const branch2 = makeId()
  const branch3 = makeId()
  const b1a = makeId(), b1b = makeId()
  const b2a = makeId()
  const b3a = makeId(), b3b = makeId()
  const converge = makeId()

  const nodes: DecisionNode[] = [
    { node_id: rootId, session_id: id, timestamp: makeTimestamp(baseTime, 0), category: 'decision', decision_point: '创意发散·无为发散→收放', scene: 'creative', difficulty: '🧠', battle_level: 0, failure_count: 0, outcome: 'success', payload: { strategy: '无为发散', beast: '🐬海豚', mindset: '触类旁通', confidence: 'high' }, children_node_ids: [branch1, branch2, branch3] },
    { node_id: branch1, session_id: id, timestamp: makeTimestamp(baseTime, 3), category: 'exec', decision_point: '方案A·React Server Components', scene: 'creative', difficulty: '🧠', battle_level: 0, failure_count: 0, outcome: 'success', payload: { strategy: '以正合', mindset: '标准路线' }, children_node_ids: [b1a, b1b] },
    { node_id: branch2, session_id: id, timestamp: makeTimestamp(baseTime, 3), category: 'exec', decision_point: '方案B·WASM + Rust（未选择）', scene: 'creative', difficulty: '🐲', battle_level: 0, failure_count: 0, outcome: 'skipped', payload: { strategy: '以奇胜', mindset: '激进路线', beast: '🦄独角兽' }, children_node_ids: [b2a] },
    { node_id: branch3, session_id: id, timestamp: makeTimestamp(baseTime, 4), category: 'external', decision_point: '方案C·跨域类比·参考游戏引擎', scene: 'creative', difficulty: '🧠', battle_level: 0, failure_count: 0, outcome: 'captured', payload: { strategy: '截教·截道三法', beast: '🐬海豚', mindset: '跨域求解' }, children_node_ids: [b3a, b3b] },
    { node_id: b1a, session_id: id, timestamp: makeTimestamp(baseTime, 8), category: 'exec', decision_point: '原型验证·RSC 方案', scene: 'creative', difficulty: '⚡', battle_level: 0, failure_count: 0, outcome: 'success', payload: { strategy: '最小实证' }, children_node_ids: [converge] },
    { node_id: b1b, session_id: id, timestamp: makeTimestamp(baseTime, 10), category: 'exec', decision_point: '性能基准·RSC 延迟测试', scene: 'testing', difficulty: '⚡', battle_level: 0, failure_count: 0, outcome: 'success', payload: { strategy: '验证矩阵' }, children_node_ids: [converge] },
    { node_id: b2a, session_id: id, timestamp: makeTimestamp(baseTime, 12), category: 'exec', decision_point: '调研·WASM 生态评估（放弃）', scene: 'creative', difficulty: '🧠', battle_level: 0, failure_count: 0, outcome: 'skipped', payload: { strategy: '穷理尽性', mindset: '生态不成熟' }, children_node_ids: [converge] },
    { node_id: b3a, session_id: id, timestamp: makeTimestamp(baseTime, 9), category: 'decision', decision_point: '游戏引擎·ECS 模式借鉴', scene: 'creative', difficulty: '🧠', battle_level: 0, failure_count: 0, outcome: 'success', payload: { strategy: '跨域类比', beast: '🐬海豚' }, children_node_ids: [converge] },
    { node_id: b3b, session_id: id, timestamp: makeTimestamp(baseTime, 11), category: 'external', decision_point: '参考·Bevy 渲染管线', scene: 'creative', difficulty: '🧠', battle_level: 0, failure_count: 0, outcome: 'captured', payload: {} }, 
    { node_id: converge, session_id: id, timestamp: makeTimestamp(baseTime, 18), category: 'decision', decision_point: '收敛·方案比选·选择RSC+ECS', scene: 'creative', difficulty: '🧠', battle_level: 0, failure_count: 0, outcome: 'success', payload: { strategy: '方案比选', mindset: '收放自如', beast: '🦉猫头鹰' }, children_node_ids: [] },
  ]
  nodes[8].children_node_ids = [converge] // b3b → converge

  return {
    session_id: id,
    date,
    created_at: baseTime.toISOString(),
    summary: '创意发散·三方案并行探索·最终收敛RSC+ECS',
    scene: 'creative',
    difficulty: '🧠',
    model_info: { ...MODELS[3], input_tokens: 12000, output_tokens: 18000 },
    agents: [{ agent_id: 'main', name: 'PI Leader', role: 'leader' }],
    nodes,
    metrics: { total_tokens: 30000, complexity_score: 3, deep_exploration_count: 1, loop_count: 0, quality_score: 5, max_battle_level: 0, beast_activations: 3 },
    isActive: false,
  }
}

/**
 * Session 6: Live/active session — companion mode
 */
function makeLiveSession(date: string): DecisionSession {
  const id = `mock-live-${date}`
  const now = new Date()
  const baseTime = new Date(now.getTime() - 10 * 60000) // started 10 min ago

  const nodes = makeDecisionTree(id, SCENES[8], '⚡', baseTime, 0, 3)
  nodes.forEach(n => n.outcome = 'pending')
  nodes[0].decision_point = '陪伴模式·交互启动'
  nodes[0].payload = { strategy: '共振五式·明心', mindset: '共情陪伴', beast: '🐬海豚' }

  return {
    session_id: id,
    date,
    created_at: baseTime.toISOString(),
    summary: '当前活跃会话 — 实时监控中',
    scene: 'companion',
    difficulty: '⚡',
    model_info: { ...MODELS[0], input_tokens: 800, output_tokens: 1200 },
    agents: [{ agent_id: 'main', name: 'PI Leader', role: 'leader' }],
    nodes,
    metrics: { total_tokens: 2000, complexity_score: 1, deep_exploration_count: 0, loop_count: 0, quality_score: 3, max_battle_level: 0, beast_activations: 0 },
    isActive: true,
    lastEventAt: new Date().toISOString(),
  }
}

/**
 * Session 7: Product analysis session
 */
function makeProductSession(date: string): DecisionSession {
  const id = `mock-product-${date}`
  const baseTime = new Date(`${date}T13:00:00Z`)
  const nodes = makeDecisionTree(id, SCENES[3], '🧠', baseTime, 1, 8)
  
  nodes[0].decision_point = '产品分析·需求拆解'
  nodes[0].payload = { strategy: '穷理尽性', mindset: '需求本质', beast: '🦅鹰' }
  nodes[1].decision_point = '用户故事·梳理核心流程'
  nodes[2].decision_point = '竞品分析·三维对比'
  nodes[3].decision_point = '技术评审·可行性验证'
  nodes[3].category = 'battle'
  nodes[3].battle_level = 1
  nodes[3].payload = { strategy: '以正合以奇胜', beast: '🦅鹰', classic: '避实击虚' }
  nodes[4].decision_point = '方案确定·MVP 范围'
  nodes[4].outcome = 'success'
  
  return {
    session_id: id,
    date,
    created_at: baseTime.toISOString(),
    summary: '产品需求拆解·竞品分析·MVP定义',
    scene: 'product',
    difficulty: '🧠',
    model_info: { ...MODELS[2], input_tokens: 8000, output_tokens: 12000 },
    agents: [{ agent_id: 'main', name: 'PI Leader', role: 'leader' }],
    nodes,
    metrics: { total_tokens: 20000, complexity_score: 3, deep_exploration_count: 1, loop_count: 1, quality_score: 4, max_battle_level: 1, beast_activations: 1 },
    isActive: false,
  }
}

/**
 * Session 8: Testing session with 截教 strategy
 */
function makeTestingSession(date: string): DecisionSession {
  const id = `mock-testing-jiejiao-${date}`
  const baseTime = new Date(`${date}T15:30:00Z`)
  const nodes = makeDecisionTree(id, SCENES[2], '🐲', baseTime, 5, 10)
  
  nodes[0].decision_point = '测试·复杂集成测试场景'
  nodes[3].category = 'battle'
  nodes[3].decision_point = '战势4阶·决死·全新路线'
  nodes[3].battle_level = 4
  nodes[3].payload = { strategy: '截教·最小实证', beast: '🦁狮', classic: '置之死地', mindset: '决死一搏' }
  nodes[5].category = 'battle'
  nodes[5].decision_point = '战势5阶·截道·截取一线生机'
  nodes[5].battle_level = 5
  nodes[5].payload = { strategy: '截教·截道三法', beast: '🐲龙', classic: '截取一线生机', mindset: '非标路径' }
  
  return {
    session_id: id,
    date,
    created_at: baseTime.toISOString(),
    summary: '集成测试·截教策略触发·截道三法',
    scene: 'testing',
    difficulty: '🐲',
    model_info: { ...MODELS[1], input_tokens: 32000, output_tokens: 48000 },
    agents: [{ agent_id: 'main', name: 'PI Leader', role: 'leader' }],
    nodes,
    metrics: { total_tokens: 80000, complexity_score: 5, deep_exploration_count: 4, loop_count: 5, quality_score: 3, max_battle_level: 5, beast_activations: 4 },
    isActive: false,
  }
}

/**
 * Generate the complete mock archive with all session types
 */
export function generateMockArchive(): DecisionArchive {
  const today = new Date().toISOString().slice(0, 10)
  const yesterday = new Date(Date.now() - 86400000).toISOString().slice(0, 10)
  const twoDaysAgo = new Date(Date.now() - 2 * 86400000).toISOString().slice(0, 10)

  const sessions: DecisionSession[] = [
    // Today
    makeLiveSession(today),
    makeCodingSession(today),
    makeDebugBattleSession(today),
    makeMultiAgentSession(today),
    // Yesterday
    makeExtremeBattleSession(yesterday),
    makeCreativeSession(yesterday),
    makeProductSession(yesterday),
    // Two days ago
    makeTestingSession(twoDaysAgo),
  ]

  return {
    sessions,
    generatedAt: new Date().toISOString(),
    sourceDir: '~/.pi/decisions (mock)',
  }
}
