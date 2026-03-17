# PI 可视化工具完整集成分析报告

## 执行摘要

PI 可视化工具采用**分层集成架构**，通过以下关键机制实现跨平台无缝集成：

1. **决策数据采集层** — Hooks 机制在各平台捕获决策点
2. **命令路由层** — `/visualize` 和 `/pi visualize` 命令统一入口
3. **可视化工具层** — Node.js + Vite 前端 + Express 服务器
4. **部署与发布层** — 安装脚本 + 编译分发流程

---

## 1. 可视化工具架构

### 1.1 目录结构

```
visualize/
├── src/                           # React 前端源码
│   ├── App.tsx                   # 主应用
│   ├── components/               # React 组件库
│   ├── hooks/                    # 自定义 hooks
│   ├── store.ts                  # Zustand 状态管理
│   ├── types.ts                  # TypeScript 类型定义
│   ├── i18n.ts                   # 国际化
│   ├── lib/                      # 工具库
│   └── styles/                   # Tailwind CSS
│
├── server/                       # Node.js 服务器
│   ├── index.ts                  # Express + WebSocket 入口
│   ├── parser.ts                 # 决策文件解析
│   ├── watcher.ts                # 文件监听
│   └── mock-data.ts              # 模拟数据生成
│
├── package.json                  # npm 依赖
├── vite.config.ts                # Vite 构建配置
├── tailwind.config.ts            # Tailwind 配置
├── tsconfig.json                 # TypeScript 配置
├── SPEC.md                       # 技术规范
└── USER_GUIDE.md                 # 完整用户指南
```

### 1.2 技术栈

| 层 | 技术 | 版本 |
|----|------|------|
| 前端框架 | React + TypeScript | 19 + 5.7 |
| 构建工具 | Vite | 6.0 |
| 样式 | Tailwind CSS | 3.4 |
| 图表库 | React Flow | 12 |
| 状态管理 | Zustand | 5 |
| 后端框架 | Express | 4.21 |
| WebSocket | ws | 8.18 |
| 文件监听 | chokidar | 4.0 |

### 1.3 构建与启动命令

```bash
# 开发模式
npm run dev              # Vite dev server (port 5173) + Express proxy

# 生产构建
npm run build            # 构建到 dist/ 目录
npm run start            # 构建 + 启动生产服务器（port 3141）
npm run start:mock       # 构建 + 启动带模拟数据的服务器

# 服务器独立运行（前端已构建）
npm run server           # 生产模式服务器（读取 ~/.pi/decisions）
npm run server:mock      # 模拟数据服务器

# 类型检查
npm run typecheck        # TypeScript 检查
```

---

## 2. 各插件目录结构与命令注册方式

### 2.1 Copilot CLI

```
copilot-cli/
├── pi/
│   ├── SKILL.md                  # PI 原版（完整，不裁剪 Loop）
│   └── SKILL_LITE.md             # PI 白话版
├── pi-en/
│   ├── SKILL.md                  # PI 英文版（完整）
│   └── SKILL_LITE.md             # PI 英文白话版
├── pi-progressive/               # 渐进式版本
│   ├── SKILL.md
│   ├── SKILL_LITE.md
│   └── references/
│       ├── four-dojos.md
│       ├── battle-momentum.md
│       ├── resonance-forms.md
│       └── team-protocol.md
└── pi-en-progressive/            # 英文渐进式版本
    ├── SKILL.md
    ├── SKILL_LITE.md
    └── references/
```

**命令注册方式：**
- 类型：AgentSkills 标准格式
- Frontmatter：标准 AgentSkills 格式（name, description, license, metadata）
- 触发方式：由 Copilot CLI 自动加载 SKILL.md

### 2.2 Claude Code

```
claude-code/
├── pi/
│   ├── SKILL.md                  # PI 原版（PURGE-01 裁剪）
│   └── SKILL_LITE.md
├── pi-en/
│   ├── SKILL.md
│   └── SKILL_LITE.md
├── pi-progressive/               # 渐进式版本
│   ├── SKILL.md
│   ├── SKILL_LITE.md
│   └── references/
└── pi-en-progressive/
    ├── SKILL.md
    ├── SKILL_LITE.md
    └── references/
```

