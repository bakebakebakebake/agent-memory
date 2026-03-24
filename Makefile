PROTO_DIR=proto

.PHONY: proto test go-test py-test build docker-up go-bench bench-compare

proto:
	export PATH="$$(go env GOPATH)/bin:$$PATH" && protoc -I $(PROTO_DIR) \
		--go_out=go-server/gen --go_opt=paths=source_relative \
		--go-grpc_out=go-server/gen --go-grpc_opt=paths=source_relative \
		$(PROTO_DIR)/memory/v1/models.proto \
		$(PROTO_DIR)/memory/v1/storage_service.proto \
		$(PROTO_DIR)/memory/v1/ai_service.proto
	. .venv/bin/activate && python -m grpc_tools.protoc -I $(PROTO_DIR) \
		--python_out=src/agent_memory/generated \
		--grpc_python_out=src/agent_memory/generated \
		$(PROTO_DIR)/memory/v1/models.proto \
		$(PROTO_DIR)/memory/v1/storage_service.proto \
		$(PROTO_DIR)/memory/v1/ai_service.proto
	. .venv/bin/activate && python -c 'from pathlib import Path; root = Path("src/agent_memory/generated/memory/v1"); [path.write_text(path.read_text().replace("from memory.v1 import", "from agent_memory.generated.memory.v1 import")) for path in root.glob("*_pb2*.py")]'

go-test:
	cd go-server && go test ./...

go-bench:
	cd go-server && go test -run=^$$ -bench=. ./...

py-test:
	pytest -q

test: go-test py-test

build:
	cd go-server && go build ./...

docker-up:
	docker compose -f deploy/docker-compose.yml up --build

bench-compare:
	PYTHONPATH=src .venv/bin/python benchmarks/compare_go_python.py
