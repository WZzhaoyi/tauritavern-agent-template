---
name: world-lore
description: 世界观、势力、地点、物品与静态关系参考。Agent 应按当前场景需求选择性读取。
---

# World Lore

## 使用时机
- 场景转换到新地点时 → 查地点
- 涉及特定势力或组织时 → 查势力
- 需要确认角色间静态关系时 → 查关系
- 涉及特殊物品或概念时 → 查物品

## 注意事项
- 不要一次性全部读取，仅按当前场景需求加载。
- 角色个人信息应从 `character-profiles` SKILL 获取，不在此包中。
- 详细资料放在 `references/` 子目录下。

## 子文件索引

| 文件 | 内容 |
|------|------|
| `references/worldview.md` | 世界观总览 |
| `references/mechanics.md` | 核心机制 |
| `references/factions.md` | 势力与组织 |
| `references/locations.md` | 地点 |
| `references/items.md` | 物品与概念 |
| `references/relationships.md` | 静态关系网 |
