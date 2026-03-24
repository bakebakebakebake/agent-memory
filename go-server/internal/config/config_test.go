package config

import (
	"os"
	"testing"

	"github.com/spf13/viper"
)

func clearEnv(t *testing.T, key string) {
	t.Helper()
	value, ok := os.LookupEnv(key)
	_ = os.Unsetenv(key)
	t.Cleanup(func() {
		if ok {
			_ = os.Setenv(key, value)
			return
		}
		_ = os.Unsetenv(key)
	})
}

func TestLoadDefaults(t *testing.T) {
	viper.Reset()
	defer viper.Reset()

	for _, key := range []string{
		"AGENT_MEMORY_HTTP_ADDRESS",
		"AGENT_MEMORY_GRPC_ADDRESS",
		"AGENT_MEMORY_DATABASE_PATH",
		"AGENT_MEMORY_API_KEY",
		"AGENT_MEMORY_JWT_SECRET",
		"AGENT_MEMORY_LOG_LEVEL",
		"AGENT_MEMORY_SEMANTIC_LIMIT",
		"AGENT_MEMORY_LEXICAL_LIMIT",
		"AGENT_MEMORY_ENTITY_LIMIT",
		"AGENT_MEMORY_DEFAULT_LIMIT",
		"AGENT_MEMORY_RRF_K",
		"AGENT_MEMORY_REQUEST_TIMEOUT_SECONDS",
	} {
		clearEnv(t, key)
	}

	cfg := Load()
	if cfg.HTTPAddress != ":8080" || cfg.GRPCAddress != ":9090" || cfg.DatabasePath != "agent-memory.db" {
		t.Fatalf("unexpected default addresses: %#v", cfg)
	}
	if cfg.SemanticLimit != 10 || cfg.LexicalLimit != 10 || cfg.EntityLimit != 10 || cfg.DefaultLimit != 5 || cfg.RRFK != 60 {
		t.Fatalf("unexpected numeric defaults: %#v", cfg)
	}
	if cfg.RequestTimeoutS != 5.0 || cfg.LogLevel != "info" {
		t.Fatalf("unexpected timeout/log defaults: %#v", cfg)
	}
}

func TestLoadEnvOverrides(t *testing.T) {
	viper.Reset()
	defer viper.Reset()

	t.Setenv("AGENT_MEMORY_HTTP_ADDRESS", "127.0.0.1:18080")
	t.Setenv("AGENT_MEMORY_GRPC_ADDRESS", "127.0.0.1:19090")
	t.Setenv("AGENT_MEMORY_DATABASE_PATH", "/tmp/agent-memory.db")
	t.Setenv("AGENT_MEMORY_API_KEY", "test-key")
	t.Setenv("AGENT_MEMORY_JWT_SECRET", "test-secret")
	t.Setenv("AGENT_MEMORY_LOG_LEVEL", "debug")
	t.Setenv("AGENT_MEMORY_SEMANTIC_LIMIT", "12")
	t.Setenv("AGENT_MEMORY_LEXICAL_LIMIT", "13")
	t.Setenv("AGENT_MEMORY_ENTITY_LIMIT", "14")
	t.Setenv("AGENT_MEMORY_DEFAULT_LIMIT", "7")
	t.Setenv("AGENT_MEMORY_RRF_K", "42")
	t.Setenv("AGENT_MEMORY_REQUEST_TIMEOUT_SECONDS", "8.5")

	cfg := Load()
	if cfg.HTTPAddress != "127.0.0.1:18080" || cfg.GRPCAddress != "127.0.0.1:19090" {
		t.Fatalf("unexpected address overrides: %#v", cfg)
	}
	if cfg.DatabasePath != "/tmp/agent-memory.db" || cfg.APIKey != "test-key" || cfg.JWTSecret != "test-secret" {
		t.Fatalf("unexpected string overrides: %#v", cfg)
	}
	if cfg.LogLevel != "debug" || cfg.SemanticLimit != 12 || cfg.LexicalLimit != 13 || cfg.EntityLimit != 14 || cfg.DefaultLimit != 7 || cfg.RRFK != 42 {
		t.Fatalf("unexpected numeric overrides: %#v", cfg)
	}
	if cfg.RequestTimeoutS != 8.5 {
		t.Fatalf("unexpected timeout override: %#v", cfg)
	}
}
