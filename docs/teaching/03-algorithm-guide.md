# 03 算法指南
> 用“直觉—公式—代码解读—计算示例”的统一结构，拆解系统里的核心算法。

## 前置知识

- [02 架构深度剖析](02-architecture-deep-dive.md)

## 本文目标

完成阅读后，你将理解：

1. 系统中的检索、治理与冲突算法分别解决什么问题
2. Go 与 Python 两端如何实现同一套策略
3. 为什么当前方案强调规则、排名和可解释性
4. 如何用具体数值手工推导结果

## 阅读提示

本文按四步法组织每个算法：

1. **直觉 (Intuition)**
2. **公式 (Formula)**
3. **代码解读 (Code Walkthrough)**
4. **计算示例 (Worked Example)**

---

## 1. 艾宾浩斯遗忘曲线

### 直觉 (Intuition)

记忆不会以固定速度衰减。重要、可信、被访问过的记忆应该保留更久，长时间未访问的弱记忆应该逐步下沉。这个模块的作用是给每条记忆算出一个“当前有效强度”，再根据阈值决定是否升到长期层或降回短期层。

### 公式 (Formula)

$$
\text{strength} = importance \times trust \times (1 + \ln(1 + access)) \times e^{-decay \cdot age^\beta}
$$

符号说明：

- $importance$：重要度
- $trust$：信任分
- $access$：访问次数
- $decay$：衰减系数
- $age$：年龄，单位为天
- $\beta$：层级相关的时间曲线参数

### 代码解读 (Code Walkthrough)

**`go-server/internal/controller/forgetting.go`**

```go
func (policy ForgettingPolicy) EffectiveStrength(memory *memoryv1.MemoryItem, ageDays float64) float64 {
	accessBoost := 1 + math.Log(1+math.Max(float64(memory.AccessCount), 0))
	beta := policy.ShortTermBeta
	if memory.Layer == "long_term" {
		beta = policy.LongTermBeta
	}
	temporalDecay := math.Exp(-memory.DecayRate * math.Pow(ageDays, beta))
	return memory.Importance * memory.TrustScore * accessBoost * temporalDecay
}
```

**`src/agent_memory/controller/forgetting.py`**

```python
def effective_strength(self, item: MemoryItem, age_days: float) -> float:
    access_boost = 1.0 + math.log1p(max(item.access_count, 0))
    beta = self.long_term_beta if item.layer == MemoryLayer.LONG_TERM else self.short_term_beta
    temporal_decay = math.exp(-item.decay_rate * (age_days ** beta))
    return item.importance * item.trust_score * access_boost * temporal_decay
```

Go 和 Python 都做了同样三件事：

1. 先根据访问次数增加权重
2. 再按层级选取不同的 $\beta$
3. 最后乘上指数衰减项

### 计算示例 (Worked Example)

假设：

- `importance = 0.8`
- `trust = 0.9`
- `access = 4`
- `decay = 0.05`
- `age = 10`
- `beta = 1.2`

则：

$$
1 + \ln(1 + 4) = 1 + \ln 5 \approx 2.609
$$

$$
e^{-0.05 \cdot 10^{1.2}} \approx e^{-0.792} \approx 0.453
$$

$$
strength \approx 0.8 \times 0.9 \times 2.609 \times 0.453 \approx 0.851
$$

若提升阈值为 `0.7`，这条记忆会进入 `long_term`。

---

## 2. 多路检索与倒数排名融合 (Reciprocal Rank Fusion, RRF)

### 直觉 (Intuition)

语义检索、全文检索和实体检索的分数尺度不同。直接做加权平均很难调。RRF 只看排名位置，把多个“谁排在前面”的信息合到一起，更稳，也更容易解释。

### 公式 (Formula)

$$
\text{score}(d) = \sum_i \frac{1}{k + rank_i(d)}
$$

符号说明：

- $d$：候选记忆
- $i$：第 $i$ 路检索
- $rank_i(d)$：候选在该路结果中的名次，从 1 开始
- $k$：平滑常数，本项目使用 `60`

### 代码解读 (Code Walkthrough)

**`go-server/internal/controller/router.go`**

```go
func ReciprocalRankFusion(rankings map[string][]string, k int) map[string]float64 {
	scores := map[string]float64{}
	for _, rankedIDs := range rankings {
		for rank, itemID := range rankedIDs {
			scores[itemID] += 1.0 / float64(k+rank+1)
		}
	}
	return scores
}
```

