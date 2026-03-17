<!--
  Licensed to the Apache Software Foundation (ASF) under one or more
  contributor license agreements.  See the NOTICE file distributed with
  this work for additional information regarding copyright ownership.
  The ASF licenses this file to You under the Apache License, Version 2.0
  (the "License"); you may not use this file except in compliance with
  the License.  You may obtain a copy of the License at

      http://www.apache.org/licenses/LICENSE-2.0

  Unless required by applicable law or agreed to in writing, software
  distributed under the License is distributed on an "AS IS" BASIS,
  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
  See the License for the specific language governing permissions and
  limitations under the License.

  Copyright (c) 2026 HePin
-->

# PI 用户指南

这份指南面向**真正要开始用 PI**的人，也面向**准备打开决策历史可视化器复盘**的人。

重点只有两个：

1. **怎么把 PI 用起来**
2. **怎么把 PI 产生的历史看明白**

文中只写**当前仓库已经实现**的能力；凡是还没做完、或文档里提到但代码里没完全落地的地方，我都会明确写成“当前限制”。

---

## 1. 先知道：PI 和可视化器分别做什么

### PI 是什么

PI（智行合一）本体是一套给 AI 助手使用的工作方法和命令路由，核心是：

- 按任务自动切换场景
- 用统一的交付标准约束 AI
- 把重要过程通过 hooks 记录成**脱敏后的决策历史**

你可以把它理解成：

```text
你提任务
  ↓
PI 组织 AI 的做事方式
  ↓
hooks 记录关键事件（已脱敏）
  ↓
~/.pi/decisions/ 下形成历史
  ↓
PI Visualize 把这些历史变成可交互页面
```

### 决策历史可视化器是什么

PI Visualize 是本仓库 `visualize/` 里的本地工具。它会读取 `~/.pi/decisions`（或你指定的目录），把历史组装成一个**离线可打开的 HTML**，或者启动一个**仅监听本机 127.0.0.1 的 live 预览服务**。

它已经实现的重点能力包括：

- 会话树浏览
- 时间线回放
- 决策图画布
- 节点详情抽屉
- 指标面板
- Heatmap 时间热图
- 双会话 compare mode
- 会话搜索、节点搜索
- 键盘快捷键
- 浏览器内导入 / 导出 / 分享
- 多 Agent roster 和交互链展示

---

## 2. 你会怎么用 PI：最实用的理解方式

如果你第一次接触 PI，建议按下面这个顺序理解。

### 2.1 最常见的两种入口

#### 入口 A：正常用 PI 处理任务

当你是要让 AI 干活时，用 `/pi ...`。

`commands/pi.md` 当前实现的参数路由是：

| 写法 | 当前行为 |
|---|---|
| `/pi` | 默认 Auto 模式 + 自动场景路由 |
| `/pi loop` | Loop 模式 |
| `/pi auto` | Auto 模式 |
| `/pi 编程`、`/pi 调试`、`/pi 测试` 等 | 强制指定场景 |
| `/pi visualize ...` | 不走普通 PI 场景流，直接进入可视化器路由 |

#### 入口 B：打开可视化器

当你是要看历史时，**有两类入口**：

1. **宿主已经接好命令路由时**：
   - `/pi visualize`
   - `/visualize`

2. **按安装方式区分的稳定入口**：
   - 如果你正在 PI 仓库源码 checkout 里工作：`cd visualize && mill frontend.standaloneHtml && mill cli.run`
   - 如果你已经运行过 `install.sh` 或 standalone setup：`~/.pi/visualize.sh`

要特别注意：

- `commands/pi.md` 和 `commands/visualize.md` 确实定义了 `/pi visualize` / `/visualize` 的命令语义
- 但**不是每种安装方式都会自动把这些命令接到你的宿主里**
- 所以如果你只是按 README 把 skill 文件复制到 `~/.copilot/skills/pi`，那一步**只保证 skill 本身可用**，并不会自动生成 `~/.pi/visualize.sh`
- 这时你要么在 PI 仓库源码 checkout 里运行 `mill cli.run`，要么先执行 `install.sh` / standalone setup，再用 `~/.pi/visualize.sh`

