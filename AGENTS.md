# TauriTavern Agent 同人小说生成系统

> **Version**: 2.0.0
> **Purpose**: 为 TauriTavern Agent 模式生成 Agent Profile、SKILLS 知识包、角色卡和前端美化配置

---

## 1. 系统概述

### 1.1 工作流（4 步）

```
Step 1  配置与规划 — 编辑本文件第 2 节配置区
  ↓
Step 2  素材创作 — 角色档案 + SKILLS 内容 + 设定参考
  ↓
Step 3  场景创作 — 首条消息和备选开场
  ↓
Step 4  生成输出 — python scripts/generate.py
```

**输出文件**（位于 `output/`）：

| 文件 | 用途 |
|------|------|
| `{作品名}.agent-profile.json` | Agent 配置档案，导入 TauriTavern Agent 系统面板 |
| `{作品名}.ttskill` | SKILLS 知识包，导入 Agent 系统面板 SKILLS 页 |
| `{作品名}角色卡.json` | 精简角色卡，导入 TauriTavern Characters |
| `agent-overrides.css` | 前端美化，按需导入主题 |

### 1.2 目录结构

```
project/
├── AGENTS.md                     # 本指南与配置中心
├── CLAUDE.md                     # 项目入口
├── literature/
│   ├── characters/               # 角色档案 .md + _stages.{json|yaml}
│   ├── scenarios/                # 场景剧本 .md（含 YAML Frontmatter）
│   └── fanfic/                   # 风格样本、设定参考原文
├── skills/                       # SKILLS 知识包源文件
│   ├── writing-style/SKILL.md
│   ├── state-system/SKILL.md
│   ├── pov-switching/SKILL.md
│   ├── world-lore/SKILL.md
│   └── character-profiles/SKILL.md
├── theme/
│   └── agent-overrides.css       # 前端美化（可选）
├── scripts/
│   ├── generate.py               # 主生成脚本
│   └── convert_stages_format.py  # 阶段文件格式转换工具
└── output/                       # 生成输出
```

### 1.3 文件命名规范

| 文件类型 | 格式 | 示例 |
|---------|------|------|
| 角色基础档案 | `{角色名}.md` | `张三.md` |
| 角色阶段数据 | `{角色名}_stages.{json\|yaml}` | `张三_stages.json` |
| 场景剧本 | `{序号}_{场景名}.md` | `01_initial.md` |
| SKILL.md 标题 | 小写字母、数字、`-`、`_` | `writing-style` |

---

## 2. 配置区

> 只改值，不改键名；缩进 2 空格；冒号后必须有空格；stages 数量 = ranges 长度 − 1。

```yaml
# =============================================================================
# 作品元数据
# =============================================================================
project:
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
    stages:
      - "{阶段4}"    # 76-100
      - "{阶段3}"    # 51-75
      - "{阶段2}"    # 26-50
      - "{阶段1}"    # 0-25

  - id: "corruption"
    name: "{维度2名称}"
    description: "{维度2描述}"
    ranges: [0, 30, 60, 100]
    stages:
      - "{阶段3}"    # 61-100
      - "{阶段2}"    # 31-60
      - "{阶段1}"    # 0-30

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
# Agent 配置档案
# =============================================================================
agent:
  max_rounds: 12
  max_tool_calls: 30
  model_retries: 2
  history_count: -1          # -1=全部聊天历史, 0=不带入, N=最近N条
  include_worldinfo: true
  subagent_enabled: false

# =============================================================================
# SKILLS 清单（脚本据此验证并打包为 .ttskill）
# =============================================================================
skills:
  - id: "writing-style"
    source_dir: "skills/writing-style"
  - id: "state-system"
    source_dir: "skills/state-system"
  - id: "pov-switching"
    source_dir: "skills/pov-switching"
  - id: "world-lore"
    source_dir: "skills/world-lore"
  - id: "character-profiles"
    source_dir: "skills/character-profiles"

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
2. 编辑第 2 节配置区，替换 `{占位符}`
3. 确定 `stages_format`：`json` 或 `yaml`

### Step 2: 素材创作

**角色档案** — `literature/characters/{角色名}.md` + `_stages.{json|yaml}`：

- `.md` 为极简键值对格式，外貌/台词/称呼用 `「」` 引用原文短语
- `_stages` 按维度记录各阶段行为表现

**SKILLS 内容** — `skills/*/SKILL.md`：

- `writing-style`：文风偏好、句式规则、对话风格
- `state-system`：状态计算规则、各维度阶段描述
- `pov-switching`：叙事视角切换规则、角色扮演模式指南
- `world-lore`：世界观、势力、地点、物品、静态关系
- `character-profiles`：角色静态设定（外貌、性格、背景等）

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
---
[前情提要：3-5 句]

[场景正文：500-900 字，收束于待回应的钩子]
```

- 首文件为 `first_mes`，其余为 `alternate_greetings`
- Agent 运行时读取场景并基于上下文续写

### Step 4: 生成输出

```bash
python scripts/generate.py
```

脚本自动读取配置 → 验证 SKILLS → 生成 Agent Profile + .ttskill + 角色卡 + 主题 CSS。

### 导入 TauriTavern

1. Characters → Import → `{作品名}角色卡.json`
2. Agent 系统面板 → 配置档案 → 导入 → `{作品名}.agent-profile.json`
3. Agent 系统面板 → SKILLS → 导入 → `{作品名}.ttskill`
4. 设为 Active Profile，开启 Agent Mode 即可使用

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
| Agent 不读 SKILLS | 检查 Profile 中 SKILLS 访问权限，确认 `skills` 清单的 Skill 已导入 |
| Agent 不提交回复 | 确认 `workspace.commit` 工具已启用 |
| 状态不更新 | 检查 `state-system` SKILL 是否正确导入，且 Agent 有 `persist/` 读写权限 |
| 角色卡导入失败 | 检查 `literature/characters/` 是否有有效的 `.md` 文件 |

---

## 附录：角色档案格式

### A. 角色基础档案（.md）

```
名称: 示例角色（称号）
性别: 女
MBTI: INFJ
貌龄: 二十五
年龄: 未明确
背景: 某门派核心弟子
性格: 外冷内热 —— 「表面高傲」却「暗藏渴念」
外貌: 「肤若凝脂，眉目如画」，常「一袭素白长裙」
台词风格:
  口癖: 「哼，不值一提」
  语气: 话少字冷，急怒时语速陡快
情感: 对主角「又爱又恨」
称呼习惯:
  自称: 「我」
  对主角: 「你」（私下）/「大人」（人前）
```

### B. 阶段数据（_stages.yaml）

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
