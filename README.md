# TauriTavern Agent 角色卡套件模板

从同一份创作源数据构建 Agent 或非 Agent 角色卡套件。具体作品统一放在 `projects/<project-id>/`，根目录保留模板代码和通用资源。

## 快速开始

环境要求：Python 3.11。

```bash
pip install -r requirements.txt
```

1. 参考 `projects/hongloumeng/` 创建项目目录。
2. 将 `tauritavern.template.yaml` 复制为项目中的 `tauritavern.yaml` 并填写配置。
3. 编辑项目的 `AGENTS.md`、`literature/`、`lorebooks/` 和 `interaction/`。
4. 构建：

```bash
python scripts/generate.py projects/<project-id>
```

产物位于项目自己的 `output/`：

| `build.target` | 输出目录 | 主要产物 |
|---|---|---|
| `agent` | `output/agent/` | 角色卡、Agent Profile、Skills、可选交互扩展 |
| `non_agent` | `output/non-agent/` | 角色卡、状态世界书 |

两种目标的运行时状态互不兼容，不要在同一聊天中直接互换。

## 导入

Agent 目标：

1. 导入 `*.character-card.json`。
2. 导入 `skills/*.ttskill`。
3. 导入并启用 `*.agent-profile.json`。
4. 开启 Agent Mode。
5. 如启用交互，按生成扩展目录中的 `README.md` 安装 UI Extension。
6. 导入并绑定 `lorebooks/` 中的世界书。

非 Agent 目标：

1. 导入角色卡和 `*.state-worldbook.json`。
2. 绑定状态世界书，保持 Agent Mode 关闭。
3. 如需自动保存状态，安装兼容 `_.set(...)` 的状态运行时；否则设置 `emit_legacy_updates: false`。

## 项目内容

```text
projects/<project-id>/
├── AGENTS.md
├── tauritavern.yaml
├── literature/
│   ├── characters/
│   ├── scenarios/
│   └── fanfic/
├── lorebooks/
├── interaction/
├── skills/           # 可选项目 Skill 或覆盖
├── extensions/       # 可选项目扩展覆盖
├── theme/            # 可选项目主题覆盖
└── output/
```

- `AGENTS.md`：项目维护与创作指南。
- `tauritavern.yaml`：构建配置。
- `literature/characters/`：角色状态阶段资料。
- `literature/scenarios/`：首条消息和备选开场。
- `lorebooks/`：角色、地点、关系和世界事实。
- `interaction/`：行动、区域和可选 SVG 地图。
- `skills/`、`extensions/`、`theme/`：仅在项目需要独有能力时使用；默认继承根目录通用资源。

配置字段和默认值见 [tauritavern.template.yaml](tauritavern.template.yaml)，完整创作约束见 [AGENTS.md](AGENTS.md)。

## 模板更新

下游仓库每周检查源模板并创建同步 PR，不自动合并。首次使用前需在 GitHub 的 **Settings → Actions → General → Workflow permissions** 中允许 Actions 创建 Pull Request。

- `projects/` 和 `.github/workflows/` 不参与模板同步。
- 手动运行 **Sync template** 时默认是 dry-run。
- 同步后项目 `framework.version` 必须与模板一致。
- 已有下游仓库需一次性复制同步工作流、`.templatesyncignore` 和 Dependabot 配置。

## 测试与发布

```bash
python -m unittest discover -s tests -v
node --check extensions/interaction-runtime/index.js
```

发布 tag 必须为 `vMAJOR.MINOR.PATCH`，并与模板中的 `framework.version` 一致。Release 会在测试通过后创建。

## 参考

- [TauriTavern](https://tauritavern.github.io/)
- [Agent 创作者指南](https://tauritavern.github.io/agent/creator-guide.html)
- [Agent Profile](https://tauritavern.github.io/agent/profiles.html)
- [Skills](https://tauritavern.github.io/agent/skills.html)

## 许可证

[MIT](LICENSE)
