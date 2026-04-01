# Dispatch AI Hackathon

FastAPI backend with a repo-hosted frontend for the Dispatch AI router demo.

## Routing Layer

The backend keeps the existing routing pipeline shape and now extends it into a real Bedrock-backed flow:

1. Signal extraction
2. Hard-rule prefilter
3. Numeric uncertainty scoring
4. Heuristic analysis
5. Gated Qwen classification only for ambiguous prompts
6. Score-based model selection with safety rules
7. Final Bedrock call with latency, token, and cost metadata

Current runtime targets:

- Amazon Nova Micro for the cheapest factual work
- Mistral for cheap general prompts
- Claude Haiku 4.5 for mid reasoning and high-uncertainty fallback
- Amazon Nova Pro for code-heavy prompts
- Claude Sonnet 4.5 for stronger reasoning
- Qwen3 Next 80B A3B as a classifier only

Safety rules stay on even when Qwen is used:

- high complexity never routes to the cheap tier
- code never routes to Nova Micro
- high uncertainty falls back to Claude Haiku

The API now accepts:

```json
{
  "prompt": "write a fastapi endpoint",
  "refinement": "brief"
}
```

`refinement` can be `brief`, `bullet`, or `detailed`.

The response includes the routed model plus explainable debug fields such as `task`, `complexity`, `uncertainty`, `prefilter`, `used_qwen`, `decision_path`, `reason`, latency, tokens, and estimated cost.

## Run Locally

Use one command from the repo root:

```bash
./run_dispatch.sh
```

Then open:

```text
http://127.0.0.1:8000/app/
```

The API stays available at:

```text
http://127.0.0.1:8000/ask
http://127.0.0.1:8000/health
```

## Share On Your Local Network

Run with:

```bash
HOST=0.0.0.0 ./run_dispatch.sh
```

Then open this from another computer on the same Wi-Fi:

```text
http://YOUR_COMPUTER_IP:8000/app/
```

## Team Workflow

1. Push this repo to GitHub.
2. Teammates clone the repo.
3. Create a virtual environment and install dependencies:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r backend/requirements.txt
```

4. Run:

```bash
./run_dispatch.sh
```

## Important Note

GitHub helps you collaborate on the codebase, but GitHub alone does not host a live FastAPI app for everyone on the internet. For public access outside your local network, deploy the app to a real host such as Render, Railway, Fly.io, EC2, or another server.
