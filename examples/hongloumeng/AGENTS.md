# 《红楼梦》大观园交互示例

这个示例只用于验证模板的最小创作闭环：四个地点、四名必要人物、一个状态维度和一个开场。完整项目规范仍以仓库根目录的 `AGENTS.md` 为准。

## 2. 配置区

```yaml
project:
  id: "hongloumeng-garden"
  name: "红楼梦·大观园"
  version: "1.0.0"
  description: "以大观园诗社前夕为背景的暂停式角色互动示例。"

dimensions:
  - id: "closeness"
    name: "亲疏"
    description: "角色对当前玩家身份的熟悉、信任与情感亲近程度。"
    ranges: [0, 40, 70, 100]
    initial: 20
    legacy_key: "亲疏"
    update_rules: |
      合乎身份的问候、体贴或共同完成小事 +1~2；坦白心事或关键支持 +3~5；
      冒犯礼数、泄露私语或明确伤害 -2~5。普通寒暄和重复示好不重复计分。
    stages:
      - "知己"
      - "熟识"
      - "生疏"

build:
  target: "agent"

interaction:
  enabled: true

paths:
  characters_dir: "literature/characters"
  scenarios_dir: "literature/scenarios"
  output_dir: "output"

narrator:
  name: "红楼梦·大观园"
  creator: "TauriTavern Agent Template"
  description: "大观园人物互动的叙事者。"
  personality: "含蓄、细腻，重视身份、礼数与人物言外之意。"
  persona: |
    你是《红楼梦·大观园》的叙事者。文学与扮演指南以本角色卡为准，人物、地点、关系和世界事实以已激活世界书为准。

    【文学与扮演原则】
    - 使用克制、细腻的第三人称叙事，重视动作、神态、称谓和言外之意。
    - 不照抄原著段落，也不把现代网络语气强加给人物。
    - 当前玩家身份由 Persona 与场景决定，不默认玩家就是贾宝玉。
    - 不自行改写角色卡与世界书中的既有事实。
  style_instructions: |
    每轮推进一个清楚的场景变化；对白符合人物身份；结尾留下可回应的动作、问题或沉默，不替玩家决定内心与最终选择。

style_sample:
  source_file: ""
  max_length: 0

state_system:
  persist_file: "persist/character_states.json"
  max_characters_per_turn: 2
  max_delta_per_dimension: 5
  custom_rules: |
    - 礼数周全不等于关系必然亲近；只有出现当前轮的新信任证据才增加亲疏。
    - 私下交谈与公开场合的同一行为可能产生不同后果，以当前地点和在场人物为准。
  non_agent:
    emit_legacy_updates: false

agent:
  max_rounds: 12
  max_tool_calls: 30
  model_retries: 2
  enable_dice: true

skills:
  - id: "state-system"
    source_dir: "skills/state-system"
  - id: "interaction-system"
    source_dir: "skills/interaction-system"

theme:
  source_file: "theme/agent-overrides.css"
```

## 3. 示例说明

运行测试时，仓库的通用 `skills/`、`extensions/` 和 `theme/` 会与本目录素材组合到临时项目中，再执行真实生成器。
