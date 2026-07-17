# 《红楼梦》大观园交互项目

这个项目用于验证模板的最小创作闭环：四个地点、四名必要人物、一个状态维度和一个开场。框架规范仍以仓库根目录的 `AGENTS.md` 为准。

## 项目维护指南

- 构建配置只修改本目录的 `tauritavern.yaml`，不要修改根目录配置模板。
- 人物、地点与关系事实以 `lorebooks/` 为准；状态阶段表现以 `literature/characters/` 为准。
- 地图中的 `data-region-id` 必须与 `interaction/regions.json` 的区域 ID 一致。
- 场景保持第三人称、含蓄克制，不默认玩家身份为贾宝玉。
- 本示例使用通用 `interaction-system` 行动策略，不维护项目覆盖；动态 `actions` 为空时回退到 `interaction/actions.json`。
- 本项目只维护作品配置与素材；通用 Skills 和主题从模板框架继承，交互扩展从模板根目录独立安装。

## 验证

运行测试时，仓库的通用 `skills/` 和 `theme/` 会与本目录素材组合到临时目录中，再执行真实生成器。
