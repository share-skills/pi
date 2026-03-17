/**
 * PI Decision Visualizer — i18n (Chinese/English)
 *
 * All translatable strings organized by component/section.
 * Usage: const t = useT(); t('topbar.export')
 */

export type Lang = 'zh' | 'en'

const zh = {
  // TopBar
  'topbar.title': 'PI 可视化',
  'topbar.simulate': '🎲 模拟',
  'topbar.export': '📤 导出',
  'topbar.import': '📥 导入',
  'topbar.live': '实时',
  'topbar.reconnecting': '重连中',
  'topbar.offline': '离线',
  'topbar.hideSidebar': '收起侧栏',
  'topbar.showSidebar': '展开侧栏',
  'topbar.stepBack': '后退一步',
  'topbar.stepForward': '前进一步',
  'topbar.play': '播放',
  'topbar.pause': '暂停',
  'topbar.genSimData': '生成模拟数据',
  'topbar.exportSession': '导出当前会话',
  'topbar.exportAll': '导出全部会话',
  'topbar.importArchive': '导入存档',
  'topbar.speed': '播放速度',
  'topbar.skillPanel': '📖 知识',
  'topbar.helpGuide': '❓ 帮助',

  // Simulation
  'sim.title': '🎲 模拟数据生成',
  'sim.quick': '⚡ 快速',
  'sim.advanced': '🔧 高级',
  'sim.scene': '场景 Scene',
  'sim.difficulty': '难度 Difficulty',
  'sim.battleLevel': '战势等级 Battle Level',
  'sim.agentCount': 'Agent 数量',
  'sim.nodeCount': '节点数 Nodes',
  'sim.generate': '🚀 生成',
  'sim.generating': '⏳ 生成中...',
  'sim.failMsg': '模拟数据生成失败，请确认服务器支持 --mock 模式',
  'sim.noServer': '无法连接服务器',
  'sim.footer': '生成的数据覆盖 SKILL.md 的九大场景、六阶战势、十二灵兽',

  // Scenes
  'scene.coding': '💻 编程开发',
  'scene.debug': '🔧 调试排错',
  'scene.creative': '🎨 创意发散',
  'scene.product': '📊 产品分析',
  'scene.testing': '🧪 测试验证',
  'scene.deployment': '🚀 部署发布',
  'scene.collaboration': '🤝 协作沟通',
  'scene.research': '🔬 技术调研',
  'scene.review': '📝 代码审查',

  // Difficulty
  'diff.easy': '简单',
  'diff.medium': '中等',
  'diff.hard': '困难',

  // Simulation scenarios
  'simScenario.coding': '简单线性链，无战势',
  'simScenario.debug-battle': '易辙→深搜→系统',
  'simScenario.multi-agent': 'Leader+Teammate+Coach',
  'simScenario.extreme': '全部6阶战势',
  'simScenario.creative': '3方案并行+收敛',
  'simScenario.product': '需求→竞品→MVP',
  'simScenario.testing-jiejiao': '截教策略触发',
  'simScenario.all': '生成所有8个模拟会话',

  // Canvas
  'canvas.title': 'PI Decision Visualizer',
  'canvas.selectSession': '从侧栏选择一个会话来可视化决策树',
  'canvas.toggleSidebar': '切换侧栏',
  'canvas.navigate': '导航',
  'canvas.noDecisions': '暂无决策',
  'canvas.noDecisionsDesc': '此会话暂无决策节点可显示',
  'canvas.resetLayout': '重置布局',
  'canvas.help': '帮助和快捷键',
  'canvas.clickForKnowledge': '点击查看文化释义',

  // Detail drawer
  'detail.decisionDetails': '决策详情',
  'detail.sessionOverview': '会话概览',
  'detail.scene': '场景',
  'detail.difficulty': '难度',
  'detail.battleLevel': '战势等级',
  'detail.failures': '失败次数',
  'detail.time': '时间',
  'detail.agent': 'Agent',
  'detail.cogState': 'PI认知状态',
  'detail.beast': '灵兽',
  'detail.mindset': '心境',
  'detail.confidence': '信心',
  'detail.battleInfo': '战势信息',
  'detail.strategy': '策略',
  'detail.allusion': '典故',
  'detail.tokens': 'Tokens',
  'detail.interaction': '交互记录',
  'detail.userPrompt': '用户指令',
  'detail.reasoning': 'AI推理',
  'detail.modelOutput': '模型输出',
  'detail.dialogChain': '对话链',
  'detail.rawPayload': 'Raw Payload',
  'detail.model': '模型',
  'detail.provider': '提供商',
  'detail.created': '创建时间',
  'detail.agents': 'Agents',
  'detail.metrics': '指标',
  'detail.noSummary': '无摘要',
  'detail.formation': '认知阵',

  // Metrics
  'metrics.tokens': 'Tokens',
  'metrics.complexity': '复杂度',
  'metrics.deepExplore': '深度探索',
  'metrics.loops': '循环',
  'metrics.quality': '质量',
  'metrics.maxBattle': '最高战势',
  'metrics.beast': '灵兽',

  // Status bar
  'status.session': '会话',
  'status.loaded': '已加载',
  'status.sessions': '个会话',
  'status.connected': '已连接',
  'status.disconnected': '未连接',

  // Tree nav
  'tree.sessions': '会话列表',
  'tree.noSessions': '暂无会话',
  'tree.noSummary': '无摘要',
  'tree.confirmDelete': '再次点击确认',
  'tree.delete': '删除会话',

  // SKILL panel
  'skill.title': 'PI SKILL 知识库',
  'skill.scenes': '九大场景',
  'skill.battleStages': '六阶战势',
  'skill.beasts': '十二灵兽',
  'skill.strategies': '五略',
  'skill.formations': '认知阵',

  // Help guide
  'help.title': '⚡ PI Visualizer — 使用指南',
  'help.tabNav': '导航',
  'help.tabTimeline': '时间轴',
  'help.tabExport': '导入/导出',
  'help.tabSimulation': '模拟',
  'help.tabSearch': '搜索/过滤',
  'help.tabTips': '技巧',
  'help.keyboard': '⌨️ 键盘快捷键',
  'help.mouse': '🖱️ 鼠标操作',
  'help.features': '✨ 功能',
  'help.scroll': '滚动',
  'help.zoom': '缩放',
  'help.clickNode': '点击节点',
  'help.viewDetails': '查看详情',
  'help.dragNode': '拖动节点',
  'help.reposition': '重新定位',
  'help.dragCanvas': '拖动画布',
  'help.pan': '平移',
  'help.timelineDesc': '使用顶栏时间轴控件回放决策过程。按空格键播放/暂停，左右方向键逐步控制。',
  'help.exportDesc': '导出当前会话或全部存档为 JSON 文件。导入 JSON 文件恢复历史会话数据。',
  'help.simDesc': '使用模拟模式生成测试数据，覆盖九大场景、六阶战势、十二灵兽等 SKILL 体系。',
  'help.searchDesc': '在侧栏中浏览按日期分组的会话列表，点击选择会话查看决策树。',
  'help.tipsTitle': '💡 使用技巧',
  'help.tip1': '点击心境标签可查看中华经典文化释义',
  'help.tip2': '悬停灵兽/策略/典故可查看详细说明',
  'help.tip3': '使用模拟模式快速生成各种场景测试数据',
  'help.tip4': '支持拖动节点自定义布局，点击网格按钮重置',
  'help.tip5': '时间轴播放时会显示当前决策的悬浮卡片',

  // Cognitive formations
  'cog.architect': '建筑师',
  'cog.commander': '统帅',
  'cog.explorer': '探索者',
  'cog.guardian': '守卫',
  'cog.harmonizer': '调和者',
  'cog.analyst': '分析师',
} as const

