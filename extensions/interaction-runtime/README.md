# 暂停式交互扩展

这是 `scripts/generate.py` 为当前角色卡套件生成的可选 UI 扩展。它不会替代 TauriTavern Agent、角色卡、世界书或用户的其他 Skills。

## 安装

TauriTavern 当前没有把第三方 UI Extension 嵌入角色卡或 `.ttskill` 的公开安装 API，因此交互扩展需要单独安装：

1. 开发或本地使用时，将整个扩展目录复制到当前用户的 SillyTavern/TauriTavern extensions 目录。
2. 套件发布时，建议把此目录作为一个独立 Git 仓库发布，再通过 Extensions → Install Extension 安装该仓库 URL。
3. 同时导入角色卡、Agent Profile 和 `skills/interaction-system.ttskill`。

安装后，只有带有当前 `projectId` 标记的角色卡会显示“行动”按钮。

## 作者自定义

不要直接在扩展代码中写剧情规则。回到项目源目录编辑：

- `interaction/actions.yaml`
- `interaction/regions.yaml`
- `interaction/map.svg`
- `skills/interaction-system/SKILL.md`（需要改变交互状态规则时）

然后重新运行 `python scripts/generate.py`。

扩展优先使用官方 `api.agent` 与 `api.skill`。`api.chat`、`api.worldInfo` 和移动布局契约存在时自动增强，不存在时相应功能会隐藏或退化，不会阻止 Agent 正常写作。