也就是说，`/pi visualize` / `/visualize` 是**“宿主已接线时可用的快捷入口”**，而不是所有环境里都天然存在的可执行命令。

---

## 3. 第一步：把 PI 装到你正在用的平台里

本仓库确实给了多个平台的安装/接入方式，但你只需要先装你当前在用的那个。

### 3.1 GitHub Copilot CLI

`README.md` 当前给出的安装方式：

```bash
mkdir -p ~/.copilot/skills/pi && cp skills/pi/SKILL.md ~/.copilot/skills/pi/SKILL.md
```

如果你还要看可视化器，需要区分两件事：

- **PI skill 安装**：上面的复制命令能把方法论装进 Copilot 的 skill 目录
- **visualizer 命令入口**：只有当你的宿主额外接入了 `commands/pi.md` / `commands/visualize.md` 这类命令路由时，`/pi visualize` / `/visualize` 才会直接可用

所以对 Copilot CLI 来说，**最稳的 visualizer 打开方式**取决于你手头是哪一种安装形态：

```bash
cd visualize && mill frontend.standaloneHtml && mill cli.run
```

如果你已经跑过一键安装或 standalone setup，也可以直接用：

```bash
~/.pi/visualize.sh
```

### 3.2 Cursor

Cursor 当前仓库里明确提供的是规则文件：

```bash
mkdir -p .cursor/rules
cp cursor/rules/pi.mdc .cursor/rules/pi.mdc
```

另外还专门提供了 `cursor/rules/pi-visualize.mdc`，里面写了在 Cursor 中如何用 `/pi visualize` 打开本地可视化器。

### 3.3 Qoder

Qoder 当前不是“专用原生可视化实现”，而是**通过通用 hooks / adapter 接入**。

仓库里已有：

- `qoder/README.md`
- `qoder/pi-qoder-adapter.sh`
- `hooks/capture-generic.sh`

示例：

```bash
./qoder/pi-qoder-adapter.sh qoder do-something
```

或者把输出喂给通用捕获 hook：

```bash
qoder ... | ./hooks/capture-generic.sh
```

### 3.4 通用 PI-enabled 项目

只要你的环境能：

- 运行 shell hook
- 提供一些基础环境变量，或
- 把事件以 JSON / 文本形式送给 `hooks/capture-generic.sh`

就能把数据写进 `~/.pi/decisions`，再用同一个可视化器查看。

---

## 4. 第二步：正常用 PI 做任务

这一节不讲“理念”，只讲**你实际怎么下命令**。

### 4.1 最简单的开始方式

```text
/pi 修复登录接口 500 错误
```

或者：

```text
/pi 调试 排查构建失败
```

或者：

```text
/pi 测试 给这个模块补回归测试
```

如果你不指定场景，PI 会按当前任务内容自动路由。

### 4.2 什么时候用 Loop，什么时候用 Auto

`commands/pi.md` 当前支持：

- `loop`
- `auto`

#### Loop 模式

适合你希望 AI **每轮都继续追问和接续**，不轻易停下的时候。

示例：

```text
/pi loop 编程 把 visualize 的导出流程讲清楚并给示例
```

#### Auto 模式

适合你希望 AI **尽量自主推进** 的时候。

示例：

```text
/pi auto 调试 排查为什么 live preview 没刷新
```

### 4.3 一个典型使用流程

```text
你提出任务
  ↓
PI 选择模式（loop / auto）
  ↓
PI 选择场景（编程 / 调试 / 测试 / 产品 / 运营 / …）
  ↓
AI 执行，hooks 记录关键节点
  ↓
结果写入 ~/.pi/decisions/YYYY-MM-DD/
  ↓
你再用 visualize 复盘
```

### 4.4 实际上会留下什么历史

当前实现会把脱敏后的历史写到：

```text
~/.pi/decisions/YYYY-MM-DD/
```

常见文件包括：

