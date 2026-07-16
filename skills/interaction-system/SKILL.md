---
name: interaction-system
description: 将玩家点击行动转换为暂停式 Agent 回合，并维护供交互界面读取的最小状态投影。
---

# Interaction System

## 使用时机

- 每次启用交互界面的 Agent 写作运行。
- 用户消息以 `[交互行动]` 开头时。
- 回复完成前需要刷新地点、目标或下一轮行动时。

本 Skill 是角色卡套件的可选交互桥梁，不定义题材、胜负条件、资源体系或固定玩法。角色卡决定文学与扮演方式，已激活世界书决定人物和世界事实，`state-system` 决定角色数值事务，用户的其他可见 Skills 仍可继续扩展工作流。

## 读取内容

1. `references/runtime.yaml`：当前套件 ID 和交互状态文件路径。
2. `assets/actions.yaml`：作者提供的基础行动；允许为空，也允许增加自定义字段。
3. `assets/regions.yaml`：作者提供的地点/区域；允许增加自定义字段。
4. `assets/map.svg`：可选界面地图。模型通常无需读取 SVG 内容。

区域可以用可选的 `characters` 列出最初可能在此出现的人物，供状态文件尚未建立时参考；它是场景入口，不是角色永远固定在该地点的硬规则。实际在场人物仍以当前剧情、世界书与持久状态为准。

界面可能把当前选择写成紧凑消息：

```text
[交互行动] {"action":{"id":"observe","label":"观察"},"target":{"type":"region","id":"start","label":"起始地点"}}
```

只把它视为玩家本轮明确选择，不把 JSON 字段直接复述到正文。

## 权威状态与界面投影

交互状态文件默认是 `persist/interaction-state.yaml`。它是 Agent 维护、界面只读的投影；不要把扩展缓存或界面选中状态当成剧情真相。

最小结构：

```yaml
version: 1
turn: 1
summary: "当前局势的一句话摘要"
location:
  id: "start"
  label: "起始地点"
targets: []
actions: []
extensions: {}
```

- `targets` 可包含当前可交互的人物、地点、物品或作者自定义目标。
- `actions` 可覆盖本轮界面行动；为空或缺失时，界面回退到 `assets/actions.yaml`。
- `extensions` 是套件作者的扩展空间。可以加入地图状态、资源、旗标、任务或自定义面板数据。
- 对未知字段应尽量原样保留，避免阻止其他 Skill 或未来版本扩展。

推荐的目标与行动项：

```yaml
targets:
  - type: character
    id: example-character
    label: 示例人物
    description: 可选的界面短说明
actions:
  - id: talk
    label: 交谈
    scope: character
    confirm: false
```

这些字段只为通用界面提供最低互操作性，不限制作者添加其它字段或使用不同题材。

## 回合事务

1. 读取现有交互状态；不存在时用场景、世界书和基础资源建立最小状态。
2. 读取玩家本轮输入。若是 `[交互行动]`，核对行动 ID 与当前目标；动态 `actions` 中的行动同样有效。
3. 按角色卡、已激活世界书、状态规则和其它可见 Skills 生成叙事。
4. 完成 `state-system` 要求的角色状态事务。
5. 把已经发生的结果投影到交互状态：递增 `turn`，更新简短 `summary`、当前位置、目标和下一轮可用行动。
6. 回读 YAML，确认语法有效且没有丢失无关字段，再交回 TauriTavern 默认 Agent 流程提交正文并 `finish`。

如果玩家行动因剧情条件无法完成，应在叙事中自然反馈，并仍然给出合理的下一轮行动；不要悄悄替换成另一项选择。需要随机检定时可以按作品规则使用 `dice.roll`，但本 Skill 不强制随机性。

## 输出边界

- 正文保持文学叙事，不显示内部状态计算、工具协议或完整 YAML。
- 界面只是输入和状态展示入口，不能覆盖角色卡、世界书或持久状态。
- 不要求玩家只能点击行动；普通文字输入始终是合法的自由行动。
- 不执行 Skill 内脚本，也不假定存在 MCP、extension tool bridge、流式 Agent 或回滚 API。
