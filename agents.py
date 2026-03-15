import json
import re
from groq import Groq


def _clean_json(text: str) -> str:
    text = re.sub(r"```(?:json)?\s*", "", text)
    text = re.sub(r"```\s*", "", text)
    return text.strip()


def _ask(api_key: str, prompt: str, max_tokens: int = 3500) -> str:
    client = Groq(api_key=api_key)
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=max_tokens,
        temperature=0.5,
    )
    return response.choices[0].message.content


# ── Scope Agent ────────────────────────────────────────────────────────────────

def generate_scope(api_key: str, project_name: str, description: str) -> str:
    prompt = f"""You are a certified Project Management Professional (PMP) with 20 years experience.
Based on the project below, produce a detailed, formal Project Scope Statement.

Use EXACTLY this markdown structure. Do NOT include a top-level "## Project Scope Statement" heading:

**Project Title:** {project_name}

### 1. Project Purpose & Justification
[2-3 sentences explaining WHY this project exists and what business/social problem it solves]

### 2. Project Objectives (SMART)
[5-6 bullet points, each a specific measurable objective with numbers and timeframes]

### 3. Project Deliverables
[Numbered list of all tangible outputs]

### 4. In-Scope Items
[Bullet list of work explicitly INCLUDED]

### 5. Out-of-Scope Items
[Bullet list of work explicitly EXCLUDED — be specific to avoid scope creep]

### 6. Constraints
[Bullet list: budget, time, technology, regulatory, resource limitations from the input]

### 7. Assumptions
[Bullet list of planning assumptions]

### 8. Key Stakeholders
[Table or list: Name/Role and their interest]

### 9. Acceptance Criteria & Success Metrics
[How will success be measured? Include KPIs]

Be thorough, specific, and realistic. Infer sensible details where needed.

Project Description:
{description}"""

    return _ask(api_key, prompt, 2800)


# ── Risk Agent ─────────────────────────────────────────────────────────────────

def generate_risks(api_key: str, scope: str) -> list:
    prompt = f"""You are a senior Risk Manager (PMP + PMI-RMP certified).
Analyse the scope statement and identify 12 realistic, diverse risks.

Return ONLY a valid JSON array. No markdown, no explanation.
Schema:
{{
  "risk_id": "R1",
  "risk_name": "Short name (5 words max)",
  "category": "Technical",
  "description": "2-sentence description of what could go wrong and consequences.",
  "likelihood": "High",
  "impact": "Medium",
  "risk_score": "High",
  "mitigation_strategy": "2-3 concrete actions to reduce likelihood or impact.",
  "contingency_plan": "What to do if the risk materialises."
}}

Rules:
  category   → Technical | Financial | Schedule | Resource | External | Organizational | Legal
  likelihood → High | Medium | Low
  impact     → High | Medium | Low
  risk_score → High×High=High | High×Med=High | Med×Med=Medium | Low×anything=Low

Return ONLY the JSON array.

Scope Statement:
{scope}"""

    raw = _ask(api_key, prompt, 3500)
    return json.loads(_clean_json(raw))


# ── WBS / CPM Agent ────────────────────────────────────────────────────────────

def generate_wbs(api_key: str, scope: str, project_name: str) -> dict:
    prompt = f"""You are a Principal Project Manager. Build a detailed WBS and CPM/PERT network.

Return ONLY valid JSON. No markdown. No explanation. No code fences.
Schema:
{{
  "wbs": [
    {{"id": "1",     "name": "Phase Name",       "level": 1}},
    {{"id": "1.1",   "name": "Work Package",      "level": 2}},
    {{"id": "1.1.1", "name": "Task",               "level": 3}}
  ],
  "tasks": [
    {{
      "task_id":      "T1",
      "task_name":    "Clear descriptive task name",
      "wbs_ref":      "1.1.1",
      "phase":        "Initiation",
      "optimistic":   3,
      "most_likely":  5,
      "pessimistic":  9,
      "dependencies": [],
      "resource":     "Role title",
      "deliverable":  "What this task produces"
    }}
  ]
}}

STRICT RULES:
- Create exactly 15-18 tasks covering: Initiation, Planning, Execution, Monitoring & Control, Closure
- Cover ALL major work identified in the scope — be thorough and project-specific
- Durations are integers in DAYS; optimistic < most_likely < pessimistic ALWAYS
- At least 30% of tasks must have dependencies creating parallel paths (not just a single chain)
- Create BOTH critical path tasks AND non-critical parallel tasks so float exists
- First 1-2 tasks have empty dependencies []
- NO circular dependencies — verify carefully
- task_ids: T1, T2, T3 ... sequentially
- Include at least 3 parallel work streams where tasks can happen simultaneously
- Return ONLY valid JSON

Project: {project_name}
Scope:
{scope}"""

    raw = _ask(api_key, prompt, 4000)
    return json.loads(_clean_json(raw))
