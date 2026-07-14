---
name: state-system
description: 角色状态维度定义、阶段描述、计算规则与持久化方式。Agent 应在每次回复后更新角色状态。
---

# State System

## 使用时机
- 回复涉及角色关系变化时
- 读取 persist/ 中的当前状态值
- 回复完成后计算状态变化并写回 persist/

## 状态维度

维度定义参见 AGENTS.md 配置区的 `dimensions` 段。每个维度的 ranges 和 stages 决定了阶段划分。

## 持久化方式

当前状态数值保存在工作区 `persist/character_states.yaml` 中，格式如下：

```yaml
{角色名}:
  affection: 45
  corruption: 12
```

## 操作流程

1. **回复前**：读取 `persist/character_states.yaml`，获取各角色当前维度数值。
2. **查阅阶段描述**：根据数值落在哪个 range，对照 `_stages` 文件中对应阶段的 content，决定角色当前行为模式。
3. **回复后更新**：根据本轮互动内容，调整相关维度数值：
   - 正向互动：+1~5
   - 负面冲突：-1~5
   - 关键事件（告白/背叛等）：±5~10
   - 无交互的角色维持不变
4. **写回**：通过 `workspace.write_file` 将更新后的 YAML 写回 `persist/character_states.yaml`。

## 注意事项
- 单轮变动不宜过大，渐进积累更合理。
- 记录更新原因（如「回复中主动安慰→好感+2」），便于后续调试。
- 阶段边界值两侧的行为应有明显差异，避免相邻阶段雷同。