- `session-*.json`
- `session-*.events.jsonl`
- `session-*.nodes.jsonl`

这些文件会被 `visualize/cli/LocalArchiveBuilder.scala` 读取并组装。

---

## 5. 第三步：打开可视化器

### 5.1 最常用：离线 HTML

如果你走的是仓库现在的**一键安装链路**，安装器会先放置：

```bash
~/.pi/visualize.sh
```

这样你即使不在仓库根目录里，也有一个统一的本地 visualizer 启动入口；首次运行时它会按需 bootstrap standalone runtime。

如果你已经在仓库根目录，最直接的命令是：

```bash
cd visualize && mill frontend.standaloneHtml && mill cli.run
```

这也是宿主已接线时 `/visualize` / `/pi visualize` 背后的核心流程。

默认行为是：

- 源目录：`~/.pi/decisions`
- 模板：`visualize/out/frontend/standaloneHtml.dest/index.html`
- 输出：`visualize/out/cli/pi-visualize.html`
- 在支持桌面自动拉起浏览器的环境里，会尝试自动打开浏览器；否则只打印输出路径

如果你不想自动打开浏览器：

```bash
cd visualize && mill cli.run --no-open
```

如果你想换输出路径：

```bash
cd visualize && mill cli.run --no-open --output /tmp/pi.html
```

如果你的历史不在默认目录：

```bash
cd visualize && mill cli.run --source /path/to/.pi/decisions
```

### 5.2 Live 本地预览

如果你希望浏览器在本地历史变化时持续刷新，用：

```bash
cd visualize && mill cli.run --live
```

这里一定要注意：

- 这不是 `file://` 自动刷新
- 它会启动一个**只监听本机**的预览服务
- 地址形态是 `http://127.0.0.1:<随机端口>/`
- 前端每 **800ms** 轮询 `/api/archive`
- 只有在当前环境支持桌面浏览器自动拉起时，CLI 才会尝试直接打开这个地址；否则会把 URL 打印给你自己打开

所以 live 模式更像：

```text
本地 decisions 目录变化
  ↓
CLI 本地 server 重新装配 archive
  ↓
浏览器轮询 /api/archive
  ↓
页面热更新
```

### 5.3 `/pi visualize` 和 `/visualize` 的关系

当前仓库里：

- `/pi visualize` 是 `commands/pi.md` 里的**特殊路由**
- `/visualize` 是独立命令定义

但这里说的是**命令定义已经存在于仓库**，不是说所有安装方式都会自动把它们暴露给你的宿主。

真正稳定的入口要按环境来看：

- 你在 PI 仓库源码 checkout 中时：`cd visualize && mill frontend.standaloneHtml && mill cli.run`
- 你已经执行过 `install.sh` 或 standalone setup 时：`~/.pi/visualize.sh`

当宿主已经把 `commands/` 目录接成 slash 命令时，`/pi visualize` 和 `/visualize` 才会走同一个 visualizer 工程。

`/pi visualize` 还会先按规则寻找 visualizer 位置：

1. 当前目录下存在 `./visualize/build.mill` 时，使用 `./visualize`
2. `~/.pi/visualize.sh`
3. `~/.pi/visualize/visualize`
4. `~/.pi/visualize`（且包含 `build.mill`）

都没有时，会提示你运行：

```bash
curl -fsSL https://raw.githubusercontent.com/share-skills/pi/main/scripts/setup-standalone-visualize.sh | bash
```

这个 standalone setup 依赖 `git` 和 `mill`。

---

## 6. 第一次运行时的 GitHub 绑定 / 本地历史同步，到底会发生什么

这一块最容易被误解，下面按**当前代码真实行为**讲。

### 6.1 先说结论

**只看可视化器时，当前并不强制绑定 GitHub。**

你直接运行：

```bash
cd visualize && mill cli.run
```

就可以生成本地 HTML。

GitHub 绑定的用途是：

- 保存一个同步配置到 `~/.pi/config.json`
- 把**脱敏后的 session JSON**同步到你指定的本地 git worktree
- 需要时再做 `git push`

也就是说，它本质上是：

