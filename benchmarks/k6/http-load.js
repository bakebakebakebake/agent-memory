import http from "k6/http";
import { check, sleep } from "k6";

const baseURL = __ENV.AGENT_MEMORY_BASE_URL || "http://127.0.0.1:8080";

export const options = {
  stages: [
    { duration: "1m", target: 10 },
    { duration: "1m", target: 50 },
    { duration: "1m", target: 100 },
  ],
  thresholds: {
    http_req_failed: ["rate<0.05"],
    http_req_duration: ["p(95)<500", "p(99)<1000"],
  },
};

function randomEmbedding() {
  return [0.1, 0.2, 0.3];
}

function memoryPayload(iteration) {
  const stamp = `${Date.now()}-${iteration}-${__VU}`;
  return JSON.stringify({
    id: `k6-http-${stamp}`,
    content: `SQLite helps agent memory stay local ${stamp}`,
    memory_type: "semantic",
    embedding: randomEmbedding(),
    created_at: new Date().toISOString(),
    last_accessed: new Date().toISOString(),
    access_count: 0,
    trust_score: 0.8,
    importance: 0.6,
    layer: "short_term",
    decay_rate: 0.1,
    source_id: "k6-http",
    entity_refs: ["sqlite", "agent"],
    tags: ["k6", "http"],
  });
}

export default function () {
  const roll = Math.random();
  let response;

  if (roll < 0.2) {
    response = http.post(`${baseURL}/api/v1/memories`, memoryPayload(__ITER), {
      headers: { "Content-Type": "application/json" },
    });
  } else if (roll < 0.6) {
    response = http.post(
      `${baseURL}/api/v1/search/query`,
      JSON.stringify({
        query: "为什么选择 SQLite",
        embedding: randomEmbedding(),
        entities: ["sqlite", "agent"],
        limit: 5,
      }),
      { headers: { "Content-Type": "application/json" } },
    );
  } else if (roll < 0.8) {
    response = http.post(
      `${baseURL}/api/v1/search/full-text`,
      JSON.stringify({ query: "SQLite agent", limit: 5, memory_type: "" }),
      { headers: { "Content-Type": "application/json" } },
    );
  } else if (roll < 0.9) {
    response = http.get(`${baseURL}/health`);
  } else {
    response = http.get(`${baseURL}/api/v1/trace/ancestors?memory_id=seed&max_depth=5`);
  }

  check(response, {
    "status is acceptable": (res) => [200, 201].includes(res.status),
  });

  sleep(0.2);
}
