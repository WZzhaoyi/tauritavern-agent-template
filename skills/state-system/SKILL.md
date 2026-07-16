---
name: state-system
description: Agent Mode 下角色与剧情状态的读取、数值计算、校验和持久化事务协议。
---

# State System

## 使用时机

- 每次 Agent 写作运行开始时，检查当前持久状态。
- 当前轮出现可能改变角色关系、能力、剧情阶段或旗标的事件时。
- 回复完成前，验证并写回发生变化的状态。

本 Skill 只会被打包进 `build.target: agent` 产物。非 Agent 构建使用状态世界书与角色卡中的 legacy `_.set(...)` 协议。

本 Skill 是角色卡套件的状态扩展，不排斥用户本地的其他 Skills。其他 Skill 可扩展写作、校对或额外工作流，但不得覆盖本 Skill 的状态事务约束，也不得篡改角色卡或已激活世界书中的事实。

## 状态维度

先读取：

1. `references/update-policy.yaml`：状态文件路径、全局限制和用户自定义规则。
2. `references/dimensions.yaml`：维度 ID、范围、初始值、阶段和每维度更新规则。
3. 需要判断阶段行为时，再读取 `references/character-stages/` 中对应角色文件。

角色的阶段行为资料位于 `references/character-stages/`，文件名为 `{角色名}_stages.{json|yaml}`。

这些文件只维护当前聊天的动态状态。角色核心性格、背景、地点、势力和静态关系以角色卡与本轮已激活世界书为准。

## 持久化方式

状态文件路径以 `references/update-policy.yaml` 的 `persist_file` 为准，默认是 `persist/character_states.yaml`。建议格式：

```yaml
version: 1
turn: 12
characters:
  角色名:
    affection: 45
    corruption: 12
plot:
  flags: {}
last_update:
  summary: "角色名主动坦白秘密，affection +2"
```

## 初始化

- 如果状态文件存在，以文件中的值为唯一旧值来源。
- 如果状态文件不存在，优先从聊天中的 `<agent_state_init>` YAML 块读取场景初始值。
- 某维度没有场景初始值时，使用 `dimensions.yaml` 中该维度的 `initial`。
- 不得从角色语气、阶段描述或历史印象反推一个未经记录的旧值。

## 更新事务

严格按以下顺序执行：

1. **读取**：读取状态文件、更新策略、维度定义和本轮相关的阶段资料。
2. **取证**：只检查当前一轮新发生的台词、动作、选择和明确剧情事件，不重复计算历史。
3. **提出变更**：内部为每项变化形成 `character / dimension / old / delta / new / evidence`。
4. **逐项校验**：
   - 角色必须在当前轮有实际参与或明确受到事件影响。
   - 维度必须存在于 `dimensions.yaml`。
   - `delta` 必须满足维度规则、用户自定义规则和全局绝对值上限。
   - 必须选择一个不会越界的有效 `delta`，满足 `new = old + delta`；接近边界时缩小增量，不能先越界再保留错误的 delta。
   - 没有新进展时保持原值，不为“每轮都要更新”而制造变化。
5. **写回**：只修改通过校验的字段，同时更新 `turn` 和简短的 `last_update`；没有变化时可以只写正文，不重写状态文件。
6. **复核**：重新读取状态文件，核对 YAML 可读、未丢失未修改字段、所有新值在范围内。
7. **完成状态事务**：复核通过后返回 TauriTavern 默认 Agent 运行流程完成正文发布与收尾；本 Skill 不重新定义通用提交协议。

## Agent Mode 输出边界

- 不要在 `output/main.md` 中输出 `_.set(...)`、`<agent_state_init>` 或状态计算过程。
- legacy 更新块只属于非 Agent 模式；Agent Mode 直接写 `persist/`。
- `persist/` 保存结果和简短依据，不保存隐藏思维过程或长篇分析。

## 注意事项

- LLM 是状态规则的执行者，不是确定性计算器；必须通过旧值、增量、新值和回读校验降低算错风险。
- 用户在 `update-policy.yaml` 和 `dimensions.yaml` 中生成的自定义规则优先于本文件的通用建议，但不能绕过数值范围与文件安全边界。
- 单轮变化应渐进；关键事件是否允许较大变化，以用户配置为准。
- 不要用状态资料覆盖角色卡或世界书的既有设定。