const en: Record<keyof typeof zh, string> = {
  // TopBar
  'topbar.title': 'PI Visualizer',
  'topbar.simulate': '🎲 Simulate',
  'topbar.export': '📤 Export',
  'topbar.import': '📥 Import',
  'topbar.live': 'Live',
  'topbar.reconnecting': 'Reconnecting',
  'topbar.offline': 'Offline',
  'topbar.hideSidebar': 'Hide sidebar',
  'topbar.showSidebar': 'Show sidebar',
  'topbar.stepBack': 'Step back',
  'topbar.stepForward': 'Step forward',
  'topbar.play': 'Play',
  'topbar.pause': 'Pause',
  'topbar.genSimData': 'Generate simulation data',
  'topbar.exportSession': 'Export current session',
  'topbar.exportAll': 'Export all sessions',
  'topbar.importArchive': 'Import archive',
  'topbar.speed': 'Playback speed',
  'topbar.skillPanel': '📖 SKILL',
  'topbar.helpGuide': '❓ Help',

  // Simulation
  'sim.title': '🎲 Simulation Generator',
  'sim.quick': '⚡ Quick',
  'sim.advanced': '🔧 Advanced',
  'sim.scene': 'Scene',
  'sim.difficulty': 'Difficulty',
  'sim.battleLevel': 'Battle Level',
  'sim.agentCount': 'Agent Count',
  'sim.nodeCount': 'Node Count',
  'sim.generate': '🚀 Generate',
  'sim.generating': '⏳ Generating...',
  'sim.failMsg': 'Failed to generate mock data. Ensure server supports --mock mode',
  'sim.noServer': 'Cannot connect to server',
  'sim.footer': 'Generated data covers 9 scenes, 6 battle stages, 12 spirit animals',

  // Scenes
  'scene.coding': '💻 Coding',
  'scene.debug': '🔧 Debugging',
  'scene.creative': '🎨 Creative',
  'scene.product': '📊 Product',
  'scene.testing': '🧪 Testing',
  'scene.deployment': '🚀 Deployment',
  'scene.collaboration': '🤝 Collaboration',
  'scene.research': '🔬 Research',
  'scene.review': '📝 Code Review',

  // Difficulty
  'diff.easy': 'Easy',
  'diff.medium': 'Medium',
  'diff.hard': 'Hard',

  // Simulation scenarios
  'simScenario.coding': 'Simple linear chain, no battles',
  'simScenario.debug-battle': 'Switch → Deep Search → Systematic',
  'simScenario.multi-agent': 'Leader+Teammate+Coach',
  'simScenario.extreme': 'All 6 battle stages',
  'simScenario.creative': '3 parallel plans + convergence',
  'simScenario.product': 'Requirements → Competitor → MVP',
  'simScenario.testing-jiejiao': 'Jiejiao strategy trigger',
  'simScenario.all': 'Generate all 8 simulation sessions',

  // Canvas
  'canvas.title': 'PI Decision Visualizer',
  'canvas.selectSession': 'Select a session from the sidebar to visualize its decision tree',
  'canvas.toggleSidebar': 'Toggle sidebar',
  'canvas.navigate': 'Navigate',
  'canvas.noDecisions': 'No Decisions Yet',
  'canvas.noDecisionsDesc': 'This session has no decision nodes to display',
  'canvas.resetLayout': 'Reset layout',
  'canvas.help': 'Help & shortcuts',
  'canvas.clickForKnowledge': 'Click for cultural context',

  // Detail drawer
  'detail.decisionDetails': 'Decision Details',
  'detail.sessionOverview': 'Session Overview',
  'detail.scene': 'Scene',
  'detail.difficulty': 'Difficulty',
  'detail.battleLevel': 'Battle Level',
  'detail.failures': 'Failures',
  'detail.time': 'Time',
  'detail.agent': 'Agent',
  'detail.cogState': 'Cognitive State',
  'detail.beast': 'Beast',
  'detail.mindset': 'Mindset',
  'detail.confidence': 'Confidence',
  'detail.battleInfo': 'Battle Info',
  'detail.strategy': 'Strategy',
  'detail.allusion': 'Allusion',
  'detail.tokens': 'Tokens',
  'detail.interaction': 'Interaction Log',
  'detail.userPrompt': 'User Prompt',
  'detail.reasoning': 'AI Reasoning',
  'detail.modelOutput': 'Model Output',
  'detail.dialogChain': 'Dialog Chain',
  'detail.rawPayload': 'Raw Payload',
  'detail.model': 'Model',
  'detail.provider': 'Provider',
  'detail.created': 'Created',
  'detail.agents': 'Agents',
  'detail.metrics': 'Metrics',
  'detail.noSummary': 'No summary',
  'detail.formation': 'Formation',

  // Metrics
  'metrics.tokens': 'Tokens',
  'metrics.complexity': 'Complexity',
  'metrics.deepExplore': 'Deep Explore',
  'metrics.loops': 'Loops',
  'metrics.quality': 'Quality',
  'metrics.maxBattle': 'Max Battle',
  'metrics.beast': 'Beast',

  // Status bar
  'status.session': 'Session',
  'status.loaded': 'loaded',
  'status.sessions': 'sessions',
  'status.connected': 'Connected',
  'status.disconnected': 'Disconnected',

  // Tree nav
  'tree.sessions': 'Sessions',
  'tree.noSessions': 'No sessions yet',
  'tree.noSummary': 'No summary',
  'tree.confirmDelete': 'Click again to confirm',
  'tree.delete': 'Delete session',

  // SKILL panel
  'skill.title': 'PI SKILL Knowledge',
  'skill.scenes': '9 Scenes',
  'skill.battleStages': '6 Battle Stages',
  'skill.beasts': '12 Spirit Animals',
  'skill.strategies': '5 Strategies',
  'skill.formations': 'Cognitive Formations',

  // Help guide
  'help.title': '⚡ PI Visualizer — User Guide',
  'help.tabNav': 'Navigation',
  'help.tabTimeline': 'Timeline',
  'help.tabExport': 'Import/Export',
  'help.tabSimulation': 'Simulation',
  'help.tabSearch': 'Search/Filter',
  'help.tabTips': 'Tips',
  'help.keyboard': '⌨️ Keyboard Shortcuts',
  'help.mouse': '🖱️ Mouse',
  'help.features': '✨ Features',
  'help.scroll': 'Scroll',
  'help.zoom': 'to zoom in/out',
  'help.clickNode': 'Click node',
  'help.viewDetails': 'to view details',
  'help.dragNode': 'Drag node',
  'help.reposition': 'to reposition',
  'help.dragCanvas': 'Drag canvas',
  'help.pan': 'to pan',
  'help.timelineDesc': 'Use the timeline controls in the top bar to replay the decision process. Press Space to play/pause, arrow keys to step.',
  'help.exportDesc': 'Export current session or all archives as JSON. Import JSON files to restore historical session data.',
  'help.simDesc': 'Use simulation mode to generate test data covering 9 scenes, 6 battle stages, 12 spirit animals from the SKILL system.',
  'help.searchDesc': 'Browse sessions grouped by date in the sidebar. Click to select a session and view its decision tree.',
  'help.tipsTitle': '💡 Tips & Tricks',
  'help.tip1': 'Click mindset badges to view cultural context and classic origins',
  'help.tip2': 'Hover over beast/strategy/allusion for detailed tooltips',
  'help.tip3': 'Use simulation mode to quickly generate test data for various scenarios',
  'help.tip4': 'Drag nodes to customize layout, click the grid button to reset',
  'help.tip5': 'During timeline playback, a floating card shows the current decision',

  // Cognitive formations
  'cog.architect': 'Architect',
  'cog.commander': 'Commander',
  'cog.explorer': 'Explorer',
  'cog.guardian': 'Guardian',
  'cog.harmonizer': 'Harmonizer',
  'cog.analyst': 'Analyst',
}

export type TranslationKey = keyof typeof zh

const translations: Record<Lang, Record<TranslationKey, string>> = { zh, en }

export function getTranslation(lang: Lang) {
  const strings = translations[lang]
  return (key: TranslationKey): string => strings[key] ?? key
}
