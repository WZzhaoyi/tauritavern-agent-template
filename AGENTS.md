# TauriTavern Agent 角色卡套件

> Version: 2.7.0

## 核心约束

- 具体作品只放在 `projects/<project-id>/`；不要把项目规则写入根目录通用代码。
- `AGENTS.md` 是项目指南，机器配置只放在项目的 `tauritavern.yaml`。
- 根目录 `tauritavern.template.yaml` 是配置模板，不是可直接构建的项目配置。
- 一次构建只选择 `agent` 或 `non_agent`；两种产物和状态存储不能混用。
- 角色卡保存创作身份、输出风格和扮演规则；世界书保存角色、地点、关系与世界事实。
- 生成产物不得作为创作源文件修改。

## 目录所有权

```text
根目录                         模板维护
├── scripts/                   生成器
├── skills/                    通用 Skills
├── extensions/                通用交互运行时
├── theme/                     默认主题
├── tests/                     框架与项目测试
└── tauritavern.template.yaml  配置模板

projects/<project-id>/         项目维护
├── AGENTS.md                  项目指南
├── tauritavern.yaml           项目配置
├── literature/                阶段资料、场景、风格样本
├── lorebooks/                 世界书
├── interaction/               行动、区域、地图
├── skills/                    可选项目 Skill 或覆盖
├── theme/                     可选项目主题覆盖
└── output/                    生成产物
```

项目缺少通用 Skill 或主题时，生成器从模板根目录读取。交互扩展从根目录独立安装，不进入项目产物；项目规则使用配置、世界书或项目 Skill 表达。

## 工作步骤

### 1. 创建项目

1. 在 `projects/<project-id>/` 创建项目目录。
2. 复制 `tauritavern.template.yaml` 为项目的 `tauritavern.yaml`。
3. 创建项目自己的 `AGENTS.md`。
4. 参考 `projects/hongloumeng/` 补齐素材目录。

配置要点：

- `schema_version` 当前为 `1`。
- `framework.version` 必须与根模板一致。
- `project.id` 只能使用小写 ASCII 字母、数字、`-` 和 `_`。
- `dimensions` 可为空；定义维度时，`stages` 数量必须等于 `ranges` 长度减一。
- `build.target` 只能是 `agent` 或 `non_agent`。
- `interaction.enabled` 只影响 Agent 构建。
- 素材和输出目录使用固定约定，不在配置中重定义路径。
- `skills:` 只表示随套件打包的 Skills，不是运行时白名单。
- Agent Profile 的 `agentSystemPrompt` 保持 `null`，`skills.visible` 保持 `["*"]`。
- 项目生成的 Skill 必须导入并绑定到对应角色卡的角色作用域；这是用户导入约定，不是 Agent Prompt 限制，也不限制用户其它可见 Skills。

### 2. 编写素材

角色卡配置：

- `narrator.persona`：稳定的创作身份与执行原则；只在具体作品需要时定义叙事视角。
- `narrator.style_instructions`：每轮直接执行的简短文风要求。
- `style_sample.source_file`：可选风格样本，长度受 `max_length` 限制。

世界书：

- 保存角色、地点、势力、背景和静态关系。
- 由 TauriTavern / SillyTavern 管理激活规则。
- 不要把整份世界书复制进 Skill。

不需要数值状态时保持 `dimensions: []`；Agent 构建会跳过 `state-system`。需要状态时，阶段文件使用 `literature/characters/{角色名}_stages.json`：

```json
{
  "character_states": [
    {
      "id": "dimension-id",
      "name": "维度名称",
      "ranges": [
        {"min": 0, "max": 25, "content": "阶段描述"},
        {"min": 26, "max": 50, "content": "阶段描述"}
      ]
    }
  ]
}
```

要求：

- 维度 ID 必须存在于 `tauritavern.yaml`。
- 范围连续且与配置一致。
- 内容只描述该阶段的行为、态度和边界。

### 3. 编写场景

文件名：`literature/scenarios/{序号}_{场景名}.md`。首文件生成 `first_mes`，其余生成 `alternate_greetings`。

```text
---
name: 场景名称
description: 一句话描述
---
[前情提要]

[场景正文，结尾留下待回应的钩子]
```

- `variables` 是可选的状态初始化元数据，不写时不假定初始变量；视角只在 `narrator.persona` 或场景正文中按项目需要定义。
- 使用 `variables` 时，其键必须是已声明的 dimension ID。
- Agent 构建把 `<agent_state_init>` 放入默认折叠的 `<details>`。
- 非 Agent 构建生成 legacy 初始化块。
- 不替玩家决定内心、身份或最终选择。

### 4. 配置交互

启用 `interaction.enabled` 后维护：

- `interaction/actions.json`：基础行动。
- `interaction/regions.json`：地点和区域。
- `interaction/map.svg`：可选地图；可点击元素的 `data-region-id` 必须匹配区域 ID。

动态行动由 Agent 按打包后的 `interaction-system` Skill 生成；`actions.json` 只提供预设与回退行动，不会自动变成作品专属提示词。通用 Skill 只定义交互协议和回合事务。具体作品对下一轮选项有特殊要求时：

