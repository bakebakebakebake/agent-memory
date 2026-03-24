PROTO_DIR=../proto

.PHONY: proto build test

proto:
	protoc -I $(PROTO_DIR) \
		--go_out=gen --go_opt=paths=source_relative \
		--go-grpc_out=gen --go-grpc_opt=paths=source_relative \
		$(PROTO_DIR)/memory/v1/models.proto \
		$(PROTO_DIR)/memory/v1/storage_service.proto \
		$(PROTO_DIR)/memory/v1/ai_service.proto

build:
	go build ./...

test:
	go test ./...
