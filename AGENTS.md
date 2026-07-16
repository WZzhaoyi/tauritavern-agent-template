# TauriTavern Agent 同人小说生成系统

> **Version**: 2.5.0
> **Purpose**: 从同一份创作源数据构建 Agent 或非 Agent 角色卡套件

---

## 1. 系统概述

### 1.1 工作流（4 步）

```
Step 1  配置与规划 — 编辑本文件第 2 节配置区
  ↓
Step 2  素材创作 — 角色卡文学指南 + 世界书设定 + 状态阶段资料
  ↓
Step 3  场景创作 — 首条消息和备选开场
  ↓
Step 4  生成输出 — python scripts/generate.py
```

`build.target` 是构建开关。一次构建只产生一种运行目标，不要将同一张角色卡视为两种模式的通用产物。

**`build.target: "agent"` → `output/agent/`**：

| 文件 | 用途 |
|------|------|
| `{project.id}.agent-profile.json` | Agent 配置档案：继承官方默认运行提示，允许用户的其他 Skills |
| `skills/state-system.ttskill` | 状态工作流 Skill，导入 Agent 系统面板 SKILLS 页 |
| `{project.id}.character-card.json` | Agent 目标角色卡，不含 legacy `_.set(...)` 协议 |
| `skills/interaction-system.ttskill` | 可选暂停式交互协议与声明式地图/行动资源 |
| `extensions/{project.id}-interaction/` | 可选点击交互扩展，单独安装，不限制普通文字输入 |
| `agent-overrides.css` | 前端美化，按需导入主题 |

**`build.target: "non_agent"` → `output/non-agent/`**：

| 文件 | 用途 |
|------|------|
| `{project.id}.character-card.json` | 传统生成目标角色卡，可含 legacy 状态更新协议 |
| `{project.id}.state-worldbook.json` | 由 `_stages` 生成的状态世界书，供非 Agent 状态运行时读取 |

### 1.2 目录结构

```
project/
├── AGENTS.md                     # 本指南与配置中心
├── CLAUDE.md                     # 项目入口
├── literature/
│   ├── characters/               # 状态阶段数据 _stages.{json|yaml}
│   ├── scenarios/                # 场景剧本 .md（含 YAML Frontmatter）
│   └── fanfic/                   # 风格样本、设定参考原文
├── skills/
│   ├── state-system/SKILL.md     # Agent 状态计算与持久化工作流
│   └── interaction-system/       # 可选暂停式交互协议
├── interaction/                  # 作者编辑的地图、区域与基础行动
├── extensions/
│   └── interaction-runtime/      # 通用 UI 运行时；不要在这里写剧情规则
├── examples/
│   └── hongloumeng/              # 四地点、四角色的最小创作与测试示例
├── tests/                         # 示例构建和跨文件一致性测试
├── theme/
│   └── agent-overrides.css       # 前端美化（可选）
├── scripts/
│   ├── generate.py               # 主生成脚本
│   └── convert_stages_format.py  # 阶段文件格式转换工具
└── output/
    ├── agent/                    # Agent 目标产物
    └── non-agent/                # 非 Agent 目标产物
```

### 1.3 文件命名规范

| 文件类型 | 格式 | 示例 |
|---------|------|------|
| 角色阶段数据 | `{角色名}_stages.{json\|yaml}` | `张三_stages.json` |
| 场景剧本 | `{序号}_{场景名}.md` | `01_initial.md` |
| 世界书条目 | 由 TauriTavern / SillyTavern 管理 | 角色、地点、势力、背景 |
| Skill ID | 小写字母、数字、`-`、`_` | `state-system` |

---

## 2. 配置区

> 只改值，不改键名；缩进 2 空格；冒号后必须有空格；stages 数量 = ranges 长度 − 1。

