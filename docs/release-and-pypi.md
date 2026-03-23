# Release and PyPI Guide

[English](release-and-pypi.md) | [简体中文](zh-CN/release-and-pypi.md)

This document describes the current release process for `agent-memory`.

## Naming

- GitHub repository: `agent-memory`
- Python package import: `agent_memory`
- CLI command: `agent-memory`
- PyPI distribution: `agent-memory-engine`

## Current published versions

- GitHub Release: `v0.1.0`
- GitHub Release: `v0.1.1`
- PyPI package: `agent-memory-engine==0.1.1`

## Release checklist

1. Update the version in `pyproject.toml`
2. Update `CHANGELOG.md`
3. Run local validation:

   ```bash
   .venv/bin/python -m pytest -q
   .venv/bin/python -m build
   ```

4. Commit and push to `main`
5. Create a Git tag:

   ```bash
   git tag v0.1.2
   git push origin v0.1.2
   ```

6. Create the GitHub Release from the tag and upload the artifacts in `dist/`
7. Publish the same artifacts to PyPI

## Build artifacts

Build locally with:

```bash
python -m build
```

Expected output:

- `dist/agent_memory_engine-<version>-py3-none-any.whl`
- `dist/agent_memory_engine-<version>.tar.gz`

## PyPI publishing

After logging in to PyPI and configuring an API token:

```bash
python -m pip install --upgrade twine
python -m twine upload dist/*
```

Recommended verification steps:

```bash
pip install --upgrade agent-memory-engine
python -c "import agent_memory; print(agent_memory.__version__)"
agent-memory --help
```

## GitHub Actions

The CI workflow currently validates:

- install on Python `3.10`, `3.11`, `3.12`
- test suite with `pytest`
- package build with `python -m build`

Workflow file:

- `.github/workflows/ci.yml`

## Release hygiene

Before creating a new release, verify:

- the GitHub release assets use the `agent_memory_engine-*` names
- `pyproject.toml` points to the correct GitHub repository URLs
- `README.md` install instructions use `pip install agent-memory-engine`
- `CHANGELOG.md` contains a new section for the target version

## Recommended next upgrades

- add trusted publishing for PyPI via GitHub Actions
- add a dedicated release workflow for tags only
- generate release notes automatically from `CHANGELOG.md`
- add checksum generation for wheel and sdist assets