> “历史同步配置 + 本地 worktree 同步 + 可选远程推送”

而不是“没有绑定就不能打开可视化器”。

### 6.2 交互式终端第一次运行时

如果满足这些条件：

- 你在交互式终端里运行
- 当前没有配置文件
- 你没有显式传 `--bind-github`
- 你也没有传 `--github-repo`

那么 CLI 会先问你：

```text
PI history sync is not configured yet. Bind a GitHub repository now? [y/N]:
```

### 如果你选 N

什么都不会中断，CLI 会继续正常生成可视化页面。

### 如果你选 Y

它会依次收集：

- GitHub 仓库：`owner/repo` 或 GitHub URL
- branch：默认 `main`
- 本地 git worktree 路径

然后把配置保存到：

```text
~/.pi/config.json
```

### 6.3 非交互式场景

如果没有交互式控制台，`--bind-github` 不能靠提问完成。

这时需要显式带上至少：

```bash
cd visualize && mill cli.run \
  --bind-github \
  --github-repo hepin/pi \
  --github-branch main \
  --github-worktree ~/.pi/github-history/hepin/pi
```

否则代码会直接报：

```text
--bind-github requires --github-repo when running without an interactive console
```

### 6.4 绑定后每次运行会同步什么

只要：

- 绑定配置存在
- source 目录存在

CLI 就会在构建 archive 后执行本地 history sync。

当前真实行为是：

1. 把 session 做**分享级脱敏**
2. 写入 worktree 下的：

```text
<你的-worktree>/pi-history/YYYY-MM-DD/session-....json
```

3. 删除过期的旧同步文件
4. `git add -A -- pi-history`
5. 如果有变化，自动创建一个**本地 commit**

commit message 形态类似：

```text
pi: sync sanitized history for main (12 sessions) 2026-03-17
```

### 6.5 push 是可选的，不会偷偷发生

默认只做本地 commit。

只有你显式传下面这些参数时，才会做 push 相关动作：

- `--github-push`
- `--github-push-dry-run`
- `--github-push-remote <name>`

示例：

```bash
cd visualize && mill cli.run --github-push-dry-run
```

或：

```bash
cd visualize && mill cli.run --github-push --github-push-remote origin
```

### 当前安全边界

代码里已经明确限制：

- **不会自动创建 remote**
- **不会强制切换 branch**
- 如果当前 worktree branch 和配置 branch 不一致，会**跳过 push**
- 如果 remote 不存在，会只打印建议命令

也就是说，当前实现更偏保守，不会越权帮你改 git 远程配置。

---

## 7. 打开页面后，你会看到什么

可以把当前 UI 理解成这个布局：

```text
┌──────────────────────────────────────────────────────────────┐
│ Top Bar: source / sessions / model / context / warnings     │
├──────────────────────────────────────────────────────────────┤
│ Timeline: slider + Play/Pause + Prev/Next + speed           │
├───────────────┬───────────────────────────────┬─────────────┤
│ Session Tree  │ Decision Canvas               │ Inspector   │
│ + search      │ + node search                 │ Metrics     │
│ + quick scrub │ + pan/zoom/drag/collapse      │ Heatmap     │
│               │ + reveal current              │ Interaction │
└───────────────┴───────────────────────────────┴─────────────┘
```

在 compare mode 下，右边会变成**双画布对比**。

---

## 8. 怎么看会话：Session 浏览与树导航

左侧是 `TreeNav`。

当前已实现：

- 按日期分组
- 每天可展开/收起
- 每个 session 显示：
  - session 短 ID
  - scene
  - summary
  - 节点数
  - 创建时间
  - interaction mode
- 顶部 session 搜索
- 搜索结果 Prev / Next
- Quick scrub 滑块 + Prev / Next 快速切换

### 当前 session 搜索能搜什么

搜索会匹配这些字段：

- session id
- date
- summary
- scene
- interaction mode
- createdAt

也就是说，它是**基础关键词过滤**，不是全文智能搜索。

### 一个常见用法