```yaml
# =============================================================================
# 作品元数据
# =============================================================================
project:
  # 稳定 ASCII 标识：用于 Profile ID 与导出文件名，不能使用中文或空格
  id: "my-card-writer"
  name: "{作品名}"
  version: "1.0.0"
  description: "{一句话描述}"

# =============================================================================
# 状态维度定义
# ranges 定义阶段边界，stages 按从高到低排列（最后=最低范围）
# =============================================================================
dimensions:
  - id: "affection"
    name: "{维度1名称}"
    description: "{维度1描述}"
    ranges: [0, 25, 50, 75, 100]
    initial: 0
    legacy_key: "{维度1名称}"  # 非 Agent _.set 路径使用；应与原世界书状态变量名一致
    update_rules: |
      日常正向互动 +1~2；明确建立信任或关系突破 +3~5；冲突或背叛 -1~5。
      重复既有态度、仅在背景中出现或没有当前轮证据时不变。
    stages:
      - "{阶段4}"    # 76-100
      - "{阶段3}"    # 51-75
      - "{阶段2}"    # 26-50
      - "{阶段1}"    # 0-25

  - id: "corruption"
    name: "{维度2名称}"
    description: "{维度2描述}"
    ranges: [0, 30, 60, 100]
    initial: 0
    legacy_key: "{维度2名称}"
    update_rules: |
      {在这里定义本维度增加、减少和保持不变的触发条件，以及不同事件对应的增量。}
    stages:
      - "{阶段3}"    # 61-100
      - "{阶段2}"    # 31-60
      - "{阶段1}"    # 0-30

# =============================================================================
# 构建目标开关：agent 或 non_agent
# 修改后重新运行 generate.py；两种目标分别输出到独立目录。
# =============================================================================
build:
  target: "agent"

# =============================================================================
# 暂停式点击交互（仅影响 agent 构建）
# true 时打包 interaction-system 并生成可单独安装的 UI Extension。
# 具体玩法不写在这里；编辑 interaction/ 与 interaction-system Skill。
# =============================================================================
interaction:
  enabled: true

# =============================================================================
# 路径配置
# =============================================================================
paths:
  characters_dir: "literature/characters"
  scenarios_dir: "literature/scenarios"
  output_dir: "output"

# =============================================================================
# 叙事者
# =============================================================================
narrator:
  name: "{作品名}"
  creator: "{创作者名称}"
  description: "《{作品名}》的叙事者。"
  personality: "{叙事者的简短性格或创作定位}"
  persona: |
    你是《{作品名}》的叙事者。文学与扮演指南以本角色卡为准，角色、地点、关系和世界事实以已激活世界书为准。

    【文学与扮演原则】
    - {作品基调、叙事身份与视角规则}
    - {角色对白、动作和心理描写规则}
    - {身份切换或多角色扮演规则}
    - 不自行改写角色卡与世界书中的既有事实。
  style_instructions: |
    {把文风要求写成每轮可直接执行的简短规则，例如句式、描写密度、对白格式和禁止项。}

# =============================================================================
# 风格样本（注入角色卡 description）
# =============================================================================
style_sample:
  source_file: "literature/fanfic/示例对话.txt"
  max_length: 1500

# =============================================================================
# 阶段数据格式：json 或 yaml（选定后统一使用，不可混用）
# =============================================================================
stages_format: "yaml"

# =============================================================================
# 状态更新契约
# update_rules 定义单个维度的语义；此处定义所有维度共同遵守的限制。
# custom_rules 是套件作者的扩展入口，可写互斥条件、剧情旗标规则和特殊角色例外。
# =============================================================================
state_system:
  persist_file: "persist/character_states.yaml"
  max_characters_per_turn: 2
  max_delta_per_dimension: 5
  custom_rules: |
    - 只更新当前轮有实际台词、动作、选择或明确受事件影响的角色。
    - 同一事实不得跨轮重复计分；没有新进展时保持原值。
    - {在这里补充本角色卡套件独有的状态更新规则。}
  non_agent:
    # 仅影响 non_agent 构建。true：角色卡输出兼容原 SillyTavern 状态脚本的 _.set(...) 块。
    # false：角色卡不输出每轮更新命令；场景中的 legacy 初始化块仍保留。
    emit_legacy_updates: true

# =============================================================================
# Agent 配置档案
# agentSystemPrompt 固定为 null，由 TauriTavern 按实际工具生成默认运行协议。
# Profile 对 Skills 使用 visible: ["*"]；state-system 的必读性由 Agent 角色卡桥接指令保证。
# =============================================================================
agent:
  max_rounds: 12
  max_tool_calls: 30
  model_retries: 2
  # 子 Agent 默认关闭；此模板不会授予 agent.delegate 等工具。
  # 仅在明确需要随机事件/检定时调用 dice.roll。
  enable_dice: true

# =============================================================================
# 本项目要打包的 SKILLS 清单（不是运行时白名单）
# 每个目录单独打包为一个 .ttskill；用户本地其他 Skills 仍对 Agent 可见。
# =============================================================================
skills:
  - id: "state-system"
    source_dir: "skills/state-system"
  - id: "interaction-system"
    source_dir: "skills/interaction-system"

# =============================================================================
# 主题（可选）
# =============================================================================
theme:
  source_file: "theme/agent-overrides.css"
```

