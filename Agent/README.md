# Delphi Agents

Small Agentspan examples for weather, reasoning, and project planning.

## Setup

Create or refresh the project environment with:

```bash
uv sync
```

Create a `.env` file in this directory and set one provider key:

```dotenv
OPENROUTER_API_KEY=your_key_here
TAVILY_API_KEY=your_tavily_key_here
REPLICATE_API_TOKEN=your_replicate_token_here
REPLICATE_VIDEO_MODEL=owner/text-to-video-model
HF_TOKEN=your_huggingface_read_token_here
```

Do not commit `.env` or expose the key in source code.

## Run an agent

Run scripts through the project environment so the correct dependencies and
Agentspan launcher are used:

```bash
uv run python weather.py
uv run python reason.py
uv run python planner.py
uv run python design.py
```

Agentspan starts its local runtime server automatically when an agent is run.
The planner task is defined in `planner.py`; it reviews the project and returns
a Markdown implementation plan without modifying files.

## Files

- `weather.py` — weather example with a weather tool.
- `reason.py` — reasoning example with web search.
- `planner.py` — planning agent and its read-only project-review task.
- `design.py` — document generation plus Replicate-backed AI image and video generation.
- `example.json` — sample project data used as input context when relevant.
