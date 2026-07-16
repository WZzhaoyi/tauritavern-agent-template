# TauriTavern Agent 同人小说生成系统

基于 [TauriTavern](https://tauritavern.github.io/)，从同一份创作源数据生成 Agent 或非 Agent 角色卡套件。

角色卡承载文学与扮演指南；传统世界书承载可复用角色、设定和背景。`build.target` 决定状态资料被编译到 Skill 还是传统状态世界书，两种构建生成不同的角色卡，不将一份产物同时兼容两种运行时。

套件作者可在 `dimensions[].update_rules` 与 `state_system.custom_rules` 中定义自己的数值规则。

Agent 构建遵循“扩展而非替代”：Profile 使用 `agentSystemPrompt: null` 继承 TauriTavern 按工具动态生成的默认运行协议；`skills.visible: ["*"]` 保留用户本地 Skills。Agent 角色卡只追加“每轮必读 `state-system`”的简短桥接指令，状态细节仍在 Skill 中。工具权限则按当前官方格式显式列出全部非委派内置工具，仅排除子 Agent，并保留可选骰子。

可选的暂停式交互层提供安全区悬浮入口和全屏游戏式地图/行动界面，普通文字输入仍然保留。模板只提供通用运行时和最低数据协议，不预设题材、资源体系或胜负规则；套件作者通过 `interaction/`、世界书和 Skills 定义自己的玩法。

## 快速开始

```bash
pip install -r requirements.txt
```

1. 编辑 `AGENTS.md` 第 2 节配置区，设置 `build.target: "agent"` 或 `"non_agent"`，并填入作品与状态配置；Agent 目标可用 `interaction.enabled` 开关点击交互
2. 将文学与扮演指南写入角色卡；将角色、设定和背景维护在传统世界书
3. 在 `literature/characters/` 下创建状态阶段资料，在 `literature/scenarios/` 下创建开场剧本
4. 运行生成脚本：

```bash
python scripts/generate.py
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

运行时使用官方 `api.agent.startRunFromLegacyGenerate()` 启动后台回合，并通过 `generateOptions.quiet_prompt` 把私有 `<tt_interaction_input>` 仅注入本次 prompt snapshot：不生成可见协议楼层，不需要再点聊天发送按钮，也不展示 Agent 中间叙述。扩展通过 `api.agent.subscribe()` 自行显示阶段、耗时、取消和错误，并确认 Agent 已用 `workspace.commit` 发布剧情；完成后读取 `persist/interaction-state.json`。交互资源和持久投影均为 JSON，扩展只使用浏览器原生 `JSON.parse()`，不依赖宿主或第三方解析器。

## 示例与测试

[《红楼梦》大观园最小示例](examples/hongloumeng/README.md)提供四个地点、四名必要人物、五项基础行动、一个开场和一份最小世界书。它不会进入默认生成产物，同时也是跨文件一致性和真实 Agent 构建测试：

```bash
python scripts/generate.py examples/hongloumeng
python -m unittest discover -s tests -v
```

测试会确认 SVG 区域、`regions.json`、角色阶段资料和世界书互相对应，并在临时目录中执行真实 `AgentGenerator`。

## 构建目标

| 目标 | 状态资料 | 更新方式 |
|------|---------|---------|
| `agent` | `_stages` 进入 `state-system.ttskill` | LLM 验证增量后写入 `persist/character_states.json` |
| `non_agent` | `_stages` 进入 `{project.id}.state-worldbook.json` | 角色卡输出 `_.set(...)`，由兼容状态脚本保存 |

未安装非 Agent 状态脚本时，角色卡和世界书仍能正常使用，但数值不会自动持久化。若不需要兼容输出，可将 `state_system.non_agent.emit_legacy_updates` 设为 `false`。

需要沿用原模板的自动状态运行时，可安装 `https://github.com/n0vi028/JS-Slash-Runner`，并启用 `import 'https://testingcf.jsdelivr.net/gh/WZzhaoyi/tavern_helper/dist/角色状态管理/index.js'`。这属于非 Agent 兼容依赖，不会被本模板打包。

Agent `persist/` 与 legacy 状态脚本是两个独立存储。共用源数据不等于产物或聊天进度可直接互换。

`AGENTS.md` 中的 `skills:` 清单只用于打包本项目随套件分发的 `.ttskill`，不是 Profile 的运行时白名单。

## 项目结构

```
├── AGENTS.md         # 配置中心与完整文档
├── literature/       # 状态阶段资料、场景剧本、角色卡风格参考
├── skills/           # 状态与可选交互协议 Skills
├── interaction/      # 作者维护的声明式地图、区域和行动
├── extensions/       # 通用交互 UI 运行时
├── examples/         # 不进入默认产物的完整创作示例
├── tests/            # 示例构建与跨文件一致性测试
├── theme/            # 前端美化 CSS（可选）
├── scripts/          # 生成脚本
└── output/
    ├── agent/        # Agent 目标产物
    └── non-agent/    # 非 Agent 目标产物
```

## 详细文档

完整的配置说明、工作流步骤和文件格式规范，请参阅 [AGENTS.md](AGENTS.md)。

Agent 交互采用有界快速事务：同阶段并行读取/写入，不重复遍历资料；普通移动不加载全部角色阶段，数值证据不足时保持状态不变并优先提交正文。运行仍要求所选 LLM API 稳定支持原生工具调用；`Upstream request failed` 属于提供商连接错误，应更换 API 后重试。

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