---

## 3. 工作流步骤

### Step 1: 配置与规划

1. 复制 `AGENTS.md`、`CLAUDE.md`、`scripts/` 到新项目
2. 编辑第 2 节配置区，替换 `{占位符}`，并为 `project.id` 设置稳定 ASCII 标识
3. 选择 `build.target`：`agent` 或 `non_agent`
4. 确定 `stages_format`：`json` 或 `yaml`
5. Agent 目标需要点击式交互时保留 `interaction.enabled: true`；纯文字套件设为 `false`

### Step 2: 素材创作

**角色卡**：将文学风格、叙事视角、扮演指南和首条/备选开场放入角色卡。这些创作源数据可共用，但生成的角色卡会按 `build.target` 分化状态协议。

- `narrator.persona` 写入角色卡 `system_prompt`，用于长期稳定的身份与文学/扮演原则。
- `narrator.style_instructions` 写入 `post_history_instructions`，用于每轮直接执行的简短风格要求。
- Agent 目标从当前 prompt snapshot 继承它们，并在 `post_history_instructions` 追加一条简短桥接指令：每轮必须读取 `state-system`，其他用户 Skills 可按需扩展。
- 非 Agent 目标直接由普通生成使用文学/扮演指南和 legacy 状态协议。

**Agent 扩展原则**：Profile 的 `instructions.agentSystemPrompt` 保持 JSON `null`，不复制 TauriTavern 默认的工具调用、commit 和 finish 提示。每轮都要执行的作品规则放在角色卡，按需读取的工作流与资料放在 Skills。这样本套件扩展官方 Agent，而不替代其运行协议。

Profile 的工具清单按 TauriTavern 当前规范使用精确工具名：默认授予当前全部非委派内置工具，只有意排除子 Agent 委派工具；`dice.roll` 由 `agent.enable_dice` 单独开关。这是执行边界，不是对用户 Skills 的白名单。官方增加新工具后，生成器也需同步加入其精确名称。

**暂停式交互**：`interaction.enabled: true` 时，生成器额外打包 `interaction-system` 并输出一个通用 UI Extension。玩家可以点击地图、目标和行动按钮；扩展先写入一条紧凑、可审计的 `[交互行动]` 用户消息，再通过官方 `api.agent.startRunFromLegacyGenerate()` 启动一个前台 Agent 回合。扩展用 `api.agent.subscribe()` 显示真实运行阶段，完成后读取 `persist/interaction-state.yaml` 刷新界面。

交互层只规定最低互操作协议，不规定题材和玩法：

