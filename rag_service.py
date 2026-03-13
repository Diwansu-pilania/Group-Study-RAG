"""
RAG Service
-----------
• Embeds knowledge base documents into ChromaDB
• Retrieves relevant context for a query
• Calls OpenRouter LLM (Llama 3.3 70B free) for generation
"""

import os, json
from typing import Optional
from openai import OpenAI
import chromadb
from chromadb.utils import embedding_functions
from backend.config import get_settings

settings = get_settings()

# ─── Clients ──────────────────────────────────────────────────────────────────

def get_llm_client() -> OpenAI:
    return OpenAI(
        api_key=settings.openrouter_api_key,
        base_url=settings.openrouter_base_url,
    )

def get_chroma_client():
    os.makedirs(settings.chroma_persist_dir, exist_ok=True)
    return chromadb.PersistentClient(path=settings.chroma_persist_dir)

def get_collection():
    client = get_chroma_client()
    emb_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name=settings.embedding_model
    )
    return client.get_or_create_collection(
        name="knowledge_base",
        embedding_function=emb_fn,
        metadata={"hnsw:space": "cosine"}
    )

# ─── Ingest Documents ─────────────────────────────────────────────────────────

def ingest_text(text: str, doc_id: str, metadata: dict = {}):
    """Add a text chunk to the vector store."""
    collection = get_collection()
    collection.upsert(
        documents=[text],
        ids=[doc_id],
        metadatas=[metadata]
    )

def ingest_file(file_path: str):
    """Ingest a .txt or .md file into ChromaDB."""
    with open(file_path, "r", encoding="utf-8") as f:
        text = f.read()

    # Simple chunking — 500 chars with 50 char overlap
    chunk_size, overlap = 500, 50
    chunks = []
    start  = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start = end - overlap

    for i, chunk in enumerate(chunks):
        doc_id = f"{os.path.basename(file_path)}_chunk_{i}"
        ingest_text(chunk, doc_id, {"source": file_path, "chunk": i})

    print(f"✅ Ingested {len(chunks)} chunks from {file_path}")

# ─── Retrieve Context ─────────────────────────────────────────────────────────

def retrieve_context(query: str, n_results: int = 5) -> str:
    """Retrieve top-N relevant chunks for a query."""
    try:
        collection = get_collection()
        results    = collection.query(query_texts=[query], n_results=n_results)
        docs       = results.get("documents", [[]])[0]
        if not docs:
            return ""
        return "\n\n---\n\n".join(docs)
    except Exception as e:
        print(f"⚠️ Retrieval warning: {e}")
        return ""

# ─── LLM Call ─────────────────────────────────────────────────────────────────

def call_llm(system_prompt: str, user_prompt: str,
             temperature: float = 0.7, max_tokens: int = 2000) -> str:
    """Call OpenRouter LLM and return the response text."""
    client = get_llm_client()
    resp   = client.chat.completions.create(
        model=settings.llm_model,
        messages=[
            {"role": "system",  "content": system_prompt},
            {"role": "user",    "content": user_prompt},
        ],
        temperature=temperature,
        max_tokens=max_tokens,
        extra_headers={
            "HTTP-Referer": settings.app_url,
            "X-Title":      settings.app_name,
        }
    )
    return resp.choices[0].message.content

# ─── RAG Pipeline ─────────────────────────────────────────────────────────────

def rag_query(query: str, system_prompt: str,
              n_results: int = 5, temperature: float = 0.7) -> str:
    """Full RAG pipeline: retrieve context → inject → generate."""
    context = retrieve_context(query, n_results)

    user_prompt = f"""Here is some relevant knowledge to help you:

<context>
{context if context else "No specific context found. Use your general knowledge."}
</context>

User request:
{query}"""

    return call_llm(system_prompt, user_prompt, temperature)

# ─── Roadmap Generation ───────────────────────────────────────────────────────

