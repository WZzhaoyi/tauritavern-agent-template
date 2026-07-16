# TauriTavern Agent 同人小说生成系统

基于 [TauriTavern](https://tauritavern.github.io/)，从同一份创作源数据生成 Agent 或非 Agent 角色卡套件。

角色卡承载文学与扮演指南；传统世界书承载可复用角色、设定和背景。`build.target` 决定状态资料被编译到 Skill 还是传统状态世界书，两种构建生成不同的角色卡，不将一份产物同时兼容两种运行时。

套件作者可在 `dimensions[].update_rules` 与 `state_system.custom_rules` 中定义自己的数值规则。

Agent 构建遵循“扩展而非替代”：Profile 使用 `agentSystemPrompt: null` 继承 TauriTavern 按工具动态生成的默认运行协议；`skills.visible: ["*"]` 保留用户本地 Skills。Agent 角色卡只追加“每轮必读 `state-system`”的简短桥接指令，状态细节仍在 Skill 中。工具权限则按当前官方格式显式列出全部非委派内置工具，仅排除子 Agent，并保留可选骰子。

## 快速开始

```bash
pip install -r requirements.txt
```

1. 编辑 `AGENTS.md` 第 2 节配置区，设置 `build.target: "agent"` 或 `"non_agent"`，并填入作品与状态配置
2. 将文学与扮演指南写入角色卡；将角色、设定和背景维护在传统世界书
3. 在 `literature/characters/` 下创建状态阶段资料，在 `literature/scenarios/` 下创建开场剧本
4. 运行生成脚本：

```bash
python scripts/generate.py
```

5. 导入目标目录中的产物：

| 目标 | 输出 |
|------|------|
| `agent` | `output/agent/` 下的角色卡、Agent Profile、SKILLS 和可选主题 |
| `non_agent` | `output/non-agent/` 下的 legacy 角色卡和状态世界书 |

6. Agent 目标需将 Profile 设为 Active Profile 并开启 Agent Mode；非 Agent 目标需导入并绑定状态世界书，保持 Agent Mode 关闭

## 构建目标

| 目标 | 状态资料 | 更新方式 |
|------|---------|---------|
| `agent` | `_stages` 进入 `state-system.ttskill` | LLM 验证增量后写入 `persist/character_states.yaml` |
| `non_agent` | `_stages` 进入 `{project.id}.state-worldbook.json` | 角色卡输出 `_.set(...)`，由兼容状态脚本保存 |

未安装非 Agent 状态脚本时，角色卡和世界书仍能正常使用，但数值不会自动持久化。若不需要兼容输出，可将 `state_system.non_agent.emit_legacy_updates` 设为 `false`。

需要沿用原模板的自动状态运行时，可安装 `https://github.com/n0vi028/JS-Slash-Runner`，并启用 `import 'https://testingcf.jsdelivr.net/gh/WZzhaoyi/tavern_helper/dist/角色状态管理/index.js'`。这属于非 Agent 兼容依赖，不会被本模板打包。

Agent `persist/` 与 legacy 状态脚本是两个独立存储。共用源数据不等于产物或聊天进度可直接互换。

`AGENTS.md` 中的 `skills:` 清单只用于打包本项目随套件分发的 `.ttskill`，不是 Profile 的运行时白名单。

## 转换角色阶段数据格式

`_stages` 文件可在 JSON 与 YAML 之间批量转换：

```bash
python scripts/convert_stages_format.py yaml
python scripts/convert_stages_format.py json
```

## 项目结构

```
├── AGENTS.md         # 配置中心与完整文档
├── literature/       # 状态阶段资料、场景剧本、角色卡风格参考
├── skills/           # SKILLS 知识包（仅状态工作流）
├── theme/            # 前端美化 CSS（可选）
├── scripts/          # 生成脚本
└── output/
    ├── agent/        # Agent 目标产物
    └── non-agent/    # 非 Agent 目标产物
```

## 详细文档

完整的配置说明、工作流步骤和文件格式规范，请参阅 [AGENTS.md](AGENTS.md)。

## 参考

- [TauriTavern 官网](https://tauritavern.github.io/)
- [Agent 系统架构](https://tauritavern.github.io/architecture/agent.html)
- [Agent Profile 配置档案](https://tauritavern.github.io/agent/profiles.html)
- [SKILLS 知识包](https://tauritavern.github.io/agent/skills.html)
- [创作者适配指南](https://tauritavern.github.io/agent/creator-guide.html)

## 许可证

[MIT](LICENSE)