**`src/agent_memory/controller/router.py`**

```python
def reciprocal_rank_fusion(rankings: dict[str, list[str]], k: int = 60) -> dict[str, float]:
    scores: dict[str, float] = defaultdict(float)
    for ranked_ids in rankings.values():
        for rank, item_id in enumerate(ranked_ids, start=1):
            scores[item_id] += 1.0 / (k + rank)
    return dict(sorted(scores.items(), key=lambda item: item[1], reverse=True))
```

### 计算示例 (Worked Example)

设三路结果分别为：

- semantic：`A, B`
- full_text：`B, A`
- entity：`B`

则：

$$
score(A) = \frac{1}{61} + \frac{1}{62} \approx 0.03252
$$

$$
score(B) = \frac{1}{62} + \frac{1}{61} + \frac{1}{61} \approx 0.04891
$$

所以 `B` 会排在前面。

---

## 3. 意图感知路由

### 直觉 (Intuition)

不同问题需要不同检索策略。“为什么”更像因果问题，“最近”更像时间问题，“如何”更像过程问题。先识别意图，再决定用哪些检索路径，能减少无效召回。

### 公式 (Formula)

这里没有连续数值公式，更适合理解为一个策略矩阵：

$$
\text{intent} = f(\text{query keywords})
$$

$$
\text{plan} = g(\text{intent}) = \{\text{strategies}, \text{filters}\}
$$

### 代码解读 (Code Walkthrough)

**`go-server/internal/controller/router.go`**

```go
var intentPatterns = []struct {
	Intent   Intent
	Patterns []string
}{
	{IntentCausal, []string{"为什么", "为何", "导致", "cause", "why"}},
	{IntentTemporal, []string{"上周", "最近", "之前", "when", "recent"}},
	{IntentProcedural, []string{"如何", "怎么", "步骤", "how to"}},
}
```

**`src/agent_memory/controller/router.py`**

```python
INTENT_PATTERNS = {
    QueryIntent.CAUSAL: ["为什么", "为何", "why", "cause"],
    QueryIntent.TEMPORAL: ["最近", "之前", "when", "recent"],
    QueryIntent.PROCEDURAL: ["如何", "怎么", "how to"],
}
```

路由结果示例：

- causal → `semantic + full_text + causal_trace`
- temporal → `semantic + full_text`，并打开 `sort=recency`
- procedural → `semantic + full_text`，并过滤 `memory_type=procedural`

### 计算示例 (Worked Example)

查询：`为什么选择 SQLite`

步骤：

1. 命中关键词“为什么”
2. 分类为 `causal`
3. 生成策略：`semantic`、`full_text`、`causal_trace`
4. 若 semantic 命中不足，则退回 lexical seed 继续追祖先链

---

## 4. 信任评分

### 直觉 (Intuition)

记忆的可信度不能只看来源。新近程度、旁证数量和冲突数量都会影响最终分数。这个模块的目标是给系统一个简单、可测、可裁剪的可信度函数。

### 公式 (Formula)

$$
\text{score} = source \times 0.5 + recency \times 0.15 + corroboration \times 0.15 - contradiction \times 0.2
$$

其中：

- $source$：来源可靠度
- $recency$：时间新鲜度，按 90 天线性衰减
- $corroboration$：旁证归一化结果
- $contradiction$：冲突归一化结果

### 代码解读 (Code Walkthrough)

**`go-server/internal/controller/trust.go`**

```go
recencyBonus := 1.0 - min(ageDays, 90.0)/90.0
corroborationBonus := min(float64(corroborationCount), 5) / 5.0
contradictionPenalty := min(float64(contradictionCount), 5) / 5.0
```

**`src/agent_memory/controller/trust.py`**

```python
recency_bonus = 1.0 - min(age_days, 90.0) / 90.0
corroboration_bonus = min(float(corroboration_count), 5.0) / 5.0
contradiction_penalty = min(float(contradiction_count), 5.0) / 5.0
```

### 计算示例 (Worked Example)

若：

- `source = 0.8`
- `age_days = 15`
- `corroboration = 2`
- `contradiction = 1`

则：

$$
recency = 1 - 15/90 = 0.8333
$$

$$
corroboration = 2/5 = 0.4,\ contradiction = 1/5 = 0.2
$$