1. 先在左侧输入 `调试`、`编程`、日期、summary 关键字
2. 用 `Prev result / Next result` 跳结果
3. 点进目标 session
4. 再在右侧时间线和节点里继续定位

---

## 9. 怎么看主画布：Decision Canvas

中间是决策图画布。

当前实现不是 D3，不依赖远程图形库，而是**Pure Scala + HTML/CSS 图层**。

### 9.1 它怎么布局

当前逻辑是：

- 能推断父子关系时，用层级布局
- 否则回退为时间线式布局

### 9.2 你能做什么

当前已实现：

- 点击节点：同步时间线游标
- 拖动节点：手动调整布局
- 滚轮：缩放
- 拖动画布空白处：平移
- 点节点右上角 `+/-`：折叠 / 展开子树
- `Reveal current`：把当前高亮节点滚动/居中到视图里
- `Reset view`：重置缩放和平移
- `Reset layout`：清掉手动拖拽偏移和折叠状态

### 9.3 节点搜索现在能搜什么

当前节点搜索匹配：

- node id
- node label
- category
- scene
- battle stage
- timestamp

而且现在一个很实用的细节已经做好了：

- **搜索会包含被折叠后代**
- 如果你 reveal 到一个被祖先折叠住的节点，系统会自动展开祖先再定位

---

## 10. 时间线怎么用

顶部时间线当前支持：

- 拖动滑块
- `Prev`
- `Next`
- `Play / Pause`
- 速度切换：`0.5x / 1x / 2x / 4x`

### 时间线与其他面板的关系

当你移动时间线时，会同步更新：

- 主画布高亮
- Metrics
- Detail drawer
- Heatmap 跳转目标

### 它读的是 nodes 还是 history

当前实现是：

- 如果 session 里有 `history`，优先按 `history` 驱动时间线
- 没有 `history`，才回退到 `nodes`

这点很重要，因为它解释了为什么有些 session 的回放粒度更细。

---

## 11. Heatmap 热图怎么看

Heatmap 在单会话模式下显示，位于指标面板下面、交互链上面。

当前有两条热图：

1. **Battle Stage Distribution**
2. **Spirit Animal Activity**

### 热图的含义

系统会把时间线默认分成 **8 个桶**，然后统计每个时间段里：

- 哪个战势更占主导
- 哪些灵兽更活跃

### 你可以怎么读

- 颜色/透明度更强：这个时间段更“密集”
- 数字更大：该桶里出现次数更多
- 点击某个格子：时间线直接跳到该时间段起点

### 当前限制

- bucket 数目前是实现参数，默认 8
- compare mode 下 Heatmap 会隐藏，避免布局冲突

---

## 12. Compare mode：怎么对比两次会话

点顶部按钮：

```text
Compare: Off  →  Compare: On
```

即可进入 compare mode。

### 当前 compare mode 已实现什么

- 左右双画布
- Secondary session 选择
- 主副会话游标按**归一化进度**同步
- 对比版 metrics
- 对比版节点链上下文
- 对比版 interaction summary

### 它适合看什么

- 同一个问题两次解决思路差异
- 同一个场景在不同模型下的节奏差异
- 同一个 session 在不同 battle stage 下的演化方式

### 当前限制

- 目前是**双会话对比**，不是多会话矩阵
- Heatmap 在 compare mode 中不会显示
- 主要快捷键中的 `N`、`R` 当前默认作用在主画布

---

## 13. Detail Drawer：怎么看节点详情

桌面端它会以**浮动面板**出现在画布右侧。

小屏时，当前实现会**回退为内嵌布局**，避免把主画布挤坏。

### 现在详情里能看到什么

至少包括：

- Node
- Label
- Category
- Scene
- Session mode
- Model
- Cognition
- Retry
- Failure
- Battle
- Confidence
- Animals
- Resonance
- Strategy
- Outcome
- Privacy

如果节点 payload 里带了上下文，还会显示：

- Thought chain
- Human input
- Interaction point
- Assistant question
- User decision
- Classic
- Next
- Payload 明细

### 这意味着什么

