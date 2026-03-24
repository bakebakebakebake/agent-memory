package observability

import "github.com/prometheus/client_golang/prometheus"

type Metrics struct {
	StoreDuration     *prometheus.HistogramVec
	SearchDuration    *prometheus.HistogramVec
	MemoryTotal       prometheus.Gauge
	ConflictsDetected prometheus.Counter
	HTTPDuration      *prometheus.HistogramVec
}

func NewMetrics() *Metrics {
	metrics := &Metrics{
		StoreDuration: prometheus.NewHistogramVec(
			prometheus.HistogramOpts{Name: "memory_store_duration_seconds", Help: "Latency for memory store operations."},
			[]string{"transport"},
		),
		SearchDuration: prometheus.NewHistogramVec(
			prometheus.HistogramOpts{Name: "memory_search_duration_seconds", Help: "Latency for memory search operations."},
			[]string{"transport", "strategy"},
		),
		MemoryTotal: prometheus.NewGauge(
			prometheus.GaugeOpts{Name: "memory_total", Help: "Active memory count."},
		),
		ConflictsDetected: prometheus.NewCounter(
			prometheus.CounterOpts{Name: "memory_conflicts_detected_total", Help: "Detected conflicts."},
		),
		HTTPDuration: prometheus.NewHistogramVec(
			prometheus.HistogramOpts{Name: "memory_http_duration_seconds", Help: "HTTP handler duration."},
			[]string{"method", "path"},
		),
	}
	prometheus.MustRegister(
		metrics.StoreDuration,
		metrics.SearchDuration,
		metrics.MemoryTotal,
		metrics.ConflictsDetected,
		metrics.HTTPDuration,
	)
	return metrics
}

func Unregister(metrics *Metrics) {
	prometheus.Unregister(metrics.StoreDuration)
	prometheus.Unregister(metrics.SearchDuration)
	prometheus.Unregister(metrics.MemoryTotal)
	prometheus.Unregister(metrics.ConflictsDetected)
	prometheus.Unregister(metrics.HTTPDuration)
}