$$
score = 0.8 \times 0.5 + 0.8333 \times 0.15 + 0.4 \times 0.15 - 0.2 \times 0.2 \approx 0.545
$$

---

## 5. 冲突检测

### 直觉 (Intuition)

两条记忆内容很像，但极性相反时，很可能构成矛盾。“用户喜欢 SQLite”和“用户不喜欢 SQLite”需要被标成 `contradicts`，这样检索和治理模块才能继续处理。

### 公式 (Formula)

$$
\text{confidence} = similarity \times 0.45 + ratio \times 0.25 + polarity\_bonus + preference\_bonus
$$

其中：

- $similarity$：外部或内部向量相似度
- $ratio$：词面重合比例
- $polarity\_bonus$：正负极性不同的加分
- $preference\_bonus$：包含偏好类表达的加分

### 代码解读 (Code Walkthrough)

**`go-server/internal/controller/conflict.go`**

```go
if leftNegative != rightNegative {
	polarityBonus = 0.25
}
if containsAny(leftNorm, preferenceMarkers) || containsAny(rightNorm, preferenceMarkers) {
	preferenceBonus = 0.15
}
value := similarity*0.45 + ratio*0.25 + polarityBonus + preferenceBonus
```

**`src/agent_memory/controller/conflict.py`**

```python
if left_negative != right_negative:
    polarity_bonus = 0.25
if _contains_any(left_norm, PREFERENCE_MARKERS) or _contains_any(right_norm, PREFERENCE_MARKERS):
    preference_bonus = 0.15
confidence = similarity * 0.45 + ratio * 0.25 + polarity_bonus + preference_bonus
```

### 计算示例 (Worked Example)

假设：

- 向量相似度 `0.82`
- 词面重合比例 `0.60`
- 极性相反
- 两边都包含“喜欢 / prefer”

则：

$$
confidence = 0.82 \times 0.45 + 0.60 \times 0.25 + 0.25 + 0.15 = 0.919
$$

这是一个很高的冲突置信度。

---

## 6. 记忆合并

### 直觉 (Intuition)

系统长期运行后，容易出现内容相近、时间接近、实体一致的重复记忆。合并模块不直接替换原始记忆，而是先给出 merge plan，降低误伤。

### 公式 (Formula)

这里更像一个过滤条件组合：

$$
\text{merge candidate} = \text{same entity group} \land \text{cosine} \ge 0.9 \land \text{within 45 days}
$$

### 代码解读 (Code Walkthrough)

**`src/agent_memory/controller/consolidation.py`**

```python
if similarity >= 0.9 and abs((left.created_at - right.created_at).days) <= 45:
    groups[key].append((left, right))
```

Go 服务端当前没有单独的 consolidation 模块，这部分仍由 Python 智能面负责。

### 计算示例 (Worked Example)

若两条记忆：

- 实体都包含 `sqlite`
- 余弦相似度 `0.93`
- 时间差 `12` 天

那么它们会进入同一个候选组，等待后续合并决策。

---

## 7. 余弦相似度

### 直觉 (Intuition)

向量检索最基本的问题是判断两段文本是否“方向接近”。余弦相似度衡量的正是这个方向夹角。

### 公式 (Formula)

$$
\cos(\theta) = \frac{\vec{a} \cdot \vec{b}}{\|\vec{a}\| \cdot \|\vec{b}\|}
$$

### 代码解读 (Code Walkthrough)

**`go-server/internal/storage/sqlite.go`**

```go
for index := range size {
	numerator += float64(left[index] * right[index])
	leftNorm += float64(left[index] * left[index])
	rightNorm += float64(right[index] * right[index])
}
```

**`src/agent_memory/storage/sqlite_backend.py`**

```python
numerator = sum(a * b for a, b in zip(left_trimmed, right_trimmed, strict=False))
left_norm = sqrt(sum(a * a for a in left_trimmed))
right_norm = sqrt(sum(b * b for b in right_trimmed))
```

### 计算示例 (Worked Example)

向量：

- `a = [1, 2, 3]`
- `b = [1, 2, 4]`

则：

$$
a \cdot b = 1 + 4 + 12 = 17
$$

$$
\|a\| = \sqrt{14}, \|b\| = \sqrt{21}
$$

$$
\cos(\theta) = \frac{17}{\sqrt{14}\sqrt{21}} \approx 0.991
$$

