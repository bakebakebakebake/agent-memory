# k6 Load Tests

> 用阶梯式压力验证 REST 与 gRPC 服务模式的吞吐、延迟与错误率。

## 前置知识

- `docs/teaching/04-go-server-guide.md`
- `docs/teaching/08-deployment-guide.md`
- `docs/teaching/11-performance-benchmarking.md`

## 本文目标

完成阅读后，你将理解：

1. 如何运行 HTTP 与 gRPC 压测脚本
2. 如何读取 `req/s`、`p50/p95/p99` 与错误率
3. 如何根据结果定位服务端瓶颈

## 文件说明

- `benchmarks/k6/http-load.js`：HTTP 负载测试，操作占比为 `store 20% / search query 40% / full-text 20% / health 10% / trace 10%`
- `benchmarks/k6/grpc-load.js`：gRPC 负载测试，保持相同的流量结构

## 运行方式

启动 Go 服务：

```bash
cd /Users/xjf/Public/Code/Agent-Project
cd go-server && go run ./cmd/server
```

运行 HTTP 压测：

```bash
k6 run benchmarks/k6/http-load.js
```

运行 gRPC 压测：

```bash
k6 run -e AGENT_MEMORY_GRPC_TARGET=127.0.0.1:9090 benchmarks/k6/grpc-load.js
```

## 指标口径

- `http_req_duration` / `grpc_req_duration`：单次请求耗时
- `http_req_failed` / `checks`：错误率或通过率
- `iterations`：总请求次数，可结合时长换算吞吐

## 小结

- 两个脚本都采用 `10 → 50 → 100` VU 的三段阶梯
- HTTP 与 gRPC 保持相同的读写比例，便于横向对比
- 建议与 `docs/benchmark-results.md` 中的基准结果一起看

## 延伸阅读

- `docs/benchmark-results.md`
- `docs/teaching/10-testing-quality-guide.md`
- `docs/teaching/11-performance-benchmarking.md`
