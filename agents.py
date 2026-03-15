import json
import re
from groq import Groq


def _clean_json(text: str) -> str:
    text = re.sub(r"```(?:json)?\s*", "", text)
    text = re.sub(r"```\s*", "", text)
    return text.strip()


def _ask(api_key: str, prompt: str, max_tokens: int = 3000) -> str:
    client = Groq(api_key=api_key)
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=max_tokens,
        temperature=0.7,
    )
    return response.choices[0].message.content


# ── Scope Agent ────────────────────────────────────────────────────────────────

def generate_scope(api_key: str, project_name: str, description: str) -> str:
    prompt = f"""You are a certified Project Management Professional (PMP).
Based on the project description below, produce a complete, formal Project Scope Statement.

Use the following structure exactly (markdown headers and bullet points):

## Project Scope Statement

**Project Title:** {project_name}

### 1. Project Purpose & Justification
Why is this project being undertaken? What business problem does it solve?

### 2. Project Objectives (SMART)
List 4-6 SMART goals (Specific, Measurable, Achievable, Relevant, Time-bound).

### 3. Project Deliverables
List all tangible outputs the project must produce.

### 4. In-Scope Items
What work IS included in this project?

### 5. Out-of-Scope Items
What is explicitly NOT included?

### 6. Constraints
Budget, time, technology, regulatory, or resource limitations.

### 7. Assumptions
What are we assuming to be true for planning purposes?

### 8. Key Stakeholders
Who is involved or affected by this project?

### 9. Success Criteria
How will the team know the project succeeded?

Be thorough, professional, and realistic. Infer sensible details from the description.

---
Project Description:
{description}"""

    return _ask(api_key, prompt, max_tokens=2500)


# ── Risk Agent ─────────────────────────────────────────────────────────────────

def generate_risks(api_key: str, scope: str) -> list:
    prompt = f"""You are a senior Risk Manager with PMP and PMI-RMP certifications.
Analyse the project scope statement and identify 10-12 realistic risks.

Return ONLY a valid JSON array with no markdown, no explanation, no code fences.
Each element must follow this schema exactly:
{{
  "risk_id": "R1",
  "risk_name": "Short descriptive name",
  "category": "Technical",
  "description": "What could go wrong and why.",
  "likelihood": "High",
  "impact": "Medium",
  "risk_score": "High",
  "mitigation_strategy": "Concrete steps to reduce likelihood or impact."
}}

Allowed values:
  category   -> Technical | Financial | Schedule | Resource | External | Organizational
  likelihood -> High | Medium | Low
  impact     -> High | Medium | Low
  risk_score -> High x High=High | High x Med=High | Med x Med=Medium | Low x any=Low

Return ONLY the JSON array, nothing else.

---
Project Scope Statement:
{scope}"""

    raw = _ask(api_key, prompt, max_tokens=3000)
    return json.loads(_clean_json(raw))


# ── WBS / CPM Agent ────────────────────────────────────────────────────────────

def generate_wbs(api_key: str, scope: str, project_name: str) -> dict:
    prompt = f"""You are an expert Project Manager building a Work Breakdown Structure and task network for CPM/PERT analysis.

Return ONLY a valid JSON object with no markdown, no explanation, no code fences.
Use this exact schema:
{{
  "wbs": [
    {{"id": "1",     "name": "Phase name",        "level": 1}},
    {{"id": "1.1",   "name": "Work package name",  "level": 2}},
    {{"id": "1.1.1", "name": "Task name",           "level": 3}}
  ],
  "tasks": [
    {{
      "task_id":      "T1",
      "task_name":    "Short clear task name",
      "wbs_ref":      "1.1.1",
      "optimistic":   2,
      "most_likely":  4,
      "pessimistic":  8,
      "dependencies": [],
      "resource":     "Role responsible"
    }}
  ]
}}

Hard rules:
- Create exactly 13-15 tasks covering the full project lifecycle.
- All durations are integers in DAYS; optimistic < most_likely < pessimistic always.
- dependencies is a list of task_ids that must finish before this task starts.
- First task has empty dependencies [].
- NO circular dependencies.
- task_ids must be T1, T2, T3 etc sequentially.
- Return ONLY valid JSON, nothing else.

Project Name: {project_name}
---
Project Scope Statement:
{scope}"""

    raw = _ask(api_key, prompt, max_tokens=3500)
    return json.loads(_clean_json(raw))
