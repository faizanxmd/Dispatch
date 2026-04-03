# Dispatch AI

Dispatch AI is a multi-model routing system built for **HACK 'A' WAR 2026** at **MSRIT**. It uses FastAPI and AWS Bedrock to route prompts across different foundation models based on task type, complexity, ambiguity, and cost.

This repository reflects the shared hackathon project build.

## What It Does

- routes prompts across multiple Bedrock models instead of using one model for everything
- uses Qwen only when a prompt is ambiguous enough to justify classification
- tracks routing path, latency, token usage, and pricing
- exposes both the router-selected model and the actually served model when fallback happens
- serves the frontend and backend from one FastAPI app

## Model Stack

- Amazon Nova Micro
- Mistral
- Moonshot Kimi K2.5
- Amazon Nova Pro
- Z.AI GLM 5
- Qwen3 Next 80B A3B
- Claude Sonnet 4.6 benchmark for savings comparison

## Tech Stack

- FastAPI
- Python
- AWS Bedrock
- HTML, CSS, JavaScript

## Run Locally

```bash
git clone https://github.com/faizanxmd/hackathon.git
cd hackathon
python3 -m venv venv
source venv/bin/activate
pip install -r backend/requirements.txt
```

Set your AWS credentials before running:

```bash
export AWS_REGION=us-east-1
export AWS_ACCESS_KEY_ID=YOUR_ACCESS_KEY_ID
export AWS_SECRET_ACCESS_KEY=YOUR_SECRET_ACCESS_KEY
export AWS_SESSION_TOKEN=YOUR_SESSION_TOKEN
```

Start the app:

```bash
./run_dispatch.sh
```

Open:

```text
http://127.0.0.1:8000/app/
```

Health check:

```text
http://127.0.0.1:8000/health
```

If port `8000` is busy:

```bash
PORT=8010 ./run_dispatch.sh
```

## API

### `POST /ask`

```json
{
  "prompt": "write a fastapi endpoint",
  "refinement": "brief"
}
```

Supported refinement modes:

- `brief`
- `bullet`
- `detailed`

The response includes:

- `response`
- `model_used`
- `debug.task`
- `debug.complexity`
- `debug.uncertainty`
- `debug.used_qwen`
- `debug.decision_path`
- `debug.latency_ms`
- token metadata
- pricing and savings metadata

## Notes

- if you only see `{"status":"Backend running"}`, open `/app/` instead of `/`
- Bedrock access must be enabled in your AWS account for the models used here
- `AWS_SESSION_TOKEN` is only needed for temporary credentials
