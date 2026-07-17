# 具体项目

每个子目录是一套独立作品，只维护项目拥有的配置与创作内容：

- `AGENTS.md`：项目维护与创作指南。
- `tauritavern.yaml`：项目构建配置和框架版本声明。
- `literature/`、`lorebooks/`、`interaction/`：项目源数据。
- 项目专有的 Skills、扩展或主题按需添加；缺少的通用资源由仓库根目录的模板提供。

不要把根目录的生成器、通用 Skills 或交互运行时复制进项目。更新模板代码后重新构建，项目会自动使用当前框架资源：

```bash
python scripts/generate.py projects/<project-id>
```

`hongloumeng/` 同时作为最小完整项目和回归测试夹具。
