# How to release

1. 修改`pyproject.toml`中的`version`为新版本号
2. 执行以下命令提交修改

   ```bash
   git add pyproject.toml
   git commit -m "update version to <new version>"
   git tag -a <new version> -m "version <new version>"
   ```
