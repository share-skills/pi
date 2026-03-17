# PI Decision Visualizer — 用户指南 / User Guide

> 🧠 将 AI 协作的隐性决策变为可见的决策树 / Making invisible AI decisions visible

---

## 目录 / Table of Contents

1. [概述 / Overview](#1-概述--overview)
2. [快速开始 / Quick Start](#2-快速开始--quick-start)
3. [与 IDE 集成 / IDE Integration](#3-与-ide-集成--ide-integration)
4. [PI SKILL 配合使用 / Working with PI SKILL](#4-pi-skill-配合使用--working-with-pi-skill)
5. [界面操作指南 / UI Walkthrough](#5-界面操作指南--ui-walkthrough)
6. [决策数据解读 / Reading Decision Data](#6-决策数据解读--reading-decision-data)
7. [导出与分享 / Export & Share](#7-导出与分享--export--share)
8. [模拟模式 / Simulation Mode](#8-模拟模式--simulation-mode)
9. [主题与语言 / Theme & Language](#9-主题与语言--theme--language)
10. [故障排除 / Troubleshooting](#10-故障排除--troubleshooting)
11. [高级用法 / Advanced Usage](#11-高级用法--advanced-usage)

---

## 1. 概述 / Overview

### 什么是 PI Decision Visualizer？

PI Decision Visualizer 是 PI（智行合一）方法论的可视化工具。它将 AI 协作过程中的每一个决策点——选择什么策略、激活什么心态、处于什么战势阶段——渲染为可交互的决策树。

**核心能力：**
- 📊 **决策树画布** — 以节点-边的形式呈现决策路径
- 🕐 **时间线回放** — 拖动时间轴，逐步回放决策过程
- 🎭 **认知状态** — 查看每个节点的灵兽、战术、心态
- 📋 **详情抽屉** — 深入查看节点的完整上下文
- 🔄 **实时同步** — 与 PI SKILL 实时联动

### What is PI Decision Visualizer?

PI Decision Visualizer is the visualization tool for the PI (智行合一) methodology. It renders every decision point during AI collaboration — strategy choices, mindset activations, battle stage escalations — as an interactive decision tree.

**Core capabilities:**
- 📊 **Decision Tree Canvas** — Visualize decision paths as nodes and edges
- 🕐 **Timeline Playback** — Scrub through decisions chronologically
- 🎭 **Cognitive State** — View beast, strategy, mindset per node
- 📋 **Detail Drawer** — Deep-dive into full node context
- 🔄 **Live Sync** — Real-time integration with PI SKILL

---

## 2. 快速开始 / Quick Start

### 安装 / Installation

```bash
# 克隆仓库（如果尚未）
git clone https://github.com/anthropic-lab/pi.git
cd pi/visualize

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

浏览器将自动打开 `http://localhost:5173`。

### 构建生产版本 / Production Build

```bash
npm run build    # 构建到 out/ 目录
npm run preview  # 预览生产版本
```

### 第一次使用 / First Time Use

1. **启动 Visualizer** — 运行 `npm run dev`
2. **加载数据** — 点击侧边栏的 📁 按钮，导入 `.pi-decisions.json` 文件
3. **选择会话** — 在左侧边栏选择一个 session
4. **探索决策树** — 在画布上拖拽、缩放，点击节点查看详情
5. **时间线回放** — 拖动底部时间轴，观察决策过程

---

## 3. 与 IDE 集成 / IDE Integration

PI Decision Visualizer 可以与多种 AI IDE 工具配合使用：

### Claude Code

```bash
# 在 Claude Code 项目中使用 PI SKILL
# PI 会自动生成 .pi-decisions.json
# 在 Visualizer 中加载该文件查看决策树
```

Claude Code 中的 PI SKILL 会在每次交互时记录决策元数据。Visualizer 读取这些数据并渲染为决策树。

### Copilot CLI

在 `copilot-cli/` 目录中配置 PI SKILL，Copilot CLI 会在 `hooks/` 中触发决策记录。每次会话结束后，决策数据会写入 `.pi-decisions.json`。

### Cursor

Cursor 通过 `.cursor/rules/` 目录加载 PI SKILL。决策数据在 Cursor 的 Agent 模式下自动收集，可通过 Visualizer 查看。

### Kiro

Kiro 通过 `kiro/` 目录中的配置集成 PI。Kiro 的 spec-driven 流程天然适合 PI 的决策记录模式。

### Qoder

Qoder 使用 `qoder/` 目录下的配置，PI SKILL 在 Qoder 的多 Agent 流程中记录每个 Agent 的决策点。

**通用流程 / Universal Workflow：**
1. 在对应 IDE 中配置 PI SKILL（参见各 IDE 目录下的文档）
2. 正常使用 AI 进行编程/调试/创作
3. PI SKILL 自动记录决策数据
4. 打开 Visualizer，导入决策数据
5. 分析决策路径，优化协作策略

---

## 4. PI SKILL 配合使用 / Working with PI SKILL

### 数据流 / Data Flow

```
AI IDE (Claude/Copilot/Cursor/Kiro/Qoder)
    ↓  PI SKILL 记录每个决策点
.pi-decisions.json
    ↓  导入到 Visualizer
Decision Tree Canvas
    ↓  分析与回放
优化下一次协作
```

### 决策数据结构 / Decision Data Structure

PI SKILL 生成的每个决策节点包含：

```json
{
  "id": "unique-id",
  "timestamp": "2024-01-15T10:30:00Z",
  "decision_point": "选择调试策略",
  "category": "execution",
  "difficulty": "medium",
  "payload": {
    "beast": "🐉 龙",
    "strategy": "以正合",
    "mindset": "analyst",
    "confidence": "high",
    "allusion": "孙子兵法",
    "battle_stage": 2,
    "user_prompt": "这个函数有 bug...",
    "model_output": "让我分析这个问题..."
  }
}
```

### 触发场景 / Trigger Scenes

| 场景 Scene | 触发词 Keywords | 说明 Description |
|---|---|---|
| 💻 编程开发 | exec, tool, code | 执行代码、使用工具 |
| 🔧 调试排错 | debug, fix, error | 排查和修复问题 |
| 🎨 创意发散 | ideate, brainstorm | 创意思维和头脑风暴 |
| 📊 产品分析 | analyze, strategy | 产品和策略分析 |
| 🧪 测试验证 | test, verify, QA | 测试和质量保证 |
| 🚀 部署发布 | deploy, release | 部署和发布流程 |
| 🤝 协作沟通 | team, communicate | 团队协作与沟通 |
| 🔬 技术调研 | research, explore | 技术研究和探索 |
| 📝 代码审查 | review, PR | 代码审查和 PR |

---

## 5. 界面操作指南 / UI Walkthrough

### 整体布局 / Overall Layout

```
┌─────────────────────────────────────────────────┐
│  TopBar（顶栏）                                   │
├────────┬────────────────────────────┬────────────┤
│        │                            │            │
│ Side-  │    Decision Canvas         │  Detail    │
│ bar    │    （决策画布）               │  Drawer   │
│（侧边栏）│                            │ （详情栏） │
│        │                            │            │
├────────┴────────────────────────────┴────────────┤
│  Timeline（时间线）                                │
└─────────────────────────────────────────────────┘
```

### 侧边栏 / Sidebar

- **会话列表** — 显示所有已加载的 AI 协作会话
- **搜索过滤** — 按关键词搜索会话
- **导入按钮** — 点击 📁 导入 `.pi-decisions.json`
- **快捷键** — 按 `[` 切换侧边栏显示

### 决策画布 / Decision Canvas

画布是核心视图，显示决策树：

- **拖拽** — 按住鼠标拖拽画布
- **缩放** — 滚轮或触控板缩放
- **点击节点** — 选中节点，打开详情抽屉
- **自动布局** — 点击右上角 ⊞ 按钮重置布局
- **帮助** — 点击右上角 ? 按钮查看快捷键

**节点颜色含义 / Node Colors：**
- 🟣 **紫色** — 策略/分析类决策
- 🟢 **绿色** — 执行/成功类决策
- 🟡 **黄色** — 警告/中等信心决策
- 🔴 **红色** — 高风险/低信心决策
- 🔵 **蓝色** — 探索/调研类决策

### 详情抽屉 / Detail Drawer

点击节点后，右侧打开详情抽屉：

- **决策点** — 当前决策的描述
- **认知状态** — 灵兽、心态、信心等级
- **战势信息** — 战术策略、经典引用
- **Prompt/Output** — 原始的用户输入和 AI 输出
- **Token 使用** — 输入/输出 token 消耗

### 时间线 / Timeline

底部时间线控制器：

- **拖动滑块** — 逐步展示决策过程
- **从左到右** — 按时间顺序展示节点
- **播放回放** — 自动播放决策流程

### 快捷键 / Keyboard Shortcuts

| 快捷键 | 功能 |
|---|---|
| `[` | 切换侧边栏 |
| `]` | 切换详情抽屉 |
| `↑` `↓` | 切换选中的会话 |
| `Esc` | 关闭弹窗/面板 |
| `?` | 打开帮助 |

---

## 6. 决策数据解读 / Reading Decision Data

### 灵兽 / Spirit Beasts (🐉)

每个灵兽代表一种认知检测能力：

| 灵兽 | 含义 | 检测能力 |
|---|---|---|
| 🐉 龙 | 全局洞察 | 完美解法、系统级问题 |
| 🐅 虎 | 执行力 | 实施质量、效率问题 |
| 🐍 蛇 | 细节洞察 | 隐藏 bug、边界情况 |
| 🦅 鹰 | 远见 | 架构问题、长期影响 |
| 🐢 龟 | 稳健 | 风险控制、稳定性 |
| 🦊 狐 | 灵活 | 创造性方案、变通 |

### 心态 / Mindset (🎭)

六种认知原型：

- **Analyst（分析者）** — 深度分析，数据驱动
- **Architect（架构师）** — 系统设计，全局思考
- **Executor（执行者）** — 快速实施，结果导向
- **Guardian（守护者）** — 风险防控，质量保证
- **Explorer（探索者）** — 创新探索，发散思维
- **Integrator（整合者）** — 综合协调，融合视角

### 战术策略 / Strategy (⚔️)

- **以正合** — 正面对敌，稳扎稳打
- **以奇胜** — 侧翼突破，出奇制胜
- **致人不致于人** — 掌控主动权
- **穷理尽性** — 穷究事物之理
- **搜读验交付** — 四步工作法

### 战势阶段 / Battle Stages (🏔️)

| 阶段 Level | 名称 | 英文 | 行为模式 |
|---|---|---|---|
| L1 | 易辙 | Switch Track | 灵活切换，快速尝试 |
| L2 | 深搜 | Deep Search | 深入搜索，广泛阅读 |
| L3 | 系统 | Systematic | 系统分析，全局思考 |
| L4 | 决死 | Last Stand | 绝境反击，破釜沉舟 |
| L5 | 截道 | Intercept | 截取一线生机 |
| L6 | 天行 | Heaven's Way | 天行健，自强不息 |

### 信心等级 / Confidence (📊)

- 🟢 **High** — 高信心，方案明确
- 🟡 **Medium** — 中等信心，需要验证
- 🔴 **Low** — 低信心，风险较大

---

## 7. 导出与分享 / Export & Share

### 导入数据 / Import

1. 点击侧边栏的 📁 按钮
2. 选择 `.pi-decisions.json` 文件
3. 数据自动加载到画布

支持的文件格式：
- `.pi-decisions.json` — PI 标准格式
- 可从任何支持 PI SKILL 的 IDE 中导出

### 导出数据 / Export

在顶栏中使用导出功能：
- **JSON** — 导出完整的决策数据
- **截图** — 导出画布截图（PNG）

### 分享 / Sharing

将 `.pi-decisions.json` 文件分享给团队成员，他们可以在自己的 Visualizer 中打开查看。

---

## 8. 模拟模式 / Simulation Mode

### 什么是模拟模式？

模拟模式生成随机决策数据，让你无需真实 AI 交互即可探索 Visualizer 的功能。

### 如何使用 / How to Use

1. 启动 Visualizer
2. 在没有加载任何数据的情况下，系统会提供模拟数据选项
3. 点击「加载模拟数据」按钮
4. 画布将显示模拟的决策树

模拟数据包含各种场景的决策节点，覆盖不同的：
- 灵兽和战术组合
- 战势阶段升级
- 信心等级变化
- 认知原型切换

---

## 9. 主题与语言 / Theme & Language

### 主题切换 / Theme

Visualizer 支持两种主题：

- 🌙 **暗色主题 (Dark)** — 默认主题，适合长时间使用
- ☀️ **亮色主题 (Light)** — 温暖的奶油色调，柔和不刺眼

在顶栏中点击主题切换按钮即可切换。

### 语言切换 / Language

支持中文和英文：

- 🇨🇳 **中文** — 默认语言，包含所有 PI 术语
- 🇺🇸 **English** — 完整英文界面

在顶栏中点击语言切换按钮切换。

---

## 10. 故障排除 / Troubleshooting

### 常见问题 / Common Issues

#### 画布空白 / Canvas is blank
- 确认已选择左侧会话
- 确认 `.pi-decisions.json` 文件格式正确
- 检查浏览器控制台是否有错误

#### 节点重叠 / Nodes overlap
- 点击右上角 ⊞ 按钮重置自动布局
- 手动拖拽节点调整位置

#### 侧边栏/详情栏消失 / Sidebar/Drawer disappeared
- 按 `[` 切换侧边栏
- 按 `]` 切换详情抽屉

#### 数据加载失败 / Data loading failed
- 确认 JSON 文件格式正确
- 确认文件包含 `sessions` 数组和 `nodes` 字段
- 文件编码应为 UTF-8

#### SKILL 面板打不开 / SKILL panel not opening
- 点击顶栏的 SKILL 按钮
- 按 `Esc` 关闭后重新打开
- 检查是否有其他弹窗遮挡

#### 时间线不响应 / Timeline not responding
- 确认当前会话有多个时间戳不同的节点
- 刷新页面重试

### 性能优化 / Performance Tips

- 大型决策树（100+ 节点）可能需要几秒加载
- 关闭 MiniMap（节点数 < 10 时自动隐藏）可提升性能
- 使用 Chrome/Edge 获得最佳性能

---

## 11. 高级用法 / Advanced Usage

### Git 同步 / Git Sync

将 `.pi-decisions.json` 纳入 git 版本控制：

```bash
# 在 .gitignore 中不要忽略 PI 决策文件
# 每次提交时包含决策数据
git add .pi-decisions.json
git commit -m "feat: add PI decision data for sprint 12"
```

这样团队可以通过 git 历史回溯决策演变。

### 实时预览 / Live Preview

开发模式下，Visualizer 支持 Hot Module Replacement：

```bash
npm run dev
# 修改代码后浏览器自动刷新
# 决策数据变化时自动重新渲染
```

### 对比模式 / Comparison Mode

将两个不同会话的决策树进行对比：

1. 加载包含多个会话的 JSON 文件
2. 在侧边栏中切换不同会话
3. 对比两棵决策树的差异——路径长度、战势升级、信心变化

### 自定义节点样式 / Custom Node Styles

决策节点的颜色和样式通过 `CATEGORY_STYLES` 配置：

```typescript
const CATEGORY_STYLES = {
  strategy: { color: '#8b5cf6' },    // 紫色
  execution: { color: '#22c55e' },   // 绿色
  analysis: { color: '#3b82f6' },    // 蓝色
  risk: { color: '#ef4444' },        // 红色
}
```

### 与 CI/CD 集成 / CI/CD Integration

在 CI/CD 流程中自动收集 PI 决策数据：

```yaml
# GitHub Actions 示例
- name: Run PI Decision Analysis
  run: |
    cat .pi-decisions.json | jq '.sessions | length'
    # 统计决策节点数
    cat .pi-decisions.json | jq '[.sessions[].nodes[]] | length'
```

---

## 📚 更多资源 / More Resources

- [PI 项目主页](../README.md)
- [SKILL 文档](../SKILL.md)
- [编译器文档](../COMPILER.md)
- [变更日志](../CHANGE_LOG.md)

---

*PI — 智行合一 / Think & Act as One*
