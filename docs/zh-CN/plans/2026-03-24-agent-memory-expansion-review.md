# Agent Memory 扩展与优化总表

[English](../../plans/2026-03-24-agent-memory-expansion-review.md) | [简体中文](2026-03-24-agent-memory-expansion-review.md)

日期：`2026-03-24`

## 1. 结论摘要

当前 `agent-memory` 已经是一个可公开展示的完整原型：

- SDK、SQLite 存储、FTS、`sqlite-vec` 集成与 fallback 已具备
- 路由、遗忘、冲突、巩固、健康监控、导出导入都有基础版本
- MCP、REST、CLI、Demo、Benchmark、CI、打包与发布都已落地
- MCP 工具已经在真实 FastMCP 风格使用中验证过

下一阶段的核心问题已经不是“有没有这些模块”，而是“先把哪些能力做深，才能成为更强的长期开源项目”。

建议优先级：

1. 检索质量与性能
2. 提取 / 冲突 / 巩固的智能化闭环
3. 生产级工程能力
4. 更强的评测与发布质量

## 2. 当前状态

### 2.1 目前做得比较好的部分

- 零配置本地运行：SQLite + WAL 非常适合 Agent workload
- 向量检索总体架构正确
- 规则路由 + RRF 可解释性强
- 健康监控、审计、演化、软删除、因果链方向正确
- SDK / CLI / MCP / REST 接口齐全
- 技术面覆盖广，适合公开展示

### 2.2 当前边界

- 若干“智能模块”还停留在 baseline
- 一些生产级问题还没有完全系统化
- 评测数据足够 demo，但还不足以支撑更强的研究型结论

## 3. 优先级建议

## P0：最高优先级

### P0-1. 把向量检索路径做成真正可证明的生产级能力

建议增加：

- `sqlite_vec_enabled`
- `vector_index_dimension`
- `vector_search_mode`
- `1k / 10k / 100k` benchmark
- fallback 告警或 metadata 输出

### P0-2. 强化提取与去重

建议增加：

- `draft_postprocessor`
- 批内去重
- 与已有记忆的近似重复检测
- 低信息草稿过滤
- `confidence`
- `evidence_turns`
- `extraction_method`

### P0-3. 将 temporal 检索升级为真正的时间约束检索

建议增加：

- 中英双语时间解析
- `created_at` / `valid_from` / `valid_until` 过滤
- `time_match_reason`

## P1：下一阶段投入

### P1-1. 把冲突检测变成治理工作流

建议增加：

- `pending`
- `resolved_keep_both`
- `resolved_supersede`
- `needs_review`
- conflict queue
- 后台维护任务统一复判

### P1-2. 把巩固从重复合并升级为主题压缩

建议增加：

- `dedup_merge`
- `topic_summary`
- `supersedes_id` 链
- `derived_from` 多边关系
- `consolidation_batch_id`

### P1-3. 增加多租户 / 多 Agent 隔离

建议增加：

- `namespace` 或 `agent_id + user_id`
- 默认租户过滤
- MCP 工具支持 namespace

## P2：工程与发布质量

### P2-1. 增加 schema migration

建议：

- `schema_version`
- `storage/migrations/001_init.sql`
- `storage/migrations/002_add_namespace.sql`
- 启动时自动执行未完成 migration

### P2-2. 强化 provider client

建议：

- 完整实现 `OpenAIEmbeddingProvider`
- 超时
- 重试
- 指数退避
- 错误分类
- provider metrics

### P2-3. 增加可观测性

建议新增指标：

- `sqlite_vec_enabled`
- `embedding_provider`
- `avg_search_latency_ms`
- `conflict_queue_size`
- `consolidation_candidates`
- 可选 debug log

## 4. 推荐路线图叙事

最合适的公开叙事是：

- **现在**：零配置、本地优先、可解释的 Agent 长期记忆引擎
- **下一步**：更强的检索质量、更可观测的向量性能、更结构化的提取
- **再下一步**：migration、多租户、生产可观测性
