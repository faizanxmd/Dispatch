# Dispatch AI

Dispatch AI is a FastAPI app with a built-in frontend for explainable multi-model routing on AWS Bedrock.

Repo: [https://github.com/faizanxmd/hackathon](https://github.com/faizanxmd/hackathon)

## What It Does

- Routes prompts across Bedrock models based on task, complexity, uncertainty, and cost
- Uses Qwen only when a prompt is ambiguous enough to need classification
- Tracks latency, token usage, routing path, and savings
- Serves both the API and the frontend from one FastAPI app

## Model Stack

- Amazon Nova Micro: simple factual and very cheap prompts
- Mistral: cheap general prompts
- Moonshot Kimi K2.5: safer reasoning and fallback path
- Amazon Nova Pro: code generation and execution fallback
- Z.AI GLM 5: strong reasoning and harder math
- Qwen3 Next 80B A3B: classifier only
- Claude Sonnet 4.6: pricing benchmark only

## Prerequisites

- Python 3.11+
- AWS Bedrock access for the models used by this app
- AWS credentials with permission to invoke Bedrock

## Quick Start

### 1. Clone the repo

```bash
git clone https://github.com/faizanxmd/hackathon.git
cd hackathon
```

### 2. Create a virtual environment

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r backend/requirements.txt
```

### 3. Configure AWS credentials

Use either `aws configure` or export environment variables.

Example:

```bash
export AWS_REGION=us-east-1
export AWS_ACCESS_KEY_ID=YOUR_ACCESS_KEY_ID
export AWS_SECRET_ACCESS_KEY=YOUR_SECRET_ACCESS_KEY
export AWS_SESSION_TOKEN=YOUR_SESSION_TOKEN
```

`AWS_SESSION_TOKEN` is only needed if your credentials use temporary sessions.

### 4. Run the app

```bash
./run_dispatch.sh
```

Open the frontend at:

```text
http://127.0.0.1:8000/app/
```

Health check:

```text
http://127.0.0.1:8000/health
```

## Run Options

Use a different port:

```bash
PORT=8010 ./run_dispatch.sh
```

Let other devices on the same Wi-Fi open it too:

```bash
HOST=0.0.0.0 PORT=8000 ./run_dispatch.sh
```

Then open:

```text
http://YOUR_COMPUTER_IP:8000/app/
```

## API

### `POST /ask`

Example request:

```json
{
  "prompt": "write a fastapi endpoint",
  "refinement": "brief"
}
```

Supported `refinement` values:

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
- `debug.prompt_token_count`
- `debug.generation_token_count`
- pricing and savings metadata

## Project Structure

```text
hackathon/
├── backend/
│   ├── main.py
│   ├── model.py
│   ├── router.py
│   ├── routing_pipeline.py
│   └── requirements.txt
├── frontend/
│   ├── index.html
│   ├── analytics.html
│   ├── history.html
│   ├── models.html
│   ├── profile.html
│   ├── settings.html
│   ├── script.js
│   └── style.css
├── render.yaml
└── run_dispatch.sh
```

## Troubleshooting

If you only see:

```json
{"status":"Backend running"}
```

you opened the backend root. Open `/app/` for the actual website.

If port `8000` is already in use:

```bash
PORT=8010 ./run_dispatch.sh
```

If Bedrock calls fail:

- confirm your AWS credentials are valid
- confirm the Bedrock models are enabled in your AWS account
- confirm your region matches the enabled models

## Deploy

Recommended: Render.

This repo includes `render.yaml` for a simple web service deploy.

Required environment variables:

- `AWS_REGION`
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `AWS_SESSION_TOKEN` if needed

Useful docs:

- [Render FastAPI guide](https://render.com/docs/deploy-fastapi)
- [Render web services](https://render.com/docs/web-services)
