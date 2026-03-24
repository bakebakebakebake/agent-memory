package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"net/http"
	"os"
	"strings"

	"github.com/bakebakebakebake/agent-memory/go-server/internal/config"
	"github.com/spf13/cobra"
)

func main() {
	cfg := config.Load()
	root := &cobra.Command{
		Use:   "agent-memory-go",
		Short: "Go CLI for the agent memory service",
	}
	root.AddCommand(
		healthCommand(cfg),
		storeCommand(cfg),
		searchCommand(cfg),
	)
	if err := root.Execute(); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}

func healthCommand(cfg config.Config) *cobra.Command {
	return &cobra.Command{
		Use:   "health",
		Short: "Read service health",
		RunE: func(command *cobra.Command, args []string) error {
			return printJSONRequest(http.MethodGet, cfg.HTTPAddress, "/health", nil)
		},
	}
}

func storeCommand(cfg config.Config) *cobra.Command {
	var sourceID string
	command := &cobra.Command{
		Use:   "store [content]",
		Short: "Store a memory through the Go server",
		Args:  cobra.ExactArgs(1),
		RunE: func(command *cobra.Command, args []string) error {
			payload := map[string]any{
				"id":            strings.ReplaceAll(args[0], " ", "-"),
				"content":       args[0],
				"memory_type":   "semantic",
				"embedding":     []float32{1, 1, float32(len(args[0]))},
				"created_at":    "",
				"last_accessed": "",
				"source_id":     sourceID,
				"trust_score":   0.75,
				"importance":    0.5,
				"layer":         "short_term",
				"decay_rate":    0.1,
				"entity_refs":   []string{},
				"tags":          []string{},
			}
			return printJSONRequest(http.MethodPost, cfg.HTTPAddress, "/api/v1/memories", payload)
		},
	}
	command.Flags().StringVar(&sourceID, "source-id", "go-cli", "Source identifier")
	return command
}

func searchCommand(cfg config.Config) *cobra.Command {
	return &cobra.Command{
		Use:   "search [query]",
		Short: "Search memories via full text",
		Args:  cobra.ExactArgs(1),
		RunE: func(command *cobra.Command, args []string) error {
			payload := map[string]any{"query": args[0], "limit": 5}
			return printJSONRequest(http.MethodPost, cfg.HTTPAddress, "/api/v1/search/full-text", payload)
		},
	}
}

func printJSONRequest(method string, address string, path string, payload map[string]any) error {
	url := "http://127.0.0.1" + address + path
	var body *bytes.Reader
	if payload != nil {
		encoded, err := json.Marshal(payload)
		if err != nil {
			return err
		}
		body = bytes.NewReader(encoded)
	} else {
		body = bytes.NewReader(nil)
	}
	request, err := http.NewRequest(method, url, body)
	if err != nil {
		return err
	}
	if payload != nil {
		request.Header.Set("Content-Type", "application/json")
	}
	response, err := http.DefaultClient.Do(request)
	if err != nil {
		return err
	}
	defer response.Body.Close()
	var decoded any
	if err := json.NewDecoder(response.Body).Decode(&decoded); err != nil {
		return err
	}
	pretty, err := json.MarshalIndent(decoded, "", "  ")
	if err != nil {
		return err
	}
	fmt.Println(string(pretty))
	return nil
}
