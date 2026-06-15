#!/bin/bash
set -e

case "${1:-api}" in
  api)
    exec pptx-api
    ;;
  ui)
    exec pptx-ui
    ;;
  mcp)
    exec pptx-mcp --transport "${MCP_TRANSPORT:-stdio}"
    ;;
  *)
    exec "$@"
    ;;
esac