**命令注册方式：**
- 类型：AgentSkills 标准格式
- 触发方式：Claude Code 加载对应目录下的 SKILL.md

### 2.3 Cursor

```
cursor/
└── rules/
    ├── pi.mdc                    # PI 原版（Cursor MDC 格式，PURGE-01 裁剪）
    ├── pi-lite.mdc               # PI 白话版
    ├── pi-en.mdc                 # PI 英文版（PURGE-01 裁剪）
    ├── pi-en-lite.mdc            # PI 英文白话版
    └── pi-visualize.mdc          # 可视化工具使用说明
    └── _frontmatter              # Frontmatter 模板
```

**命令注册方式：**
- 类型：Cursor Rules (MDC 格式)
- Frontmatter：
  ```yaml
  description: "PI 智行合一。触发：编程/开发/..."
  alwaysApply: true
  ```
- 触发方式：`alwaysApply: true` 使规则始终激活

### 2.4 Kiro

```
kiro/
└── steering/
    ├── pi.md                     # PI 原版（Markdown，PURGE-01 裁剪）
    ├── pi-lite.md                # PI 白话版
    ├── pi-en.md                  # PI 英文版（PURGE-01 裁剪）
    ├── pi-en-lite.md             # PI 英文白话版
    └── _frontmatter              # Frontmatter 模板
```

**命令注册方式：**
- 类型：Kiro Steering 配置
- Frontmatter：
  ```yaml
  inclusion: auto
  name: pi
  description: "PI 智行合一。触发：..."
  ```
- 触发方式：`inclusion: auto` 自动包含

### 2.5 Qoder

```
qoder/
├── README.md                     # 集成说明
└── pi-qoder-adapter.sh           # 适配器脚本（执行捕获和决策记录）
```

**命令注册方式：**
- 类型：Bash 适配器脚本
- 注册方式：`pi-qoder-adapter.sh <command>` 包装任意命令
- 功能：
  1. 捕获命令执行上下文
  2. 记录执行结果和退出码
  3. 将决策数据写入 `~/.pi/decisions`
  4. 与 hooks 机制联动

**pi-qoder-adapter.sh 关键逻辑：**
```bash
# 1. 创建会话
if [ -z "$PI_SESSION_ID" ]; then
    export PI_SESSION_ID="qoder-$(date +%s)"
fi

# 2. 执行命令
"$@"
EXIT_CODE=$?

# 3. 构造决策 JSON
DECISION_JSON="{
  \"session_id\": $ESCAPED_SESSION_ID,
  \"label\": $ESCAPED_LABEL,
  \"category\": \"execution\",
  \"outcome\": $ESCAPED_OUTCOME,
  \"payload\": {\"command\": $ESCAPED_COMMAND, \"exit_code\": $EXIT_CODE}
}"

# 4. 调用通用捕获 hook
echo "$DECISION_JSON" | "$HOOKS_DIR/capture-generic.sh"
```

---

## 3. visualize 命令的注册方式

### 3.1 /visualize 命令（Cursor 专用）

**文件位置：** `/Users/hepin/IdeaProjects/pi/cursor/rules/pi-visualize.mdc`

**内容：**
```yaml
---
description: "PI Visualizer usage in Cursor (local offline + optional live preview)"
alwaysApply: true
---

# PI Visualizer in Cursor

To visualize your PI decision history locally:

## 1) Generate a standalone (offline) HTML
/pi visualize

## 2) Live local preview (opt-in)
cd visualize && mill cli.run --live
```

**工作流程：**
1. 用户在 Cursor 中输入 `/visualize` 或 `/pi visualize`
2. 规则通过 `alwaysApply: true` 被激活
3. 规则指导用户执行命令

### 3.2 /pi visualize 命令（全平台通用）

**文件位置：** `/Users/hepin/IdeaProjects/pi/commands/pi.md`

**关键部分：**
```markdown
## Special Route: `/pi visualize`

If the first argument is `visualize`, **do not** activate the generic PI scene router. 
Instead, treat the remaining arguments as visualizer CLI flags and execute:

1. 定位可视化工具
2. 构建前端（如果从源码运行）
3. 运行 CLI：
   - 离线 HTML：mill cli.run [args]
   - 实时预览：mill cli.run --live [args]
4. 转发额外标志
5. 报告执行结果
```