1. 以根目录 `skills/interaction-system/SKILL.md` 为基础，在 `projects/<project-id>/skills/interaction-system/SKILL.md` 创建项目覆盖。
2. 保留通用 Skill 的输入协议、状态文件、`workspace.commit` 和 `workspace.finish` 约定，只补充“项目行动策略”。
3. 在策略中明确：选项数量与类型、允许的 `scope`、稳定 ID 命名、哪些行动需要 `confirm`，以及何时使用 `disabled` 与 `disabled_reason`。
4. 说明作品边界：选项只基于当前轮可知事实，不剧透、不预设结果、不替玩家做最终选择，并保留与作品节奏相符的观察、等待、离开或自由行动空间。
5. 无法生成可靠动态选项时写入 `"actions": []`，让界面回退到 `assets/actions.json`；不要写入缺少 `id` 或 `label` 的非空数组。

项目的 `AGENTS.md` 应记录是否使用通用行动策略；若有覆盖，只记录维护边界和素材来源，实际 Agent 提示必须写入项目 `interaction-system` Skill。人物、地点和剧情事实仍放在世界书，不复制进 Skill。

普通聊天输入和交互面板中的自定义行动输入始终有效。项目规则放在配置、世界书或项目 Skill 中，不写入通用扩展 JavaScript。

### 5. 构建

```bash
python scripts/generate.py projects/<project-id>
```

| 目标 | 输出 |
|---|---|
| `agent` | `output/agent/`：角色卡、Profile、Skills、主题和世界书 |
| `non_agent` | `output/non-agent/`：角色卡和可选状态世界书 |

## 运行约定

### Agent

- 先导入角色卡；导入随项目打包的 `.ttskill` 时，把目标作用域设为该角色卡；最后导入 Agent Profile。Skill 安装名为 `<project-id>-<skill-id>`，不同项目可共存。
- Profile 必须启用 workspace 提交工具；骰子由 `agent.enable_dice` 控制。
- 声明状态维度时，每轮读取项目专属 `state-system`，只更新有当前轮证据的角色和维度；`dimensions: []` 时跳过。
- 启用角色状态时保存到 `persist/character_states.json`。
- 启用交互时，同时维护 `persist/interaction-state.json` 和 `output/main.md`。
- 首轮持久文件不存在是正常情况，应创建而不是报错。
- 没有数值变化时不重写状态；证据不足时保持原值。
- 完成正文和状态后提交并结束运行。

### Non-Agent

- 导入角色卡并保持 Agent Mode 关闭；只有声明状态维度时才导入状态世界书。
- `emit_legacy_updates: true` 只生成 `_.set(...)`，仍需兼容运行时执行。
- 未安装运行时时设置为 `false`，或手动维护状态。

## Skill 约定

每个 Skill 目录必须包含以 YAML frontmatter 开头的 `SKILL.md`：

```text
---
name: skill-id
description: 简短说明
---

# Skill 标题
```

- `name` 使用小写字母、数字、`-` 或 `_`。
- 配置中的 Skill ID 不得重复，并且必须与 frontmatter `name` 一致。
- 打包时自动将安装名改为 `<project-id>-<skill-id>`；源目录继续使用配置中的原始 Skill ID。
- 生成的角色卡通过模板扩展字段声明 `skillInstallScope: character` 和项目化安装名；这是导入清单，不是 Agent Prompt 权限或运行时白名单。
- 大型资料放入 `references/`，运行时资源放入 `assets/`。

## 模板更新

- 下游仓库每周检查模板更新并创建 PR，不自动合并。
- `.github/.templatesyncignore` 必须保护 `projects/` 和 `.github/workflows/`。
- 手动运行 **Sync template** 默认是 dry-run。
- 同步后先运行测试，再按需迁移项目并更新 `framework.version`。
- 工作流逻辑不自动同步；Actions 版本由 Dependabot 更新。

## 测试与发布

```bash
python -m unittest discover -s tests -v
node --check extensions/interaction-runtime/index.js
```

- `projects/hongloumeng/` 是完整构建测试项目。
- 修改生成器、通用 Skill、扩展、配置 schema 或项目结构后必须运行完整测试。
- 发布 tag 使用 `vMAJOR.MINOR.PATCH`，并与 `tauritavern.template.yaml` 的 `framework.version` 一致。

## 常见检查

| 问题 | 检查 |
|---|---|
| 找不到配置 | 项目根目录是否存在 `tauritavern.yaml` |
| 框架版本不匹配 | 检查迁移后更新项目 `framework.version` |
| Agent 不读状态 Skill | 是否把最新的 `<project-id>-state-system.ttskill` 导入当前角色卡的角色作用域 |
| Agent 不发布正文 | Profile 是否启用 workspace commit |
| 点击行动无效 | 是否已安装根目录通用交互扩展，并把 `<project-id>-interaction-system.ttskill` 导入当前角色卡的角色作用域 |
| 地图不能点击 | SVG `data-region-id` 是否匹配 `regions.json` |
| 非 Agent 状态不保存 | 是否安装 legacy 状态运行时 |
| 世界书未生效 | 检查关键词、递归、绑定和激活状态 |