def generate_roadmap(topic: str, goal: str, skill_level: str,
                     duration_days: int) -> dict:
    """Generate a structured learning roadmap as JSON."""

    system_prompt = """You are an expert learning coach and curriculum designer.
Generate a detailed, personalized learning roadmap in strict JSON format.
Be practical, structured, and encouraging. No markdown, only valid JSON."""

    user_prompt = f"""Create a {duration_days}-day learning roadmap for the following:

Topic: {topic}
Goal: {goal}
Current skill level: {skill_level}

Return ONLY a valid JSON object with this exact structure:
{{
  "title": "Roadmap title",
  "overview": "2-3 sentence overview",
  "total_days": {duration_days},
  "skill_level": "{skill_level}",
  "phases": [
    {{
      "phase_number": 1,
      "phase_name": "Phase name",
      "days": "1-7",
      "objective": "What you will achieve",
      "topics": ["topic1", "topic2", "topic3"]
    }}
  ],
  "daily_time_minutes": 45,
  "resources": ["resource1", "resource2"],
  "success_metrics": ["metric1", "metric2"]
}}"""

    raw = rag_query(user_prompt, system_prompt, temperature=0.5)

    # Parse JSON safely
    try:
        # Strip markdown code fences if present
        clean = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        return json.loads(clean)
    except Exception:
        return {"title": topic, "overview": raw, "phases": [], "total_days": duration_days}


# ─── Daily Task Generation ────────────────────────────────────────────────────

def generate_daily_tasks(topic: str, phase_name: str, day_number: int,
                          skill_level: str) -> list[dict]:
    """Generate 3 tasks for a specific day."""

    system_prompt = """You are a learning coach generating daily study tasks.
Return ONLY valid JSON — a list of task objects. No markdown, no explanation."""

    user_prompt = f"""Generate exactly 3 learning tasks for:

Topic: {topic}
Phase: {phase_name}
Day: {day_number}
Skill level: {skill_level}

Return ONLY a JSON array:
[
  {{
    "title": "Short task title",
    "description": "Clear 2-3 sentence description of what to do",
    "task_type": "read",
    "xp_reward": 10,
    "estimated_minutes": 20
  }},
  {{
    "title": "Short task title",
    "description": "Clear 2-3 sentence description",
    "task_type": "quiz",
    "xp_reward": 15,
    "estimated_minutes": 15
  }},
  {{
    "title": "Short task title",
    "description": "Clear 2-3 sentence description",
    "task_type": "project",
    "xp_reward": 25,
    "estimated_minutes": 30
  }}
]

task_type must be one of: read, quiz, project, video"""

    raw = rag_query(user_prompt, system_prompt, temperature=0.6)

    try:
        clean = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        return json.loads(clean)
    except Exception:
        return [{
            "title":       f"Day {day_number} Study",
            "description": "Review today's topic thoroughly.",
            "task_type":   "read",
            "xp_reward":   10,
            "estimated_minutes": 30
        }]


# ─── Assessment ───────────────────────────────────────────────────────────────

def assess_submission(task_title: str, task_description: str,
                       submission: str) -> dict:
    """Assess a user's task submission and return score + feedback."""

    system_prompt = """You are a learning coach evaluating student work.
Be encouraging but honest. Return ONLY valid JSON."""

    user_prompt = f"""Evaluate this student submission:

Task: {task_title}
Task description: {task_description}
Student's submission: {submission}

Return ONLY a JSON object:
{{
  "score": 85,
  "passed": true,
  "feedback": "Specific, encouraging 2-3 sentence feedback",
  "strengths": ["strength1", "strength2"],
  "improvements": ["area1"]
}}

Score is 0-100. passed is true if score >= 60."""

    raw = call_llm(system_prompt, user_prompt, temperature=0.3)

    try:
        clean = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        return json.loads(clean)
    except Exception:
        return {"score": 75, "passed": True,
                "feedback": "Good effort! Keep going.", "strengths": [], "improvements": []}
