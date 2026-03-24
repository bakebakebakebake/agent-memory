package config

import "github.com/spf13/viper"

type Config struct {
	HTTPAddress     string
	GRPCAddress     string
	DatabasePath    string
	APIKey          string
	JWTSecret       string
	LogLevel        string
	SemanticLimit   int
	LexicalLimit    int
	EntityLimit     int
	DefaultLimit    int
	RRFK            int
	RequestTimeoutS float64
}

func Load() Config {
	viper.SetDefault("http_address", ":8080")
	viper.SetDefault("grpc_address", ":9090")
	viper.SetDefault("database_path", "agent-memory.db")
	viper.SetDefault("log_level", "info")
	viper.SetDefault("semantic_limit", 10)
	viper.SetDefault("lexical_limit", 10)
	viper.SetDefault("entity_limit", 10)
	viper.SetDefault("default_limit", 5)
	viper.SetDefault("rrf_k", 60)
	viper.SetDefault("request_timeout_seconds", 5.0)
	viper.SetEnvPrefix("agent_memory")
	viper.AutomaticEnv()
	return Config{
		HTTPAddress:     viper.GetString("http_address"),
		GRPCAddress:     viper.GetString("grpc_address"),
		DatabasePath:    viper.GetString("database_path"),
		APIKey:          viper.GetString("api_key"),
		JWTSecret:       viper.GetString("jwt_secret"),
		LogLevel:        viper.GetString("log_level"),
		SemanticLimit:   viper.GetInt("semantic_limit"),
		LexicalLimit:    viper.GetInt("lexical_limit"),
		EntityLimit:     viper.GetInt("entity_limit"),
		DefaultLimit:    viper.GetInt("default_limit"),
		RRFK:            viper.GetInt("rrf_k"),
		RequestTimeoutS: viper.GetFloat64("request_timeout_seconds"),
	}
}
