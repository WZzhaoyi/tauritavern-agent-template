# 暂停式交互扩展

这是 `scripts/generate.py` 为当前角色卡套件生成的可选 UI 扩展。它不会替代 TauriTavern Agent、角色卡、世界书或用户的其他 Skills。

## 安装

TauriTavern 当前没有把第三方 UI Extension 嵌入角色卡或 `.ttskill` 的公开安装 API，因此交互扩展需要单独安装：

1. 开发或本地使用时，将整个扩展目录复制到当前用户的 SillyTavern/TauriTavern extensions 目录。
2. 套件发布时，建议把此目录作为一个独立 Git 仓库发布，再通过 Extensions → Install Extension 安装该仓库 URL。
3. 同时导入角色卡、Agent Profile 和 `skills/interaction-system.ttskill`。

安装后，只有带有当前 `projectId` 标记的角色卡会显示“行动”按钮。

安装后的悬浮入口会打开全屏地图/行动界面。点击行动后，扩展通过 Agent Host API 的隐式 `quiet_prompt` 传入私有 `<tt_interaction_input>`，并直接启动后台回合。控制协议不会出现在聊天正文或 Agent 中间过程，也不需要再点聊天的发送按钮。扩展会显示运行阶段和耗时，并检查 Agent 是否真正发布了剧情。

如果仍看到可见的 `[交互行动]`，表示它来自旧聊天历史或旧版扩展。请替换整个扩展目录、重新导入 `interaction-system.ttskill`，并完全重启 TauriTavern。新 Skill 会将历史中的旧协议视为已发生行动，不在本轮重放。

## 作者自定义

不要直接在扩展代码中写剧情规则。回到项目源目录编辑：

- `interaction/actions.json`
- `interaction/regions.json`
- `interaction/map.svg`
- `skills/interaction-system/SKILL.md`（需要改变交互状态规则时）

然后重新运行 `python scripts/generate.py`。

扩展优先使用官方 `api.agent` 与 `api.skill`。`api.chat`、`api.worldInfo` 和移动布局契约存在时自动增强，不存在时相应功能会隐藏或退化，不会阻止 Agent 正常写作。

交互资源与界面投影均为 JSON，扩展仅使用浏览器原生 `JSON.parse()`，不需要 SillyTavern/TauriTavern 提供 YAML 或其它解析库。
