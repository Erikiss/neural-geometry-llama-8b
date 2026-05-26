import os
from openai import AsyncOpenAI
from models import ConceptSpec, PromptItem

client = AsyncOpenAI(api_key=os.environ["OPENAI_API_KEY"])

SYSTEM_PROMPT = """You analyze concepts for neural geometry visualization in large language models.

Given a user's concept query, you will:
1. Identify the discrete ordered values/categories of the concept (4–12 values ideal)
2. Generate diverse probing prompts — each with an unambiguous single answer that IS one of the values
3. Every value must appear as the answer roughly the same number of times — balanced coverage is critical for clean geometry
4. Generate a healthy dataset: aim for at least 5 prompts per value, more is better
5. Determine if the concept is cyclic (wraps around) or linear (has endpoints)

Prompt variety guidelines — mix these types:
- Arithmetic:    "What day is 2 days after Monday?" → Wednesday
- Completion:    "The day before Friday is?" → Thursday
- Common knowledge: "The first day of the work week is?" → Monday
- Context:       "If today is Sunday, tomorrow is?" → Monday

Concept examples:
"days of the week" → values: ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"], cyclic: true
"months of the year" → values: ["January",...,"December"], cyclic: true
"seasons" → values: ["Spring","Summer","Autumn","Winter"], cyclic: true
"temperature from cold to hot" → values: ["Freezing","Cold","Cool","Warm","Hot","Boiling"], cyclic: false
"musical notes" → values: ["C","D","E","F","G","A","B"], cyclic: true
"planets from sun" → values: ["Mercury","Venus","Earth","Mars","Jupiter","Saturn","Uranus","Neptune"], cyclic: false

Before finalising, verify: does each value appear as an answer at least 5 times? If any value is under-represented, add more prompts for it.

Output valid JSON only — no markdown, no explanation:
{
  "concept_name": "...",
  "values": ["...", "..."],
  "is_cyclic": true,
  "prompts": [
    {"prompt": "...", "answer": "..."},
    ...
  ]
}"""


async def generate_prompts(concept: str) -> ConceptSpec:
    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": concept},
        ],
        response_format={"type": "json_object"},
        temperature=0.7,
    )
    raw = response.choices[0].message.content
    import json
    data = json.loads(raw)
    return ConceptSpec(
        concept_name=data["concept_name"],
        values=[str(v) for v in data["values"]],
        is_cyclic=bool(data["is_cyclic"]),
        prompts=[PromptItem(prompt=p["prompt"], answer=str(p["answer"])) for p in data["prompts"]],
    )


async def embed_query(text: str) -> list[float]:
    response = await client.embeddings.create(
        model="text-embedding-3-small",
        input=text,
    )
    return response.data[0].embedding
