#!/usr/bin/env bash
# ACIS Docker one-click launcher (Linux / macOS)
# Usage:
#   ./start.sh            start (build + up + wait healthy)
#   ./start.sh import     optional: import real AgriKG graph into Neo4j
#   ./start.sh status     show service status
#   ./start.sh logs       tail API logs
#   ./start.sh stop       stop (keep data volumes)
# Optional: export DEEPSEEK_API_KEY='sk-...' before start for LLM Judge/Critic

set -euo pipefail

CMD="${1:-start}"

require_docker() {
  if ! docker info >/dev/null 2>&1; then
    echo "[ACIS] Docker is not running. Start Docker first." >&2
    exit 1
  fi
}

wait_healthy() {
  echo "[ACIS] waiting for API health (http://localhost:8000/health) ..."
  for i in $(seq 1 30); do
    sleep 2
    if curl -sf --max-time 3 http://localhost:8000/health >/dev/null 2>&1; then
      echo "[ACIS] API ready: $(curl -sf http://localhost:8000/health)"
      return
    fi
  done
  echo "[ACIS] API did not become ready in 60s; check logs: ./start.sh logs" >&2
  exit 1
}

show_hints() {
  echo ""
  echo "============================================"
  echo "  ACIS is up"
  echo "  API:        http://localhost:8000   (GET /health, POST /diagnose)"
  echo "  Neo4j console: http://localhost:17474 (neo4j / agriai2026)"
  echo "  Qdrant:     http://localhost:6333"
  echo "============================================"
  echo ""
  echo "Tips:"
  echo "  - Enable LLM Judge/Critic: export DEEPSEEK_API_KEY='sk-...' before start"
  echo "  - Import real AgriKG graph:  ./start.sh import"
  echo "  - Stop:                      ./start.sh stop"
}

case "$CMD" in
  start)
    require_docker
    docker compose up -d --build
    wait_healthy
    show_hints
    ;;
  import)
    require_docker
    if [ ! -d "data/Agriculture_KnowledgeGraph-master" ]; then
      echo "[ACIS] data/Agriculture_KnowledgeGraph-master not found; skipping import."
      echo "       Unpack AgriKG data there and re-run ./start.sh import"
      exit 0
    fi
    docker compose exec api python scripts/import_agrikg.py --yes
    ;;
  status) require_docker; docker compose ps ;;
  logs)   require_docker; docker compose logs -f api ;;
  stop)
    require_docker
    docker compose down
    echo "[ACIS] stopped (volumes kept). To wipe data: docker compose down -v"
    ;;
  *)
    echo "Usage: $0 [start|import|status|logs|stop]"
    exit 1
    ;;
esac