---

## 8. FTS5 全文检索

### 直觉 (Intuition)

向量检索擅长语义邻近，但对关键字精确命中、代码标识符和中英混合短语，全文检索更直接。

### 公式 (Formula)

当前 Python 端使用 `FTS5 + bm25` 排序，Go 端用 `LIKE` 与词项匹配做轻量实现。这里的重点是“词项召回 + 结果排序”，而非复杂的语义模型。

### 代码解读 (Code Walkthrough)

**`src/agent_memory/storage/sqlite_backend.py`**

```python
SELECT m.*, v.embedding_json, bm25(memories_fts) AS rank_score
FROM memories_fts
JOIN memories m ON m.rowid = memories_fts.rowid
```

**`go-server/internal/storage/sqlite.go`**

```go
queryText += ` AND (LOWER(m.content) LIKE ? OR LOWER(m.tags_json) LIKE ?)`
score := lexicalScore(query, item.Content, item.Tags)
```

### 计算示例 (Worked Example)

查询：`SQLite agent`

若内容中两个词都出现，`lexicalScore = 2 / 2 = 1.0`。若只出现一个词，分数为 `0.5`。

---

## 9. 检索编排全流程

### 直觉 (Intuition)

单路检索很少能覆盖所有问题。编排器的责任是把多路结果组织起来，保持召回质量与可解释性。

### 公式 (Formula)

可以把编排器抽象成：

$$
\text{output} = \text{Touch}(\text{GetMemory}(\text{TakeTopK}(\text{RRF}(\text{Collect}(\text{Plan}(query))))))
$$

### 代码解读 (Code Walkthrough)

**`go-server/internal/search/orchestrator.go`**

```go
plan := orchestrator.router.Plan(query)
for _, strategy := range plan.Strategies {
    // semantic / full_text / entity / causal_trace
}
fused := controller.ReciprocalRankFusion(rankings, orchestrator.config.RRFK)
```

**`src/agent_memory/client.py`**

```python
plan = self.router.plan(query)
rankings: dict[str, list[str]] = {}
fused = reciprocal_rank_fusion(rankings, k=self.config.rrf_k)
```

### 计算示例 (Worked Example)

对查询“为什么选择 SQLite”：

1. Router 判定为 `causal`
2. Orchestrator 先跑 semantic 和 full-text
3. 选前两条命中做 `TraceAncestors`
4. 用 RRF 融合
5. `touch_memory()` 刷新访问计数

---

## 10. 维护周期

### 直觉 (Intuition)

记忆系统是活系统。若没有定期维护，旧记忆会越来越多，冲突边会积累，健康指标会失真。维护周期负责把衰减、升降层、冲突扫描和合并候选统一串起来。

### 公式 (Formula)

维护周期更适合看作一个阶段式流程：

$$
\text{maintain} = \text{decay check} \rightarrow \text{layer transition} \rightarrow \text{conflict upkeep} \rightarrow \text{consolidation}
$$

### 代码解读 (Code Walkthrough)

**`src/agent_memory/client.py`**

```python
def maintain(self) -> MaintenanceReport:
    report = MaintenanceReport()
    # 遍历记忆，计算 strength，决定 promoted / demoted / decayed
    # 继续做 conflict upkeep 与 consolidation
```

Go 服务端当前把维护核心逻辑更多放在 Python 智能面，服务端主要暴露存储、查询与治理接口。

### 计算示例 (Worked Example)

假设一次维护扫描 100 条记忆：

- 8 条强度超过 `0.7`，升级为 `long_term`
- 5 条强度低于 `0.3`，回到 `short_term`
- 3 对记忆进入冲突候选
- 2 组记忆进入合并候选

那么最终报告会记录这些计数，便于后续观测和调优。

## 小结

- 遗忘、RRF、路由和冲突检测构成了系统的算法骨架
- Go 与 Python 在关键公式和策略上保持一致
- 当前方案强调规则化、可测性和可解释性
- 若要继续优化，最值得深挖的方向是 procedural recall、合并质量和冲突复判

## 延伸阅读

- [04 Go 服务端指南](04-go-server-guide.md)
- [05 Python SDK 指南](05-python-sdk-guide.md)
- [07 数据库与 Schema 指南](07-database-schema-guide.md)
- [11 性能与基准测试](11-performance-benchmarking.md)