它不只是“看一个点”，而是能让你把：

- AI 当时用了什么认知模式
- 人类输入在什么位置介入
- 失败/重试是怎么累积的

放到一个面板里看。

---

## 14. Thought & Interaction Chain：怎么读多 Agent 历史

右侧还有一个非常重要的面板：

```text
Thought & interaction chain
```

这个面板当前已经实现两块内容：

1. **Agent Roster**
2. **Interaction Timeline**

### 14.1 Agent Roster

当 hooks 采到了 Agent 数据后，你会看到：

- 名称 / display name
- 角色（Leader / Teammate / Coach 等）
- parent agent
- status badge

而且 `cancelled` 这种状态现在会被保留下来，不会再被模糊成 unknown。

### 14.2 Interaction Timeline

当前会展示：

- 人类输入摘要
- skill / PI 上下文
- subagent handoff
- 关键交互点
- 时间戳
- 相关 metadata

### 14.3 它依赖什么

这部分不是“凭空出现”的，它依赖 hooks 事件流。

仓库中当前已接入的关键事件有：

- `UserPromptSubmit`
- `SubagentStart`
- `SubagentStop`
- Bash 工具结果
- 若存在 `team.*` 事件，也会被合并

### 当前限制

- 如果你的平台没有把这些事件喂给 hooks，这一栏会显示空态
- 它展示的是**脱敏摘要链**，不是原始长文本对话全文

---

## 15. 搜索、过滤、键盘快捷键

这一块已经很好用了，而且都是当前代码里真实存在的。

### 15.1 Session 搜索

聚焦左侧 session 搜索框后，可以筛选：

- id
- 日期
- scene
- summary
- mode

### 15.2 Node 搜索

在画布上方的 node 搜索框里，可以查：

- label
- id
- scene
- category

### 15.3 当前快捷键

| 快捷键 | 当前行为 |
|---|---|
| `Alt + ↑` | 上一个 session（尊重当前 filter） |
| `Alt + ↓` | 下一个 session（尊重当前 filter） |
| `Alt + ←` | 时间线后退一步 |
| `Alt + →` | 时间线前进一步 |
| `/` | 聚焦 session 搜索 |
| `N` | 聚焦 node 搜索 |
| `R` | Reveal 当前节点 |

### 实用建议

如果你已经筛过 session，再用 `Alt + ↑ / ↓`，它只会在**筛选结果内部**移动，这一点对复盘非常省事。

---

## 16. 导入、导出、分享：现在怎么做最稳

### 16.1 导入

浏览器内当前支持：

- 选择文件导入
- 拖拽文件导入

能吃进去的内容包括：

- `.json`
- `.jsonl`
- `.pi-session.json`
- `.events.jsonl`
- standalone `.html` share artifact

多个文件导入时，前端会把它们合并成一个 archive。

### 16.2 导出

顶部现在有两个明确的导出按钮：

- `Export session`
- `Export archive`

对应产物：

- `*.pi-session.json`
- `pi-archive.json`

### 16.3 分享

顶部还有：

- `Share HTML`

它会把**当前选中的单个 session**导出成一个可离线打开的单文件 HTML。

这个文件可以通过：

- 邮件
- IM
- Gist

之类的方式发给别人。

### 16.4 隐私保护现在到底做了什么

这块当前实现非常明确：

#### 普通脱敏

`PrivacySanitizer` 会处理：

- `prompt`
- `content`
- `source_code`
- `patch`
- `diff`
- `password`
- `credential`
- `api_key`
- `access_token`
- `refresh_token`
- `stdin/stdout/stderr`

以及：

- 用户目录路径
- 可疑长 token
- 常见密钥/凭证字样

要注意这里的边界：

- `access_token` / `refresh_token` 这类键名会按**字段键名**直接命中脱敏
- 裸字段名 `token` **不是当前实现里的精确 blocked key**
- 但如果字符串内容里出现 `token=...`、`token: ...` 这类模式，仍可能被文本级规则启发式脱敏

#### 分享级脱敏

`sanitizeForShare` 会进一步：

