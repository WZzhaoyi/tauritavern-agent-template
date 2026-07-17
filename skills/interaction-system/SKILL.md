---
name: interaction-system
description: 将玩家点击行动转换为暂停式 Agent 回合，并维护供交互界面读取的最小状态投影。
---

# Interaction System

## 使用时机

- 每次启用交互界面的 Agent 写作运行。
- 本次运行的隐式 prompt 包含 `<tt_interaction_input>` 时。
- 回复完成前需要刷新地点、目标或下一轮行动时。

本 Skill 是角色卡套件的可选交互桥梁，不定义题材、胜负条件、资源体系或固定玩法。角色卡决定文学与扮演方式，已激活世界书决定人物和世界事实；只有 `references/runtime.json` 中 `state.enabled=true` 时才同时执行 `state-system` 的角色数值事务。用户的其他可见 Skills 仍可继续扩展工作流。

## 读取内容

1. `references/runtime.json`：当前套件 ID、交互状态文件路径和可选角色状态配置；启用交互时必须读取。
2. `assets/actions.json`：作者提供的基础行动；只在需要核对未知行动、生成回退行动或缺少标签时读取。
3. `assets/regions.json`：作者提供的地点/区域；只在需要核对未知地点、生成初始目标或缺少标签时读取。
4. `assets/map.svg`：可选界面地图。模型通常无需读取 SVG 内容。

区域可以用可选的 `characters` 列出最初可能在此出现的人物，供状态文件尚未建立时参考；它是场景入口，不是角色永远固定在该地点的硬规则。实际在场人物仍以当前剧情、世界书与持久状态为准。

界面会把当前选择作为本次 Agent 运行的私有隐式 prompt，不向聊天时间线写入协议消息：

```text
<tt_interaction_input version="1">{"action":{"id":"observe","label":"观察"},"target":{"type":"region","id":"start","label":"起始地点"}}</tt_interaction_input>
```

面板的自由输入使用同一协议，并增加 `custom_input`；这是玩家本轮行动原文，不需要拿 `custom` ID 查询基础行动表：

```text
<tt_interaction_input version="1">{"action":{"id":"custom","label":"自定义行动"},"target":null,"custom_input":"打开窗户查看街道"}</tt_interaction_input>
```

只执行本次 prompt 中最后一个 `<tt_interaction_input>`。聊天历史中若存在旧版 `[交互行动]`，它表示已经发生的历史行动，不得在本轮重放。不得在 Agent 过程叙述、`output/main.md` 或聊天正文中引用、转录或解释控制标签与 JSON。

扩展产生的预设标签已经按当前 `actions.json` 与 `regions.json` 校验，并同时携带 ID 和 label。此时直接采用标签内容，不要再次读取两个资源文件；`action.id=custom` 时直接执行 `custom_input`，也不读取基础行动表。只有其它标签字段缺失、ID 未知或需要生成回退列表时才读取对应资源。

## 权威状态与界面投影

交互状态文件默认是 `persist/interaction-state.json`。它是 Agent 维护、界面只读的投影；不要把扩展缓存或界面选中状态当成剧情真相。

最小结构：

```json
{
  "version": 1,
  "turn": 1,
  "summary": "当前局势的一句话摘要",
  "location": {"id": "start", "label": "起始地点"},
  "targets": [],
  "actions": [],
  "extensions": {}
}
```

- `targets` 可包含当前可交互的人物、地点、物品或作者自定义目标。
- `actions` 可覆盖本轮界面行动；为空或缺失时，界面回退到 `assets/actions.json`。
- `extensions` 是套件作者的扩展空间。可以加入地图状态、资源、旗标、任务或自定义面板数据。
- 对未知字段应尽量原样保留，避免阻止其他 Skill 或未来版本扩展。

当 `runtime.json.state.enabled=true` 时，界面会从其中声明的权威角色状态文件读取数值，并结合指定状态 Skill 的维度定义显示只读进度条；不要把同一角色数值重复复制到交互投影。没有角色状态维度时跳过这一步。其它需要展示的简报可写入 `extensions.briefing`：数值自动显示为进度条，文字、布尔和数组显示为文本。本模板当前不允许界面直接编辑这些值。

