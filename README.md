# TauriTavern Agent 同人小说生成系统

基于 [TauriTavern](https://tauritavern.github.io/) Agent 模式，为同人小说创作生成成套配置：Agent 配置档案、SKILLS 知识包、角色卡和前端美化。

## 快速开始

```bash
pip install -r requirements.txt
```

1. 编辑 `AGENTS.md` 第 2 节配置区，填入作品名、状态维度等
2. 在 `literature/` 下创建角色档案和场景剧本
3. 在 `skills/` 下按模板填充写作风格、状态系统、视角、世界观和角色设定
4. 运行生成脚本：

```bash
python scripts/generate.py
```

5. 将 `output/` 下生成的文件导入 TauriTavern：

| 文件 | 导入方式 |
|------|---------|
| `{作品名}角色卡.json` | Characters → Import |
| `{作品名}.agent-profile.json` | Agent 系统面板 → 配置档案 → 导入 |
| `{作品名}.ttskill` | Agent 系统面板 → SKILLS → 导入 |

6. 将 Agent Profile 设为 Active Profile，开启 Agent Mode 即可开始创作

## 转换角色阶段数据格式

`_stages` 文件可在 JSON 与 YAML 之间批量转换：

```bash
python scripts/convert_stages_format.py yaml
python scripts/convert_stages_format.py json
```

## 项目结构

```
├── AGENTS.md         # 配置中心与完整文档
├── literature/       # 角色档案、场景剧本、风格参考
├── skills/           # SKILLS 知识包（写作风格、状态系统、视角、世界观、角色设定）
├── theme/            # 前端美化 CSS（可选）
├── scripts/          # 生成脚本
└── output/           # 生成产物
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