- 把 `sessionId` 改成 `shared-session`
- 把 agent 改名为 `Agent 1`、`Agent 2`……
- 去掉 parent 关系中的真实身份
- 强制标记为 redacted
- 把 agents / interactions / history 记入 masked fields

### 16.5 当前限制

- `Share HTML` 当前是**单 session**
- 不是“整个 archive 一键分享成大 HTML”
- 导出的分享件是**脱敏工件**，不是原始记录

---

## 17. 响应式布局：现在做到什么程度

当前实现不是“桌面专用写死页面”。

从变更记录和前端代码来看，已经明确做了这些：

- 时间线控件上移到顶部，并保持可见
- 左侧 session 列表支持滚动
- detail drawer 在桌面端浮动显示
- 小屏时 detail drawer 回退为内嵌布局

### 这意味着什么

- **单会话浏览**在较小窗口里也能工作
- **对比模式**仍然更适合大屏 / 桌面端

### 当前限制

- 仓库没有把它定位成“手机优先”产品
- 复杂 compare 场景在窄屏下可读性会下降

---

## 18. 不同平台现在到底支持到什么程度

这一节只写“当前仓库真实能支撑到哪一步”。

### 18.1 GitHub Copilot CLI

**当前 genuinely 支持：**

- 安装 PI skill 到 `~/.copilot/skills/pi`
- 使用 `/pi` 方法论路线
- hooks 识别 `COPILOT_SESSION_ID`
- hooks 读取 `COPILOT_MODEL*`、`COPILOT_INPUT_TOKENS`、`COPILOT_OUTPUT_TOKENS`
- tool 结果采集脚本支持 `COPILOT_TOOL_*`

**这意味着：**

- 如果你的 Copilot CLI 环境把这些变量和事件传出来，visualizer 能把它们展示出来
- 如果你的宿主还额外接入了 `commands/` 命令路由，那么 `/pi visualize` / `/visualize` 也可以直接使用；否则请在源码 checkout 里走 `mill cli.run`，或在完成安装后使用 `~/.pi/visualize.sh`

### 18.2 Cursor

**当前 genuinely 支持：**

- 安装 `cursor/rules/pi.mdc`
- 使用 `cursor/rules/pi-visualize.mdc` 中定义的 `/pi visualize` 使用方式

**需要你知道的边界：**

- Cursor 这边仓库里看到的是“规则层支持”
- 历史采集质量仍取决于你是否把 PI hooks / 事件链真正接上

### 18.3 Qoder

**当前 genuinely 支持：**

- `qoder/pi-qoder-adapter.sh`
- `qoder/README.md` 里的接入说明
- `hooks/capture-generic.sh` 通用事件捕获

**适合的使用方式：**

```bash
./qoder/pi-qoder-adapter.sh qoder do-something
```

或：

```bash
qoder ... | ./hooks/capture-generic.sh
```

### 18.4 通用 PI-enabled 项目

**当前 genuinely 支持：**

- 用 `PI_*` 环境变量提供模型/会话信息
- 用 `hooks/capture-generic.sh` 送入外部事件
- 把产物写成可被 visualizer 装配的 session / events / nodes 文件

如果你的项目不是仓库里这些“官方适配平台”，但能满足上面这几条，就可以接入可视化器。

---

## 19. 一套推荐工作流：从干活到复盘

如果你想马上开始，建议直接照这个流程走。

### 流程 A：日常开发

```text
1. 用 /pi 处理任务
2. 让 hooks 把历史写入 ~/.pi/decisions
3. 用 visualizer 打开页面（宿主已接线时可用 `/pi visualize`；源码 checkout 里可用 `mill cli.run`；安装流可用 `~/.pi/visualize.sh`）
4. 看时间线 + 详情抽屉
5. 找失败点、战势升级点、交互分叉点
```

### 流程 B：对比两次解决过程

```text
1. 打开 visualizer
2. 在左侧选第一条 session
3. 打开 Compare
4. 选第二条 session
5. 对比 metrics / node chain / interaction
```

