# 暂停式交互扩展

本说明随通用 UI 运行时一起复制：

- 根目录 `extensions/interaction-runtime/` 是框架源码。
- `projects/<project-id>/output/agent/extensions/<project-id>-interaction/` 是注入项目配置后的可安装扩展。

请只安装生成后的扩展，不要直接安装或修改根目录模板。重新构建会覆盖生成目录。

## 安装

1. 构建项目：

   ```bash
   python scripts/generate.py projects/<project-id>
   ```

2. 将生成的扩展目录复制到 SillyTavern/TauriTavern 扩展目录；发布时也可以把该目录作为独立 Git 仓库安装。
3. 同时导入项目生成的角色卡、Agent Profile 和 `skills/interaction-system.ttskill`。

只有带有对应 `projectId` 标记的角色卡会显示交互入口。普通文字输入始终可用。

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
- Agent 成功提交后，扩展读取 `output/main.md`、`persist/character_states.json` 和 `persist/interaction-state.json`。
- 界面缓存只用于恢复展示，不替代 Agent workspace 中的权威文件。
- 若聊天中仍出现可见的 `[交互行动]`，替换旧扩展和 Skill 后完全重启 TauriTavern。
