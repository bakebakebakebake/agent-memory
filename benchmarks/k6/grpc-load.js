import grpc from "k6/net/grpc";
import { check, sleep } from "k6";

const client = new grpc.Client();
client.load(["proto"], "memory/v1/models.proto", "memory/v1/storage_service.proto");

export const options = {
  stages: [
    { duration: "1m", target: 10 },
    { duration: "1m", target: 50 },
    { duration: "1m", target: 100 },
  ],
  thresholds: {
    grpc_req_duration: ["p(95)<500", "p(99)<1000"],
    checks: ["rate>0.95"],
  },
};

const target = __ENV.AGENT_MEMORY_GRPC_TARGET || "127.0.0.1:9090";

export function setup() {
  client.connect(target, { plaintext: true });
}

export default function () {
  const stamp = `${Date.now()}-${__ITER}-${__VU}`;
  const roll = Math.random();
  let response;

  if (roll < 0.2) {
    response = client.invoke("memory.v1.StorageService/AddMemory", {
      item: {
        id: `k6-grpc-${stamp}`,
        content: `SQLite keeps memory local ${stamp}`,
        memoryType: "semantic",
        embedding: [0.1, 0.2, 0.3],
        createdAt: new Date().toISOString(),
        lastAccessed: new Date().toISOString(),
        trustScore: 0.8,
        importance: 0.6,
        layer: "short_term",
        decayRate: 0.1,
        sourceId: "k6-grpc",
        entityRefs: ["sqlite", "agent"],
        tags: ["k6", "grpc"],
      },
    });
  } else if (roll < 0.6) {
    response = client.invoke("memory.v1.StorageService/SearchQuery", {
      query: "为什么选择 SQLite",
      embedding: [0.1, 0.2, 0.3],
      entities: ["sqlite", "agent"],
      limit: 5,
    });
  } else if (roll < 0.8) {
    response = client.invoke("memory.v1.StorageService/SearchFullText", {
      query: "SQLite agent",
      limit: 5,
      memoryType: "",
    });
  } else if (roll < 0.9) {
    response = client.invoke("memory.v1.StorageService/HealthCheck", {});
  } else {
    response = client.invoke("memory.v1.StorageService/TraceAncestors", {
      memoryId: "seed",
      maxDepth: 5,
    });
  }

  check(response, {
    "grpc status ok": (res) => res && res.status === grpc.StatusOK,
  });

  sleep(0.2);
}

export function teardown() {
  client.close();
}
