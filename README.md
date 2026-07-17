# TauriTavern Agent 角色卡套件模板

基于 [TauriTavern](https://tauritavern.github.io/) 的角色卡套件构建模板，适用于同人小说、互动叙事和多角色扮演项目。它从同一份创作源数据生成 Agent 或非 Agent 目标产物。

角色卡承载文学与扮演指南；传统世界书承载可复用角色、设定和背景。`build.target` 决定状态资料被编译到 Skill 还是传统状态世界书，两种构建生成不同的角色卡，不将一份产物同时兼容两种运行时。

套件作者可在 `dimensions[].update_rules` 与 `state_system.custom_rules` 中定义自己的数值规则。

Agent 构建遵循“扩展而非替代”：Profile 使用 `agentSystemPrompt: null` 继承 TauriTavern 按工具动态生成的默认运行协议；`skills.visible: ["*"]` 保留用户本地 Skills。角色卡只加入状态与可选交互工作流的桥接说明，具体规则仍由 Skills、角色卡和世界书共同提供。

可选的暂停式交互层提供地图、行动、剧情正文和只读状态简报。普通布局使用全屏舞台；SillyTavern 视觉小说模式下自动停靠到上方舞台并保留下方聊天区。普通文字输入始终可用。模板只提供最低互操作协议，不预设题材、资源体系或胜负规则。

## 从模板创建项目

在 GitHub 仓库页面选择 **Use this template → Create a new repository**，然后克隆新仓库。也可以直接复制本仓库并删除原有 Git 历史。

具体作品统一放在 `projects/<project-id>/`。用户只修改项目子目录；根目录的生成器、通用 Skills、扩展运行时和默认主题保持由模板更新。根目录的 `tauritavern.template.yaml` 是新项目配置模板，可以参考 `projects/hongloumeng/` 创建完整项目目录。

## 模板更新

由本模板创建的下游仓库会每周检查 `WZzhaoyi/tauritavern-agent-template`，发现框架更新时创建 Pull Request，不会直接修改默认分支或自动合并。同步只处理框架拥有的文件，以下路径始终保留当前仓库版本：

- `projects/`：具体项目配置、素材和项目专有代码。
- `output/`：生成产物。
- `.github/workflows/`：涉及仓库写权限，使用默认 `GITHUB_TOKEN` 时不自动同步。

首次使用前，在下游仓库的 **Settings → Actions → General → Workflow permissions** 中允许 GitHub Actions 创建 Pull Request。也可以在 Actions 页手动运行 **Sync template**；手动触发默认是 dry-run，取消 `dry_run` 才会创建同步 PR。同步 PR 必须经过 CI 和人工审查后再合并。

同步使用 `.github/.templatesyncignore` 保护项目目录，且不强制删除下游文件。工作流自身的逻辑更新需要人工同步；这样无需向模板同步任务授予 PAT 的 `workflow` 权限。工作流引用的 Actions 已固定到完整 commit SHA，并由 Dependabot 在每个仓库中独立创建依赖更新 PR。

已有的下游仓库需要一次性复制 `.github/workflows/sync-template.yml`、`.github/.templatesyncignore` 和 `.github/dependabot.yml`，之后才能自动收到框架同步 PR。同步更新框架后，生成器会比较项目 `framework.version` 与根模板版本；不一致时停止构建，要求先检查迁移内容并显式更新项目配置。

## 快速开始

```bash
pip install -r requirements.txt
```

生成器使用 Python 3.11 测试；运行时资源全部为 JSON、SVG、JavaScript 和 CSS。Python 侧使用 `PyYAML` 读取独立的 `tauritavern.yaml` 和场景 Markdown frontmatter。`AGENTS.md` 只作为项目维护与创作指南，不再作为机器配置来源。

1. 在 `projects/<project-id>/` 创建项目，并编辑其中的 `tauritavern.yaml`；设置 `build.target: "agent"` 或 `"non_agent"`，Agent 目标可用 `interaction.enabled` 开关点击交互
2. 将文学与扮演指南写入项目角色卡配置；将角色、设定和背景维护在项目的传统世界书
3. 在项目的 `literature/characters/` 下创建状态阶段资料，在 `literature/scenarios/` 下创建开场剧本
4. 运行生成脚本：

```bash
python scripts/generate.py projects/<project-id>
```

5. 导入目标目录中的产物：

| 目标 | 输出 |
|------|------|
| `agent` | `output/agent/` 下的角色卡、Agent Profile、SKILLS、可选交互扩展和主题 |
| `non_agent` | `output/non-agent/` 下的 legacy 角色卡和状态世界书 |

6. Agent 目标需将 Profile 设为 Active Profile 并开启 Agent Mode；非 Agent 目标需导入并绑定状态世界书，保持 Agent Mode 关闭

启用交互后，还需按 `output/agent/extensions/{project.id}-interaction/README.md` 安装 UI Extension。官方当前不提供随角色卡或 Skill 自动安装第三方扩展的公开 API，因此这一步保留用户确认；不安装扩展不会影响普通文字 Agent 使用。

## 暂停式交互

套件作者通常只需要编辑：

```text
interaction/
├── actions.json    # 基础行动；Agent 可在每轮状态中动态覆盖
├── regions.json    # 地点与区域
└── map.svg         # 可选地图，使用 data-region-id 标记点击区域
```

点击行动后，扩展通过官方 Agent Host API 直接启动回合，不会在聊天中留下可见的控制协议，也不需要再点发送按钮。Agent 成功提交后，界面从 `output/main.md`、`persist/character_states.json` 和 `persist/interaction-state.json` 刷新剧情、角色数值和交互状态。交互资源与持久状态均使用 JSON，前端不依赖外部 YAML 解析器。

## 项目与测试

[《红楼梦》大观园项目](projects/hongloumeng/README.md)提供四个地点、四名必要人物、五项基础行动、一个开场和一份最小世界书。`projects/` 聚合用户自定义内容，根目录保留可统一更新的模板代码；该项目同时也是跨文件一致性和真实 Agent 构建测试：

```bash
python scripts/generate.py projects/hongloumeng
python -m unittest discover -s tests -v
```

测试会构建默认模板和《红楼梦》项目，校验 SVG 区域、角色阶段资料、世界书与生成产物的一致性，并防止通用运行时意外引入项目专有内容。

## 构建目标

| 目标 | 状态资料 | 更新方式 |
|------|---------|---------|
| `agent` | `_stages.json` 进入 `state-system.ttskill` | LLM 验证增量后写入 `persist/character_states.json` |
| `non_agent` | `_stages.json` 进入 `{project.id}.state-worldbook.json` | 角色卡输出 `_.set(...)`，由兼容状态脚本保存 |

未安装非 Agent 状态脚本时，角色卡和世界书仍能正常使用，但数值不会自动持久化。若不需要兼容输出，可将 `state_system.non_agent.emit_legacy_updates` 设为 `false`。

需要沿用原模板的自动状态运行时，可安装 `https://github.com/n0vi028/JS-Slash-Runner`，并启用 `import 'https://testingcf.jsdelivr.net/gh/WZzhaoyi/tavern_helper/dist/角色状态管理/index.js'`。这属于非 Agent 兼容依赖，不会被本模板打包。

Agent `persist/` 与 legacy 状态脚本是两个独立存储。共用源数据不等于产物或聊天进度可直接互换。

`tauritavern.yaml` 中的 `skills:` 清单只用于打包本项目随套件分发的 `.ttskill`，不是 Profile 的运行时白名单。

## 项目结构

```
├── AGENTS.md         # 项目维护与创作指南
├── tauritavern.template.yaml # 新项目配置模板
├── literature/       # 状态阶段资料、场景剧本、角色卡风格参考
├── lorebooks/        # 可选的传统世界书
├── skills/           # 状态与可选交互协议 Skills
├── interaction/      # 作者维护的声明式地图、区域和行动
├── extensions/       # 通用交互 UI 运行时
├── projects/         # 用户拥有的具体项目，自定义内容集中在各项目子目录
├── tests/            # 项目构建与跨文件一致性测试
├── theme/            # 前端美化 CSS（可选）
├── scripts/          # 生成脚本
└── output/
    ├── agent/        # Agent 目标产物
    └── non-agent/    # 非 Agent 目标产物
```

## 详细文档

配置字段和默认值请参阅根目录的 [tauritavern.template.yaml](tauritavern.template.yaml)；具体项目应维护自己的 `tauritavern.yaml`。工作流步骤和文件格式规范请参阅 [AGENTS.md](AGENTS.md)。

Agent 目标需要所选 LLM API 稳定支持原生工具调用。状态只根据当前回合的明确证据更新；数值证据不足时保持不变。

交互界面会在 SillyTavern 视觉小说模式下自动停靠到上方舞台，保留下方聊天区。成功提交的 `output/main.md` 可直接在舞台中阅读；角色数值按维度显示为只读进度条，其它作者简报变量显示为文字或进度条。所有展示均来自成功 Agent run 与聊天级缓存，不创建第二套权威状态。

## 参考

- [TauriTavern 官网](https://tauritavern.github.io/)
- [Agent 系统架构](https://tauritavern.github.io/architecture/agent.html)
- [Agent Profile 配置档案](https://tauritavern.github.io/agent/profiles.html)
- [SKILLS 知识包](https://tauritavern.github.io/agent/skills.html)
- [创作者适配指南](https://tauritavern.github.io/agent/creator-guide.html)
- [Agent API](https://tauritavern.github.io/api/agent.html)
- [Skill API](https://tauritavern.github.io/api/skill.html)
- [扩展作者指南](https://tauritavern.github.io/agent/extension-authors.html)

## 许可证

[MIT](LICENSE)
