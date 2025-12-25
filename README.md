# AI Agent — Docker Integration

Quick notes to build and run the agent in Docker.

Build image:

```bash
docker build -t ai-agent .
```

Run container (no local LLM/ollama required):

```bash
docker run --rm -it \
  -e ENABLE_LLM=false \
  -e AGENT_BASE_URL=http://host.docker.internal:5000/api/notes \
  ai-agent
```

Using docker-compose:

```bash
docker-compose up --build
```

Notes:
- The container disables local LLM calls by default (`ENABLE_LLM=false`). If you have the `ollama` CLI available inside the container or in your environment and want the agent to call it, set `ENABLE_LLM=true` and set `LLM_MODEL` as needed.
- The interpreter calls the `ollama` CLI via subprocess when LLM is enabled; installing and running Ollama is outside the scope of this Dockerfile.
- Environment variables:
  - `ENABLE_LLM` (true/false)
  - `LLM_MODEL` (default: `llama3.2:latest`)
  - `AGENT_BASE_URL` (backend URL used by `tools.py`)
