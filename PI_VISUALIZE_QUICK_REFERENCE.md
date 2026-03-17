# PI 可视化工具集成 — 快速参考表

## 核心三层架构

| 层级 | 组件 | 技术 | 职责 |
|------|------|------|------|
| **数据采集** | Hooks (CLI 触发) | Bash | 在 Claude Code/Cursor 中捕获决策点 |
| **可视化工具** | Visualizer | React 19 + Vite 6 + Express 4 | 交互式决策树渲染 + 实时预览 |
| **命令路由** | /visualize 和 /pi visualize | Markdown 命令定义 | 统一入口，定位工具，启动可视化 |

---

## 各插件集成概览

| 插件 | 目录 | 集成方式 | 数据流 |
|------|------|---------|--------|
| **Copilot CLI** | copilot-cli/pi/ | AgentSkills 格式，完整不裁剪 | SKILL.md → Hook 触发 → ~/.pi/decisions |
| **Claude Code** | claude-code/pi/ | AgentSkills 格式，PURGE-01 裁剪 | SKILL.md → Hook 触发 → ~/.pi/decisions |
| **Cursor** | cursor/rules/*.mdc | Cursor Rules，alwaysApply: true | pi.mdc + pi-visualize.mdc → Hook 触发 → /visualize |
| **Kiro** | kiro/steering/*.md | Kiro Steering，inclusion: auto | pi.md → Hook 触发 → ~/.pi/decisions |
| **Qoder** | qoder/pi-qoder-adapter.sh | Bash 适配器脚本 | pi-qoder-adapter.sh <cmd> → Hook 触发 → ~/.pi/decisions |

---

## 可视化启动流程

```
用户操作
  ↓
/visualize (Cursor) 或 /pi visualize (全平台)
  ↓
命令处理器检查工具位置：
  ✓ ./visualize/package.json (本地)
  ✓ ~/.pi/visualize.sh (已安装)
  ✓ ~/.pi/visualize/visualize/package.json (npm 项目)
  ✗ 都不存在 → 提示运行 setup-standalone-visualize.sh
  ↓
[如果从源码] npm install && npm run build
  ↓
npm run server (port 3141)
  ↓
Express 服务器启动 (port 3141)
  ↓
浏览器自动打开 http://127.0.0.1:3141
  ↓
Visualizer 加载并渲染决策树
```

---

## 决策数据采集 Hook 清单

| Hook 名 | 触发条件 | 脚本 | 记录内容 |
|--------|---------|------|---------|
| UserPromptSubmit | 用户提交 prompt | capture-prompt.sh | 用户输入、时间戳 |
| PreCompact | 内容压缩前 | pre-compact.sh | 上下文信息 |
| **Stop** | AI 完成输出 | **capture-decision.sh** | **决策选择、战势、认知状态** |
| PostToolUse (Bash) | 工具成功 | capture-tool-result.sh success | 执行结果、输出 |
| PostToolUseFailure (Bash) | 工具失败 | capture-tool-result.sh failure | 错误信息、exit code |
| SubagentStart | 子代理启动 | capture-subagent.sh start | 代理 ID、参数 |
| SubagentStop | 子代理结束 | capture-subagent.sh stop | 执行结果 |

**数据存储位置：** `~/.pi/decisions/YYYY-MM-DD/session-*.json`

---

## 安装与启动脚本

### install.sh 的责任

1. 检测已安装的 AI IDE 工具（Claude Code/Cursor/Kiro/Qoder/Copilot CLI/etc）
2. 安装 PI SKILL 文件到各工具的配置目录
3. **安装 visualizer launcher：**
   - 复制 `scripts/setup-standalone-visualize.sh` → `~/.pi/setup-standalone-visualize.sh`
   - 创建启动脚本 `~/.pi/visualize.sh`
4. 安装 Cursor 规则文件（包括 `pi-visualize.mdc`）

### setup-standalone-visualize.sh 的责任

1. 检查 `git` 和 `node`/`npm` 依赖
2. Clone PI 仓库 → `~/.pi/visualize/`
3. 安装依赖并构建前端：`npm install && npm run build`
4. 保存本地副本：`~/.pi/setup-standalone-visualize.sh`
5. 创建启动器：`~/.pi/visualize.sh`

### ~/.pi/visualize.sh 的责任

1. 检查 `~/.pi/visualize/visualize/package.json` 是否存在
2. 不存在时，重新运行 setup-standalone-visualize.sh
3. 安装依赖（如需要）：`npm install`
4. 启动服务：`npm run server`
5. 自动打开浏览器

---

## 当前架构 vs. 文档中的架构

### 文档期望（commands/visualize.md）

```
package.json (npm)
    ↓
npm install && npm run build (Vite)
    ↓
npm run server (port 3141)
```

### 实际代码（visualize/ 目录）

```
package.json (npm)
    ↓
npm run build (Vite)
    ↓
npm run start / npm run server
```

### 差异影响

文档与代码已对齐，无差异。

---

## "开箱即用"现状与改进方案

### 现状问题

```
~/.pi/visualize.sh 首次运行：
  1. 下载 1 GB+ PI 仓库（git clone）
  2. npm install (~200MB)
  3. npm run build (~30秒)
  4. 启动服务 (~5秒)
  总耗时：2-5 分钟 ❌
```

### 推荐方案

#### A. 预编译可执行文件（最优）
```
~/.pi/visualizer-cli           # Go/Rust 二进制
~/.pi/visualize-dist/          # 前端资源
~/.pi/visualize.sh             # 轻量启动器

用户运行：~/.pi/visualize.sh
结果：1 秒内启动 ✅ 无依赖 ✅
```

#### B. 静态 HTML 嵌入（轻量）
```
~/.pi/visualize.html           # 完全独立的 HTML（包含决策数据）

用户运行：~/.pi/visualize.sh
结果：直接打开本地 file:// ✅ 无服务器 ✅
缺点：不支持实时更新 ❌
```

#### C. Node.js Bundle（折中）
```
使用 pkg 或 esbuild 打包
~/.pi/visualizer-cli-linux-x64
~/.pi/visualizer-cli-macos-arm64

用户运行：~/.pi/visualize.sh
结果：无需 Node.js，但文件 50-100MB
```

---

## 生产部署推荐

### 开发 (npm run dev)

```bash
启动 Vite dev server (port 5173)
启动 Express server (port 3141)
支持 HMR 和 WebSocket
```

**不适用于生产环境**

### 生产标准 (npm run start)

```bash
npm run build           # 构建 dist/
npm run server          # 启动服务器
```

**问题：** 用户需要 Node.js + npm

### 生产最优方案

```bash
# 构建时（CI/CD）
npm run build:bundle    # 生成二进制
npm run build:standalone  # 生成静态 HTML

# 发布时
包含预编译的 visualizer-cli-*
包含预构建的 dist/
包含轻量 ~/.pi/visualize.sh

# 用户端
~/.pi/visualize.sh
```

---

## PI SKILL 发布中的可视化约束

### PUBLISH.md 第 3.6b 步

在发布 PI SKILL 时，必须同步验证：

- [ ] `install.sh` 包含 visualizer launcher 安装步骤
- [ ] `scripts/setup-standalone-visualize.sh` 可独立执行
- [ ] `cursor/rules/pi-visualize.mdc` 随 Cursor 安装
- [ ] 文档（README/commands）中的说明与实现一致
- [ ] 没有将 visualizer 说成"用户必须手动 clone"

### PUBLISH.md 第 3.12 步（可视化校验）

- [ ] install.sh 有 visualizer launcher 安装
- [ ] setup 脚本的 URL 与公开仓库一致
- [ ] Cursor 规则文件包含 pi-visualize.mdc
- [ ] 不存在悬空引用或过时说明

---

## 快速诊断

### 用户遇到 "/visualize 不工作"

检查清单：
```bash
# 1. 检查启动器是否存在
ls ~/.pi/visualize.sh

# 2. 检查决策数据是否存在
ls ~/.pi/decisions/

# 3. 手动测试启动
bash ~/.pi/visualize.sh

# 4. 如果失败，重新初始化
bash ~/.pi/setup-standalone-visualize.sh

# 5. 检查依赖
command -v git && echo "✓ git" || echo "✗ git"
command -v node && echo "✓ node" || echo "✗ node"
command -v npm && echo "✓ npm" || echo "✗ npm"
```

### 用户遇到 "Hook 不生成决策文件"

检查清单：
```bash
# 1. 检查 hooks 配置是否加载
cat ~/.claude/.claude-plugin/hooks.json

# 2. 检查 hooks 脚本是否存在
ls ~/.claude-plugin/hooks/capture-*.sh

# 3. 检查决策目录权限
ls -la ~/.pi/decisions/

# 4. 检查最新的决策文件
ls -lt ~/.pi/decisions/*/*.json | head -5

# 5. 手动触发一次 hook
bash ~/.claude-plugin/hooks/capture-decision.sh
```

---

## 相关文档导航

| 文件 | 用途 |
|------|------|
| `/commands/visualize.md` | visualize 命令的完整说明 |
| `/commands/pi.md` | /pi visualize 路由说明 |
| `/visualize/USER_GUIDE.md` | Visualizer 操作指南 |
| `/visualize/SPEC.md` | 技术规范（API/数据格式） |
| `/PUBLISH.md` | 发布流程（包含可视化校验） |
| `/DISTRIBUTE.md` | 分发流程（包含可视化配套） |
| `/hooks/hooks.json` | Hook 定义 |
| `/scripts/setup-standalone-visualize.sh` | 独立安装脚本 |
| `/install.sh` | 一键安装脚本 |

