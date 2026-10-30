# Spatial AI Interface

A spatial-first AI interface where drawing replaces traditional text prompting.

Users express intent visually through sketches, layouts, annotations, and spatial relationships on an infinite canvas. The system interprets this intent using AI and dynamically generates interactive interfaces, dashboards, workflows, and applications directly from the canvas.

Instead of forcing users to describe ideas linearly through text, Spatial AI Interface enables direct visual thinking and real-time human-AI collaboration.

---

## Features

* Infinite spatial canvas
* Visual prompting system
* AI-powered interface generation
* Groq + Ollama hybrid architecture
* Dynamic UI rendering
* Spatial intent parsing
* Real-time interactive generation
* Structured AI orchestration pipeline
* Tool-switching AI backend
* Extensible multimodal architecture

---

# Tech Stack

## Frontend

* React
* TypeScript
* Vite
* TailwindCSS
* Excalidraw (MIT licensed; no production license key)
* Zustand
* Framer Motion

## Backend

* Python
* FastAPI
* WebSockets
* Pydantic

## AI Layer

* Groq
* Ollama

---

# Project Structure

```txt
project-root/
│
├── frontend/
├── backend/
├── ai-core/
└── README.md
```

---

# Installation

## Clone the Repository

```bash
git clone <your-repo-url>
cd <your-project-folder>
```

---

# Frontend Setup

```bash
cd frontend
npm install
```

---

# Backend Setup

```bash
cd backend

python -m venv venv
```

## Activate Virtual Environment

### macOS / Linux

```bash
source venv/bin/activate
```

### Windows

```bash
venv\\Scripts\\activate
```

---

## Install Backend Dependencies

```bash
python -m pip install -r requirements.txt

# Verify that the same interpreter can import the AI SDK.
venv/bin/python -c "from google import genai; print('google-genai: OK')"
```

---

# Environment Variables

Create a `.env` file inside:

```txt
backend/
```

Add:

```env
GROQ_API_KEY=your_groq_api_key
OLLAMA_URL=http://localhost:11434
```

---

# Ollama Setup

Install Ollama and pull a model locally.

Example:

```bash
ollama pull llama3
```

Start Ollama locally before running the backend.

---

# Running the Project

## Start Backend

```bash
cd backend
# Use the virtual environment's interpreter for both installation and startup.
venv/bin/python -m pip install -r requirements.txt
venv/bin/python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Backend runs on:

```txt
http://localhost:8000
```

## Publishing generated apps

Successful coding-agent generations are published automatically under their
existing project ID. Production setup for the `app.pythios.xyz` subdomain,
secure iframe isolation, and durable Render disk storage is documented in
[PUBLISHING.md](PUBLISHING.md).

---

## Start Frontend

Open a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Frontend runs on:

```txt
http://localhost:5173

The development frontend calls the local backend at `http://localhost:8000`. The production build calls the Render backend configured in `frontend/.env.production`. If the backend is unavailable, the browser-only fallback generator keeps preview generation working.
```

---

# MVP Workflow

1. Draw layouts and structures on the canvas
2. Serialize spatial intent
3. Send canvas state to backend
4. Route request through AI orchestration layer
5. Generate structured interface output
6. Render generated interface dynamically

The implemented MVP also includes a deterministic local generation fallback.
That means the browser interface works without a Groq key or a running Ollama
instance. Add credentials in `backend/.env` when you want external AI routing.

---

# Architecture Overview

## Spatial Canvas

The canvas acts as the primary intent surface.

Users communicate through:

* drawings
* layouts
* text
* positioning
* relationships
* spatial grouping

---

## AI Orchestration

The backend routes tasks between:

* Groq for fast structured generation
* Ollama for local reasoning and routing

The orchestration layer:

* extracts intent
* classifies tasks
* selects tools
* generates structured outputs
* returns renderable interface definitions

---

## Frontend Rendering

Generated outputs are rendered dynamically as:

* interactive interfaces
* dashboards
* components
* workflows
* visual systems

The frontend acts as a spatial runtime for generated applications.

---

# Future Goals

* Incremental regeneration
* Real-time collaborative AI editing
* Multimodal vision understanding
* Selective region updates
* Dynamic tool creation
* Spatial memory systems
* Adaptive generated interfaces
* Local-first AI execution
* Advanced scene graph reasoning

---

# Philosophy

Traditional software forces humans to adapt to tools.

Spatial AI Interface reverses this relationship.

The interface adapts to human intent.

Drawing becomes the native language for interacting with intelligence.

---

# License

MIT
