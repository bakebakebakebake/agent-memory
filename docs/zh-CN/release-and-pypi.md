# 发布与 PyPI 指南

[English](../release-and-pypi.md) | [简体中文](release-and-pypi.md)

本文说明 `agent-memory` 当前的发布流程。

## 命名约定

- GitHub 仓库：`agent-memory`
- Python import：`agent_memory`
- CLI 命令：`agent-memory`
- PyPI 分发名：`agent-memory-engine`

## 当前已发布版本

- GitHub Release：`v0.1.0`
- GitHub Release：`v0.1.1`
- PyPI：`agent-memory-engine==0.1.1`

## 发布检查清单

1. 更新 `pyproject.toml` 中的版本号
2. 更新 `CHANGELOG.md`
3. 本地验证：

   ```bash
   .venv/bin/python -m pytest -q
   .venv/bin/python -m build
   ```

4. 提交并推送到 `main`
5. 创建 git tag：

   ```bash
   git tag v0.1.2
   git push origin v0.1.2
   ```

6. 基于 tag 创建 GitHub Release，并上传 `dist/` 中的产物
7. 将同一批产物发布到 PyPI

## 构建产物

本地构建：

```bash
python -m build
```

预期输出：

- `dist/agent_memory_engine-<version>-py3-none-any.whl`
- `dist/agent_memory_engine-<version>.tar.gz`

## 发布到 PyPI

配置好 API Token 后：

```bash
python -m pip install --upgrade twine
python -m twine upload dist/*
```

推荐验证：

```bash
pip install --upgrade agent-memory-engine
python -c "import agent_memory; print(agent_memory.__version__)"
agent-memory --help
```

## GitHub Actions

当前 CI 会验证：

- Python `3.10`、`3.11`、`3.12`
- `pytest`
- `python -m build`

工作流文件：

- `.github/workflows/ci.yml`

## 发布卫生检查

发布前建议确认：

- GitHub Release 附件名称为 `agent_memory_engine-*`
- `pyproject.toml` 指向正确 GitHub 仓库
- `README.md` 使用 `pip install agent-memory-engine`
- `CHANGELOG.md` 已添加新版本说明

## 后续可升级项

- 为 PyPI 增加 trusted publishing
- 增加只针对 tag 的 release workflow
- 从 `CHANGELOG.md` 自动生成 release notes
- 为 wheel 和 sdist 生成校验和
