# 暂停式交互扩展

这是一次安装即可服务多个项目的通用 UI 运行时：

- 根目录 `extensions/interaction-runtime/` 是框架源码。
- `projects/<project-id>/output/agent/extensions/tauritavern-interaction/` 是可安装副本。

请只安装生成后的扩展，不要直接安装或修改根目录模板。重新构建会覆盖生成目录。

## 安装

1. 构建项目：

   ```bash
   python scripts/generate.py projects/<project-id>
   ```

2. 将生成的扩展目录复制到 SillyTavern/TauriTavern 扩展目录；发布时也可以把该目录作为独立 Git 仓库安装。
3. 同时导入项目生成的角色卡和 Agent Profile；导入项目前缀命名的 `skills/*.ttskill` 时，把目标作用域设为该角色卡。不要导入到全局、预设或 Profile 作用域。

项目配置由角色卡的 `tauritavern_interaction` 标记提供，不写死在扩展中。多个项目共用同一扩展，切换角色卡时自动切换 Profile、角色作用域 Skill、状态路径与缓存命名空间。普通聊天输入和面板内的自定义行动输入始终可用。

## 项目自定义

在项目源目录维护声明式内容：

- `projects/<project-id>/interaction/actions.json`
- `projects/<project-id>/interaction/regions.json`
- `projects/<project-id>/interaction/map.svg`

只有需要改变通用交互工作流或 UI 逻辑时，才在项目中添加同路径覆盖：

- `projects/<project-id>/skills/interaction-system/SKILL.md`
- `projects/<project-id>/extensions/interaction-runtime/`

项目未提供覆盖时，生成器自动使用根目录的通用 Skill 和扩展运行时。

## 运行要点

- 地图元素的 `data-region-id` 必须对应 `regions.json` 中的区域 ID。
- Agent 成功提交后，扩展读取 `output/main.md` 和 `persist/interaction-state.json`；声明角色状态维度时再读取对应角色状态文件。
- 预设行动与面板自由输入使用同一回合流程；自由输入支持 `Ctrl/Cmd+Enter` 提交。
- 界面缓存只用于恢复展示，不替代 Agent workspace 中的权威文件。
