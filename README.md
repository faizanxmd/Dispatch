# Dispatch AI

Dispatch AI is a FastAPI app with a built-in frontend for explainable multi-model routing on AWS Bedrock.

## What It Does

- Routes prompts across multiple Bedrock models based on task, complexity, uncertainty, and cost
- Uses Qwen only for ambiguous prompts
- Tracks latency, tokens, and savings
- Serves both the API and the frontend from one app

## Current Stack

- Amazon Nova Micro: simple factual prompts
- Mistral: cheap general prompts
- Moonshot Kimi K2.5: safe reasoning and fallback
- Amazon Nova Pro: code and failover
- Z.AI GLM 5: strong reasoning
- Qwen3 Next 80B A3B: classifier only
- Claude Sonnet 4.6: benchmark for savings comparison only

## API

`POST /ask`

```json
{
  "prompt": "write a fastapi endpoint",
  "refinement": "brief"
}
```

`refinement` supports `brief`, `bullet`, and `detailed`.

The response includes the routed model plus debug fields like `task`, `complexity`, `uncertainty`, `used_qwen`, `decision_path`, `latency_ms`, `token_count`, and pricing metadata.

## Run Locally

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r backend/requirements.txt
./run_dispatch.sh
```

Open:

```text
http://127.0.0.1:8000/app/
```

## Deploy

The repo is set up for both Render and Vercel.

### Vercel

- [vercel.json](vercel.json) routes requests into the FastAPI app
- [api/index.py](api/index.py) is the Vercel Python entrypoint
- [requirements.txt](requirements.txt) exposes the Python dependencies at the project root

Required environment variables:

- `AWS_REGION`
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `AWS_SESSION_TOKEN` if your AWS credentials require it

Official docs:

- [Vercel FastAPI guide](https://vercel.com/docs/frameworks/backend/fastapi)
- [Vercel Python runtime](https://vercel.com/docs/functions/runtimes/python)
- [Vercel project configuration](https://vercel.com/docs/project-configuration/vercel-json)

### Render

The repo also includes [render.yaml](render.yaml) for a simple Render web service deploy.
