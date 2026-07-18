# 暂停式交互扩展

这是一次安装即可服务多个项目的通用 UI 运行时。项目构建不会复制它。

## 安装

1. 将模板根目录 `extensions/interaction-runtime/` 安装到 SillyTavern/TauriTavern。
2. 后续项目只需导入角色卡、Agent Profile 和角色作用域 Skills，无需重复安装扩展。

项目配置由角色卡的 `tauritavern_interaction` 标记提供，不写死在扩展中。多个项目共用同一扩展，切换角色卡时自动切换 Profile、角色作用域 Skill、状态路径与缓存命名空间。普通聊天输入和面板内的自定义行动输入始终可用。

## 项目自定义

在项目源目录维护声明式内容：

- `projects/<project-id>/interaction/actions.json`
- `projects/<project-id>/interaction/regions.json`
- `projects/<project-id>/interaction/map.svg`

只有需要改变交互工作流时，才在项目中覆盖：

- `projects/<project-id>/skills/interaction-system/SKILL.md`

通用 UI 逻辑只在根目录 `extensions/interaction-runtime/` 维护。

## 运行要点

- 地图元素的 `data-region-id` 必须对应 `regions.json` 中的区域 ID。
- Agent 成功提交后，扩展读取 `output/main.md` 和 `persist/interaction-state.json`；声明角色状态维度时再读取对应角色状态文件。
- “本轮设定”按正文对应的 Agent `runId` 读取 `input/prompt_snapshot.json` 中的 `worldInfoActivation`；不使用普通生成流程的全局最近激活记录代替本轮快照。
- 预设行动与面板自由输入使用同一回合流程；自由输入支持 `Ctrl/Cmd+Enter` 提交。
- 成功回合可在面板顶部选择“重跑上一回合”。它使用宿主的 `regenerate` 流程替换上一条回复，不会在已推进状态上将行动再执行一次。
- 界面缓存只用于恢复展示，不替代 Agent workspace 中的权威文件。