- 编辑 `interaction/actions.yaml` 定义基础行动；Agent 也可以在持久状态中生成当轮行动。
- 编辑 `interaction/regions.yaml` 与可选 `interaction/map.svg` 定义地点。SVG 可点击元素使用 `data-region-id` 对应区域 ID。
- `skills/interaction-system/SKILL.md` 定义状态投影规则，允许作者和其他 Skills 在 `extensions` 或未知字段中继续扩展。
- 普通文字输入始终有效；点击面板是便利入口，不是对玩家表达方式的限制。
- `api.chat`、`api.worldInfo` 与移动 Layout 契约存在时自动增强；不存在时隐藏相应功能，不影响核心 Agent 回合。

**传统世界书**：将可复用的角色、地点、势力、背景和静态关系存入 TauriTavern / SillyTavern 世界书。它是这类设定的唯一真相来源，并按原有规则动态激活；本模板不会复制整份世界书到 Skill。

非 Agent 目标不能读取 Skill。生成器会把同一批 `_stages.{json|yaml}` 编译为 `{project.id}.state-worldbook.json`，其中每个角色的阶段数据位于 `<character_states>` 块。它是可导入的状态世界书，可与另行维护的角色/设定/背景世界书并用或合并。

**状态阶段资料** — `literature/characters/{角色名}_stages.{json|yaml}`：

- 按状态维度记录阶段行为表现。
- `agent` 目标：复制到 `state-system.ttskill` 的 `references/character-stages/`。
- `non_agent` 目标：编译到状态世界书的 `<character_states>` 条目。

**SKILL 内容** — `skills/state-system/SKILL.md`：

- 只定义 Agent 的状态计算、持久化和检查流程。
- 生成器会将 `dimensions` 配置写入 Skill 的 `references/dimensions.yaml`。
- 生成器会将 `state_system` 配置写入 Skill 的 `references/update-policy.yaml`。
- 套件作者通过各维度的 `update_rules` 和全局 `custom_rules` 定义自己的状态逻辑，无需修改 Skill 模板。
- Profile 使用 `skills.visible: ["*"]`；这个项目的 `skills:` 配置只决定打包哪些 `.ttskill`，不会隐藏或禁用用户本地的其他 Skills。

**交互内容** — `interaction/` 与 `skills/interaction-system/SKILL.md`：

- `actions.yaml`、`regions.yaml` 和 `map.svg` 会进入 `interaction-system.ttskill` 的 `assets/`。
- 交互扩展通过 Host `api.skill.readFile()` 读取这些 UTF-8 资源；地图优先使用 SVG，避免二进制资源读取依赖。
- `persist/interaction-state.yaml` 是 Agent 权威的 UI 投影；扩展的聊天级缓存只用于快速恢复界面，不替代它。
- 不要把具体剧情判断写入通用扩展 JavaScript；应放入角色卡、世界书、状态规则或作者自己的 Skills。

仓库内的 `examples/hongloumeng/` 是最小完整示例，同时由 `tests/test_hongloumeng_example.py` 验证地图区域、必要人物、世界书、阶段资料和实际生成产物保持一致。示例不会进入默认项目输出。

**风格样本** — 从原著选取代表段落，原则：
- 叙事节奏、对话风格、描写手法各选 1 段
- 直接摘录原文，总长 ≤ 1500 字

### Step 3: 场景创作

`literature/scenarios/{序号}_{场景名}.md` 格式：

```
---
name: 场景名称
description: 一句话描述
pov: 第三人称视角     # 声明适配视角，留空=不指定
variables:             # 可选：本开场的初始状态，键必须使用 dimension id
  角色A:
    affection: 20
    corruption: 5
---
[前情提要：3-5 句]

[场景正文：500-900 字，收束于待回应的钩子]
```