**文件位置：** `/Users/hepin/IdeaProjects/pi/commands/visualize.md`

**行为：**
1. **定位工具：**
   - 检查 `./visualize/build.mill`（当前工作区）
   - 检查 `~/.pi/visualize.sh`（已安装的独立版本）
   - 检查 `~/.pi/visualize/visualize`（Mill 项目目录）
   - 检查 `~/.pi/visualize` + `build.mill`
   - 失败时建议运行：`curl -fsSL https://raw.githubusercontent.com/share-skills/pi/main/scripts/setup-standalone-visualize.sh | bash`

2. **构建前端（如果从源码）：**
   ```bash
   cd [detected-visualize-dir] && mill frontend.standaloneHtml
   ```

3. **运行 CLI：**
   ```bash
   # 离线 HTML（默认）
   cd [detected-visualize-dir] && mill cli.run [args]
   
   # 实时预览
   cd [detected-visualize-dir] && mill cli.run --live [args]
   ```

4. **默认行为：**
   - 源：`~/.pi/decisions`
   - 模板：`visualize/out/frontend/standaloneHtml.dest/index.html`
   - 输出：`visualize/out/cli/pi-visualize.html`
   - 浏览器：自动打开（可用 `--no-open` 禁用）

---

## 4. 各插件启动可视化的触发点

### 4.1 数据采集 Hook 机制

**文件位置：** `/Users/hepin/IdeaProjects/pi/hooks/hooks.json`

**Hook 触发点：**

| Hook | 触发条件 | 命令 | 用途 |
|------|---------|------|------|
| UserPromptSubmit | 用户提交 prompt | capture-prompt.sh | 记录用户输入 |
| PreCompact | 内容压缩前 | pre-compact.sh | 记录上下文 |
| Stop | AI 完成输出 | capture-decision.sh | 记录最终决策 |
| PostToolUse (Bash) | 工具执行成功 | capture-tool-result.sh success | 记录工具结果 |
| PostToolUseFailure (Bash) | 工具执行失败 | capture-tool-result.sh failure | 记录失败信息 |
| SubagentStart | 子代理启动 | capture-subagent.sh start | 记录子代理启动 |
| SubagentStop | 子代理结束 | capture-subagent.sh stop | 记录子代理结束 |

**数据流：**
```
[Claude Code / Cursor] 
    ↓ (Hook 触发)
[capture-*.sh] 
    ↓ (构造决策 JSON)
[~/.pi/decisions/] 
    ↓ (累积决策数据)
[/pi visualize] 
    ↓ (加载数据)
[Visualizer] (渲染决策树)
```

### 4.2 Qoder 特化集成

**文件位置：** `/Users/hepin/IdeaProjects/pi/qoder/pi-qoder-adapter.sh`

**集成方式：**
```bash
# 用户使用 Qoder 执行命令时
qoder pi-qoder-adapter.sh <command>

# 例如
qoder pi-qoder-adapter.sh npm run build

# 适配器会：
# 1. 捕获命令执行上下文
# 2. 记录执行结果
# 3. 构造决策 JSON
# 4. 调用 capture-generic.sh 保存到 ~/.pi/decisions
```

---

## 5. 如何实现"开箱即用"（无需额外依赖）

### 5.1 关键问题

原文档指定了基于 **Mill** 的构建（Scala build system），但实际项目采用 **Node.js + Vite + npm**。这导致以下问题：

- ❌ 文档期望：`mill cli.run` 和 `mill frontend.standaloneHtml`
- ✅ 实际项目：`npm run build` 和 `npm run start`

### 5.2 当前方案的问题

| 问题 | 影响 |
|-----|------|
| 需要 Node.js/npm | 用户需要自行安装 Node 环境 |
| 需要 git | 执行 setup-standalone-visualize.sh 时需要 clone 仓库 |
| 需要 Mill | 文档中要求 mill，但项目实际不用 |
| 首次运行延迟 | ~/.pi/visualize.sh 首次运行需要 clone + npm install + build |

### 5.3 "开箱即用"的实现方案（需要修改）

#### **方案 A：预编译的可执行文件（推荐）**

