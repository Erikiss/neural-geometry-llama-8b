from pydantic import BaseModel


class PromptItem(BaseModel):
    prompt: str
    answer: str


class ConceptSpec(BaseModel):
    concept_name: str
    values: list[str]
    is_cyclic: bool
    prompts: list[PromptItem]


class QueryRequest(BaseModel):
    concept: str
    layer: int = 28


class QueryResult(BaseModel):
    cache_hit: bool
    concept_name: str
    layer: int
    is_cyclic: bool
    values: list[str]
    prompts: list[PromptItem]
    figure: dict
    pca_variance: list[float]
    n_prompts: int
