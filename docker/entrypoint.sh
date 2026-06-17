#!/bin/bash
set -e

case "${1:-api}" in
  api)
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