```
~/.pi/
├── visualize.sh                  # 轻量启动器
├── visualize-dist/               # 预编译前端
│   ├── index.html
│   ├── assets/
│   └── manifest.json
└── visualizer-cli                # 预编译 Node CLI（Go 或其他二进制）
```

**启动流程：**
```bash
~/.pi/visualize.sh
    ↓
检查 visualizer-cli 是否存在
    ↓
直接运行：./visualizer-cli --source ~/.pi/decisions
    ↓
启动 http://127.0.0.1:3141，自动打开浏览器
```

**优点：**
- ✅ 无需 Node.js/npm/git/mill
- ✅ 瞬间启动
- ✅ 真正的"开箱即用"

#### **方案 B：静态 HTML + 本地 API（备选）**

```
~/.pi/visualize.html              # 完全独立的 HTML 文件（含数据）
```

**生成方式：**
```bash
npm run build:standalone
    ↓
生成 standalone.html（嵌入 ~/.pi/decisions 内容）
```

**启动方式：**
```bash
~/.pi/visualize.sh
    ↓ (检查 standalone.html 是否存在)
    ↓ (存在则)
    ↓
open ~/.pi/visualize.html
    ↓
纯前端渲染，无需任何服务器/依赖
```

**优点：**
- ✅ 无依赖
- ✅ 离线工作
- ✅ 可以通过文件分享
- ❌ 需要在生成时嵌入数据（不支持实时更新）

#### **方案 C：轻量 Deno/Bun CLI（折中）**

```
~/.pi/visualizer-cli               # Deno 或 Bun 二进制
```

- Deno：原生 TypeScript，单文件部署
- Bun：极速 JS 运行时，更小的二进制
- 仍比 Node.js 要轻

---

## 6. npm run start:mock 和 npm run dev 的生产替代方案

### 6.1 当前情况

**开发环境：**
```bash
npm run dev
    ↓
启动 Vite dev server (port 5173)
启动 Express server (port 3141) 
Vite 代理 /api 和 /ws 到 3141
支持 HMR（Hot Module Reload）
```

**生产环境：**
```bash
npm run build         # 构建到 dist/
npm run start         # dist/ + 启动 Express (port 3141)
npm run start:mock    # dist/ + 启动 Express (--mock 标志)
```

### 6.2 生产部署的关键问题

| 问题 | 说明 |
|------|------|
| Node.js 依赖 | 线上必须安装 Node.js 和 npm 依赖 |
| 启动延迟 | npm install + npm run build 需要时间 |
| 版本管理 | 不同环境的 Node 版本可能不同 |
| 容器化 | Docker/K8s 需要完整的 Node 镜像 |

### 6.3 推荐的生产方案

#### **方案 1：预编译 + 轻量运行时（推荐）**

```bash
# 构建时（CI/CD）
npm run build
npm run build:standalone          # 生成完全独立的 HTML

# 打包到发布物
dist/                             # 前端资源
server-cli                        # 预编译的 Express CLI（Go/Rust/Deno）
                                 # 或 Node.js bundle (pkg/esbuild)
.pi/visualize.sh                 # 启动脚本
```

**运行时（用户端）：**
```bash
~/.pi/visualize.sh
    ↓
执行预编译的 server-cli（无需 Node.js）
    ↓
读取 ~/.pi/decisions
    ↓
启动 HTTP 服务器 + 前端
```

#### **方案 2：Node.js Bundle（使用 pkg 或 esbuild）**

```bash
# 打包
npm run build:bundle
    ↓
    pkg dist/server.cjs --targets node18-linux-x64,node18-macos-arm64
    ↓
    输出：visualizer-cli-linux-x64，visualizer-cli-macos-arm64
```

#### **方案 3：Docker 容器**

```dockerfile
# Dockerfile
FROM node:18-alpine
WORKDIR /app
COPY dist/ /app/dist
COPY server/ /app/server
COPY package.json /app/
RUN npm ci --only=production
EXPOSE 3141
CMD ["npm", "run", "server"]
```

---

## 7. 完整集成流程图

