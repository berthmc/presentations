---
name: 300-mcp-servers
description: >-
  Launch and interact with the CMS documentation MCP server (port 3003) and the 
  security-auditor MCP server (port 3001) in Docker. Use this as a standard procedure 
  whenever there is a code change.
---

# MCP Servers (CMS)

## Security Auditor MCP (Port 3001)
- **Mandatory**: Invoke the security-auditor MCP server available in the docker environment at port 3001 as a standard procedure whenever there is a code change.
- **Docker Compose**: Start it using the `codereview` repository or if it's included in the local stack.
- **Troubleshooting**: If connecting to port 3001 raises problems with some models, ensure the Docker network is correctly bridged to the host (`host.docker.internal`).

## Documentation MCP (Port 3003)
- Runs as part of the `cms` stack (`mcp_docs` container).
- Provides context on the CMS API and structures.
- Launch: `sudo docker compose up -d mcp_docs`
