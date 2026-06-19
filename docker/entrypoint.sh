#!/bin/bash
set -e

wait_for_ollama() {
  local host_url="${OLLAMA_HOST:-http://localhost:11434}"
  local host="${host_url#http://}"
  host="${host#https://}"
  host="${host%%/*}"
  local max_attempts="${OLLAMA_WAIT_ATTEMPTS:-30}"
  local attempt=1

  echo "Waiting for Ollama at http://${host}/api/tags ..."
  while [ "${attempt}" -le "${max_attempts}" ]; do
    if curl -sf "http://${host}/api/tags" >/dev/null 2>&1; then
      echo "Ollama is ready."
      return 0
    fi
    sleep 2
    attempt=$((attempt + 1))
  done

  echo "Warning: Ollama not reachable at http://${host} after ${max_attempts} attempts." >&2
  return 1
}

case "${1:-api}" in
  api)
    wait_for_ollama || true
    exec pptx-api
    ;;
  ui)
    echo "UI is now served by React/Vite — run: cd frontend && npm install && npm run dev"
    exit 1
    ;;
  mcp)
    exec pptx-mcp --transport "${MCP_TRANSPORT:-stdio}"
    ;;
  *)
    exec "$@"
    ;;
esac