```
┌─────────────────────────────────────────────────────────────┐
│                     安装 / 首次启动                           │
├─────────────────────────────────────────────────────────────┤
│  curl -fsSL https://raw.github.../setup-standalone-visualize.sh
│      ↓
│  创建 ~/.pi/setup-standalone-visualize.sh（保存本地副本）
│      ↓
│  检查 git/mill 依赖
│      ↓
│  git clone https://github.com/share-skills/pi.git ~/.pi/visualize
│      ↓
│  cd ~/.pi/visualize/visualize && mill frontend.standaloneHtml
│      ↓
│  创建 ~/.pi/visualize.sh 启动器
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│                   持续使用 / 启动可视化                        │
├─────────────────────────────────────────────────────────────┤
│  ~/.pi/visualize.sh
│      ↓
│  检查 ~/.pi/visualize/visualize/build.mill 是否存在
│      ↓ (不存在时)
│  运行 bash ~/.pi/setup-standalone-visualize.sh (重新初始化)
│      ↓ (存在时)
│  cd ~/.pi/visualize/visualize
│      ↓
│  mill frontend.standaloneHtml (确保前端最新)
│      ↓
│  mill cli.run --source ~/.pi/decisions
│      ↓
│  启动 Express 服务器 (port 3141) + 自动打开浏览器
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│               决策数据采集 / 各插件联动                        │
├─────────────────────────────────────────────────────────────┤
│  Claude Code / Cursor
│      ↓ (Hook 触发)
│  hooks/capture-decision.sh
│      ↓
│  写入 ~/.pi/decisions/YYYY-MM-DD/session-*.json
│      ↓
│  浏览器刷新时加载
│      ↓
│  Visualizer 展示最新决策树
└─────────────────────────────────────────────────────────────┘
```

---

## 8. PI SKILL 分发与可视化配套

### 8.1 发布流程中的可视化配套物

**DISTRIBUTE.md 规定的可视化发布流程：**

```yaml
Phase 3: 分发（P3）

步骤 3.6b  可视化发布配套物：
  - 确认 install.sh 会放置 ~/.pi/visualize.sh 启动器
  - 确认 scripts/setup-standalone-visualize.sh 可独立工作
  - 确认 cursor/rules/pi-visualize.mdc 随安装链路分发
  - 确认 README.md / commands/visualize.md 中的说明与实现一致
```

### 8.2 具体的分发细节

| 物件 | 位置 | 用途 | 分发方式 |
|------|------|------|---------|
| visualize.sh | ~/.pi/visualize.sh | CLI 启动器 | install.sh 复制 |
| setup-standalone-visualize.sh | ~/.pi/setup-standalone-visualize.sh | 首次初始化 | curl 下载或 install.sh 复制 |
| pi-visualize.mdc | ~/.cursor/rules/pi-visualize.mdc | Cursor 规则 | install.sh 复制 |
| commands/visualize.md | 内置文档 | 命令说明 | 仓库内 |

---

## 9. 当前状态 vs. 预期状态

### 9.1 当前状态（实际代码）

| 方面 | 状态 |
|------|------|
| 前端技术 | React 19 + Vite 6 + Tailwind ✅ |
| 后端技术 | Express 4 + Node.js ✅ |
| 数据采集 | Hooks 机制（Claude Code/Cursor） ✅ |
| 命令路由 | /pi visualize + /visualize ✅ |
| 安装脚本 | setup-standalone-visualize.sh ⚠️ (期望 mill，实际 npm) |
| 可视化规则 | cursor/rules/pi-visualize.mdc ✅ |
| 文档 | commands/visualize.md ⚠️ (频繁提及 mill) |

### 9.2 预期状态（文档）

| 方面 | 期望 |
|------|------|
| 构建系统 | Mill (Scala 构建工具) |
| CLI 命令 | `mill frontend.standaloneHtml` |
| CLI 命令 | `mill cli.run [--live] [--source ...]` |
| 独立部署 | ~/.pi/visualize (Mill 项目) |

### 9.3 差异原因

文档中多次提及 **Mill** 但代码实际使用 **npm/Vite**，原因：
- 可能是文档编写时的规划
- 或代码实现中途改为 npm/Vite（更轻量、更快)
- 需要更新所有文档以保持一致

---

## 10. 关键缺陷与改进建议

### 10.1 缺陷清单