### 流程 C：分享一个可安全外发的样本

```text
1. 选中目标 session
2. 点击 Share HTML
3. 发出生成的单文件 HTML
```

### 流程 D：把历史同步到本地 git worktree

```bash
cd visualize && mill cli.run \
  --bind-github \
  --github-repo hepin/pi \
  --github-branch main \
  --github-worktree ~/.pi/github-history/hepin/pi
```

以后再跑：

```bash
cd visualize && mill cli.run
```

它就会按已保存的配置继续做本地同步。

---

## 20. 当前已实现 vs 当前限制

这是最重要的“防踩坑”清单。

### 已实现

| 功能 | 当前状态 |
|---|---|
| `/pi visualize` 路由 | 已实现 |
| `/visualize` 命令 | 已实现 |
| 离线单文件 HTML | 已实现 |
| `--live` 本地预览 | 已实现 |
| 会话树 + 日期展开/收起 | 已实现 |
| Session 搜索 / 快速切换 | 已实现 |
| 决策图画布（拖拽/缩放/平移/折叠） | 已实现 |
| 节点搜索 + reveal | 已实现 |
| Timeline 回放 | 已实现 |
| Metrics | 已实现 |
| Heatmap | 已实现 |
| Compare mode | 已实现 |
| Detail drawer | 已实现 |
| Import / Export | 已实现 |
| Share HTML（单 session） | 已实现 |
| 多 Agent roster / interaction chain | 已实现 |
| 本地 worktree history sync | 已实现 |
| 可选 git push / dry-run | 已实现 |

### 当前限制

| 主题 | 当前限制 |
|---|---|
| 搜索 | 目前是基础关键词搜索，不是高级组合过滤 |
| 分享 | 重点是单 session HTML，不是整 archive 的一键分享页 |
| Compare | 只支持双会话对比 |
| Heatmap | compare mode 下隐藏 |
| 多 Agent | 依赖 hooks 事件是否采到 |
| Live | 依赖 CLI 本地进程常驻；不是 file:// 自动刷新 |
| GitHub 同步 | 默认只做本地 commit；push 必须显式开启 |
| Git 远程处理 | 不会自动建 remote，不会强切 branch |
| 布局 | 自动布局仍在继续增强，不是最终版 |
| 命令入口 | `/pi visualize` / `/visualize` 取决于宿主是否接好 `commands/` 路由；源码 checkout 用 `mill cli.run`，安装流用 `~/.pi/visualize.sh` |

---

## 21. 最后给你一组“拿来就用”的命令

### 用 PI 处理任务

```text
/pi 修复 visualize compare mode 的问题
```

```text
/pi loop 调试 为什么热图点击后没有跳到预期节点
```

```text
/pi auto 编程 给 visualizer 补用户文档
```

### 打开可视化器

```bash
cd visualize && mill frontend.standaloneHtml && mill cli.run
```

### 不自动打开浏览器

```bash
cd visualize && mill cli.run --no-open
```

### 指定输出文件

```bash
cd visualize && mill cli.run --no-open --output /tmp/pi.html
```

### Live 预览

```bash
cd visualize && mill cli.run --live
```

### 首次绑定并同步到本地 git worktree

```bash
cd visualize && mill cli.run \
  --bind-github \
  --github-repo hepin/pi \
  --github-branch main \
  --github-worktree ~/.pi/github-history/hepin/pi
```

### 先做 push dry-run

```bash
cd visualize && mill cli.run --github-push-dry-run
```

### 真正 push

```bash
cd visualize && mill cli.run --github-push --github-push-remote origin
```

### 安装 standalone visualizer

```bash
curl -fsSL https://raw.githubusercontent.com/share-skills/pi/main/scripts/setup-standalone-visualize.sh | bash
```

---

## 22. 一句话总结

如果你只记住一句话：

> **PI 负责让 AI 做事更有章法，Visualize 负责把这套做事过程变成你能复盘、对比、分享的本地可视化历史。**

先把 PI 用起来，再用 visualize 回头看，你会更容易真正理解它的价值。