```json
{
  "extensions": {
    "briefing": [
      {"id": "garden_reputation", "label": "园中声望", "value": 42, "min": 0, "max": 100},
      {"id": "weather", "label": "天气", "value": "微雨"}
    ]
  }
}
```

推荐的目标与行动项：

```json
{
  "targets": [
    {
      "type": "character",
      "id": "example-character",
      "label": "示例人物",
      "description": "可选的界面短说明"
    }
  ],
  "actions": [
    {"id": "talk", "label": "交谈", "scope": "character", "confirm": false}
  ]
}
```

这些字段只为通用界面提供最低互操作性，不限制作者添加其它字段或使用不同题材。

## 回合事务

1. 每次运行在首个并行工具阶段直接读取 `persist/interaction-state.json`；启用角色状态时同时读取其权威状态文件。不要先列 workspace 目录只为确认文件存在。`Not found` 是正常首轮，不重试读取，直接应用场景、世界书和当前输入建立最小状态。
2. 读取玩家本轮普通输入或本次运行最后一个 `<tt_interaction_input>`，核对行动 ID 与当前目标；动态 `actions` 中的行动同样有效。
3. 按角色卡、已激活世界书、状态规则和其它可见 Skills 生成叙事。
4. 仅当 `runtime.json.state.enabled=true` 时，完成其中指定 `state-system` 要求的角色状态事务。
5. 把已经发生的结果投影到交互状态：递增 `turn`，更新简短 `summary`、当前位置、目标、下一轮可用行动和作者定义的可选 `extensions.briefing`。与角色状态和 `output/main.md` 在同一模型回合并行写入。
6. 写入前在内存中核对 JSON；只有写入报错或无法确认合并结果时才回读，禁止无条件回读刚写入的文件。
7. 下一模型回合立即调用 `workspace.commit` 发布 `output/main.md`，再调用 `workspace.finish`。交互扩展使用后台 presentation 隐藏 Agent 中间过程，但“后台可以无 commit 结束”不适用于本交互回合；每轮仍必须发布剧情正文。

### 有界快速路径

一次正常点击回合应按以下四个工具阶段完成，独立调用全部并行：

1. 直接读取角色卡指定的交互 Skill 根文件、固定短引用、交互状态文件与已激活世界书；若启用角色状态，同时读取指定状态 Skill、短引用及权威状态文件。全部并行，不先 list/search Skill 或列目录；状态文件 `Not found` 时直接初始化。已完整提供的点击标签不读取 actions/regions。
2. 并行写入必要的持久状态、交互投影和 `output/main.md`；无数值变化时不重写角色状态。
3. `workspace.commit`。
4. `workspace.finish`。

不得用普通 assistant 文本汇报内部进度。接近回合上限时，停止可选读取和校对：保持不确定的数值不变，完成交互投影、正文发布和 finish。

路径必须使用 `references/runtime.json` 中的精确值；默认文件名是 `interaction-state.json`（连字符），不是 `interaction_state.josn`。

如果玩家行动因剧情条件无法完成，应在叙事中自然反馈，并仍然给出合理的下一轮行动；不要悄悄替换成另一项选择。需要随机检定时可以按作品规则使用 `dice.roll`，但本 Skill 不强制随机性。

## 输出边界

- 正文保持文学叙事，不显示内部状态计算、工具协议或完整 JSON。
- 不显示 `<tt_interaction_input>`、`[交互行动]` 或其字段转录；只用自然叙事呈现行动结果。
- 界面只是输入和状态展示入口，不能覆盖角色卡、世界书或持久状态。
- 不要求玩家只能点击行动；普通文字输入始终是合法的自由行动。
- 不执行 Skill 内脚本，也不假定存在 MCP、extension tool bridge、流式 Agent 或回滚 API。
