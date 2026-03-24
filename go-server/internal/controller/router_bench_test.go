package controller

import "testing"

func BenchmarkRouterClassify(b *testing.B) {
	router := Router{}
	query := "为什么 SQLite 适合本地优先的 Agent 记忆系统"
	b.ReportAllocs()
	b.ResetTimer()
	for index := 0; index < b.N; index++ {
		_ = router.Classify(query)
	}
}

func BenchmarkReciprocalRankFusion(b *testing.B) {
	rankings := map[string][]string{
		"semantic":   {"m1", "m2", "m3", "m4", "m5"},
		"full_text":  {"m2", "m1", "m5", "m4", "m3"},
		"entity":     {"m2", "m6", "m1", "m7", "m3"},
		"causal":     {"m8", "m1", "m2"},
		"recency":    {"m2", "m9", "m1"},
		"procedural": {"m10", "m2", "m1"},
	}
	b.ReportAllocs()
	b.ResetTimer()
	for index := 0; index < b.N; index++ {
		_ = ReciprocalRankFusion(rankings, 60)
	}
}