- 首文件为 `first_mes`，其余为 `alternate_greetings`，随角色卡进入聊天历史。
- `agent` 目标将 `variables` 写为 `<agent_state_init>` YAML，供 Skill 首次建立 `persist/`。
- `non_agent` 目标将 `variables` 写为 `<character_states_init>` 中的 legacy `_.set(...)`。
- Agent Mode 开启后，Agent 从当前聊天上下文继续创作，不直接读取项目中的场景文件。

### Step 4: 生成输出

```bash
python scripts/generate.py
```

脚本读取 `build.target` 后只生成对应目标：

- `agent`：Profile + SKILLS + Agent 角色卡 + 可选交互扩展 + 主题 CSS。
- `non_agent`：状态世界书 + legacy 角色卡。

Agent Profile 中 `agentSystemPrompt` 必须是 `null`，不是空字符串。TauriTavern 会依据实际可用工具和工作区生成默认 Agent 运行提示；本模板不复制这份提示。

### 导入 Agent 目标

1. Characters → Import → `output/agent/{project.id}.character-card.json`
2. Agent 系统面板 → SKILLS → 导入 `output/agent/skills/` 下的每一个 `.ttskill`
3. Agent 系统面板 → 配置档案 → 导入 → `output/agent/{project.id}.agent-profile.json`
4. 设为 Active Profile，开启 Agent Mode 即可使用
5. 若启用交互，按 `output/agent/extensions/{project.id}-interaction/README.md` 单独安装 UI Extension

TauriTavern 当前没有公开“随角色卡或 Skill 自动安装第三方 UI Extension”的 API，因此生成器不会绕过用户确认自动安装扩展。发布套件时，建议把生成的扩展目录作为独立 Git 仓库分发；不安装扩展时，角色卡、世界书、Agent Profile 和 Skills 仍可通过普通文字正常使用。

### 导入非 Agent 目标

1. Characters → Import → `output/non-agent/{project.id}.character-card.json`
2. World Info / Lorebooks → Import → `output/non-agent/{project.id}.state-worldbook.json`
3. 将状态世界书与角色卡/聊天绑定，保持 Agent Mode 关闭
4. 需要数值自动持久化时，另行启用兼容 legacy `_.set(...)` 的状态运行时

### 两种构建目标的状态行为

| 模式 | 状态规则来源 | 状态写入方式 | 依赖 |
|------|-------------|-------------|------|
| `agent` | `state-system` Skill + 角色卡/世界书上下文 | Agent 校验后写入 `persist/character_states.yaml` | 支持工具调用的 LLM API、Profile 的 workspace 工具 |
| `non_agent` + legacy 运行时 | 状态世界书 + 角色卡 `post_history_instructions` | LLM 输出 `_.set(...)`，由兼容状态脚本执行 | 原 SillyTavern 状态管理扩展/脚本 |
| `non_agent` 且未安装脚本 | 角色卡与状态世界书仍可导入 | 数值不会自动保存 | 手动维护，或将 `emit_legacy_updates` 设为 false |

两种构建可以共用 `dimensions`、`update_rules`、`custom_rules`、`_stages` 和场景初始值作为源数据，但运行时产物不共用。Agent 产物使用维度 `id` 与 `persist/`；非 Agent 产物使用 `legacy_key` 与状态脚本。

两种产物的状态存储彼此独立。不应在同一聊天中途直接互换角色卡或状态后端；如果必须迁移已有进度，需要专门的状态转换/同步步骤。

LLM 对自然语言事件的判断不是确定性计算。模板通过以下原则降低数值错误：旧值必须可追溯、只计算当前轮、限制参与角色与单轮增量、执行 `old + delta = new`、限制边界，并在 Agent Mode 写回后重新读取核对。需要绝对确定性的公式、UI 联动或跨会话全局状态时，仍应使用脚本或专用工具。