| 级别 | 缺陷 | 影响 | 修复 |
|------|------|------|------|
| 🔴 High | setup-standalone-visualize.sh 期望 build.mill，但代码无此文件 | 用户首次运行会失败 | 更改脚本检查 package.json 或预编译 dist/ |
| 🔴 High | 文档频繁提及 mill，但项目实际用 npm | 文档误导 | 全量更新 commands/*.md 和 scripts/*.sh |
| 🟡 Medium | npm run start:mock 需要 Node.js，违反"开箱即用" | 新用户体验差 | 预编译 Node 二进制或生成静态 HTML |
| 🟡 Medium | 没有 ~/.pi/visualize.sh 时，命令路由会失败 | 首次使用体验差 | install.sh 需要自动创建或提示创建 |
| 🟢 Low | install.sh 安装流程与 visualize 启动流程分离 | 逻辑复杂性高 | 考虑合并为统一的初始化流程 |

### 10.2 改进建议

**短期（修复文档与脚本匹配）：**
1. 更新 setup-standalone-visualize.sh 检查逻辑（package.json 而非 build.mill）
2. 全量更新 commands/visualize.md 移除 mill 引用
3. 更新 install.sh 中的 visualizer 启动脚本生成逻辑

**中期（实现真正的"开箱即用"）：**
1. 预编译 Node CLI 为跨平台二进制（Go/Rust 重写或 pkg 打包）
2. 预构建 dist/ 并在 ~/.pi 中保留副本
3. 移除运行时的 npm install / npm run build 步骤

**长期（优化部署方案）：**
1. 考虑 Deno/Bun 作为轻量运行时
2. 支持 Docker / 容器部署
3. 为不同平台提供预构建的可执行文件（.exe for Windows, .app for macOS 等）

---

## 11. PI SKILL 的分发与可视化的关系

### 11.1 PUBLISH.md 中的可视化条款

```yaml
Phase 3: 分发（P3）

步骤 3.6b  同步可视化发布配套物：
  - 确认 install.sh 会放置 ~/.pi/visualize.sh 启动器
  - 确认 scripts/setup-standalone-visualize.sh 可独立工作，且与公开仓库 URL 一致
  - 确认 cursor/rules/pi-visualize.mdc 随安装链路一起分发
  - 确认 README.md / README.en.md / commands/visualize.md 中的 visualizer 安装说明与当前实现一致

步骤 3.12  可视化发布链路校验：
  - install.sh 中存在 visualizer launcher 安装步骤
  - scripts/setup-standalone-visualize.sh 的 raw URL / repo URL 与公开安装仓库一致
  - Cursor 安装路径包含 pi-visualize.mdc
  - 文档不再把 visualizer 说成"用户必须手动 clone 才能使用"
```

### 11.2 具体关系

```
SKILL_META.md (迭代真源)
    ↓ (P2 编译)
SKILL.md (精简版) + SKILL_LITE.md (白话版)
    ↓ (P3 分发 + 可视化配套)
    ├─ skills/pi/SKILL.md (原版，PURGE-01 裁剪)
    ├─ claude-code/pi/SKILL.md
    ├─ cursor/rules/pi.mdc
    ├─ kiro/steering/pi.md
    ├─ openclaw/pi/SKILL.md
    ├─ copilot-cli/pi/SKILL.md (完整，不裁剪)
    │
    └─ [同时] 更新可视化配套：
        ├─ install.sh (visualize launcher 安装)
        ├─ cursor/rules/pi-visualize.mdc
        ├─ commands/visualize.md
        └─ README.md/README.en.md (visualizer 安装说明)
```

---

## 总结

PI 的可视化工具通过以下机制实现完整集成：

1. **多平台支持** — 通过 SKILL 分发到 Claude Code/Cursor/Kiro/Copilot CLI/Qoder，每个平台独立触发可视化

2. **数据采集** — Hooks 在关键点（UserPromptSubmit, Stop, PostToolUse 等）捕获决策数据

3. **命令路由** — `/visualize` (Cursor) 和 `/pi visualize` (全平台) 统一入口

4. **核心依赖**：
   - Node.js + npm (用于构建和运行)
   - 可选：git (用于首次初始化)
   - 可选：mill (文档期望，但实际代码不需要)

5. **主要问题** — 文档与代码不匹配（期望 mill，实际 npm），需要修复

6. **开箱即用方案** — 需要预编译二进制或生成静态 HTML，当前方案仍需 Node.js