交互扩展不拥有剧情状态。Agent 成功 `workspace.finish` 后，`persist/` 才会成为下一回合的权威状态；失败或取消时界面保留上一个成功投影，并允许重试。当前公开 API 不支持 rollback、Agent streaming 或稳定 extension tool bridge，因此模板不会伪造撤销、逐 token 流式状态或 Skill 脚本工具。

### 非 Agent legacy 运行时

`emit_legacy_updates: true` 只负责让角色卡要求 LLM 输出兼容的 `_.set(...)`，不会自行执行命令。若当前 TauriTavern / SillyTavern 环境兼容原模板运行时，可沿用：

1. 安装 `https://github.com/n0vi028/JS-Slash-Runner`。
2. 在脚本管理中启用：

```javascript
import 'https://testingcf.jsdelivr.net/gh/WZzhaoyi/tavern_helper/dist/角色状态管理/index.js'
```

若不使用该运行时，将 `emit_legacy_updates` 设为 `false`，避免普通回复出现不会被执行的状态命令。

---

## 4. SKILL.md 格式

每个 Skill 目录下必须有 `SKILL.md`，以 YAML frontmatter 开头：

```markdown
---
name: skill-id
description: 简短描述
---

# Skill 标题

## 使用时机
- 什么情况下应读取本 Skill

## 内容
按需组织，可拆分到 references/ 子目录
```

要求：`name` 用小写字母、数字、`-`、`_`；`description` 简要说明用途。

---

## 5. 常见问题

| 问题 | 解决 |
|------|------|
| 生成了错误模式的文件 | 检查 `build.target` 是 `agent` 还是 `non_agent`，重新运行生成器 |
| Agent 不读 `state-system` | 确认 Skill 已导入，且 Agent 目标角色卡保留了“每轮必读 `state-system`”桥接指令 |
| 用户本地其他 Skills 不可见 | 检查生成 Profile 的 `skills.visible` 是否为 `["*"]`，以及 Skill 本身的作用域是否适用于当前运行 |
| Agent 不提交回复 | 确认 `workspace.commit` 工具已启用 |
| 状态不更新 | 检查 `state-system` SKILL 是否正确导入，且 Agent 有 `persist/` 读写权限 |
| 角色卡没有“行动”按钮 | 确认 `interaction.enabled: true`，已安装生成的 UI Extension，并导入 `interaction-system.ttskill` |
| 点击行动后没有启动 | 确认当前为单角色 chat-completion 路径，Profile ID 与生成套件一致，且 TauriTavern 提供 `api.agent.startRunFromLegacyGenerate` |
| 地图不能点击 | 检查 `map.svg` 元素的 `data-region-id` 是否与 `regions.yaml` 中的 `id` 一致 |
| 交互状态没有刷新 | 检查 `persist/interaction-state.yaml` 是否在成功 `workspace.finish` 前被 Agent 写入；失败或取消不会提升持久变更 |
| Agent 正文出现 `_.set(...)` | 检查导入的是 Agent 目标角色卡，并确认 `state-system` 中的可见输出边界未被其他 Skill 覆盖 |
| 非 Agent 下看不到阶段资料 | 使用 `non_agent` 构建并导入/绑定生成的 `.state-worldbook.json` |
| 非 Agent 模式数值未保存 | `_.set(...)` 需要原 SillyTavern 兼容状态脚本执行；未安装时不会自动保存 |
| 数值变化不符合玩法 | 修改对应维度的 `update_rules` 或 `state_system.custom_rules`，重新生成并导入角色卡与 Skill |
| 世界书设定未生效 | 检查传统世界书的关键词、递归和角色绑定；Agent 只能读取本轮已激活条目 |

---

## 附录：阶段数据格式（_stages.yaml）

```yaml
character_states:
  - id: "affection"
    name: "好感度"
    ranges:
      - min: 0
        max: 25
        content: "阶段描述"
      - min: 26
        max: 50
        content: "阶段描述"
      - min: 51
        max: 75
        content: "阶段描述"
      - min: 76
        max: 100
        content: "阶段描述"
```
