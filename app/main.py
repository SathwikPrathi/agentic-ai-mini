from __future__ import annotations

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import Settings, get_settings
from app.core.logging import configure_logging, get_logger
from app.schemas import QueryRequest, QueryResponse, StepResult
from app.service import AgenticAIService


logger = get_logger(__name__)


def get_service(settings: Settings = Depends(get_settings)) -> AgenticAIService:
    return AgenticAIService(settings)


app = FastAPI(title="Agentic AI Mini-Project", version="1.0.0")

# Optional CORS for quick front-end testing
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _startup() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    logger.info("startup env=%s model=%s llm_configured=%s", settings.app_env, settings.model, bool(settings.openai_api_key))


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/query", response_model=QueryResponse)
async def query(req: QueryRequest, svc: AgenticAIService = Depends(get_service)) -> QueryResponse:
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="query must not be empty")

    try:
        result = await svc.handle_query(req.query, use_llm=req.use_llm)
        steps = [StepResult(**s) for s in result["steps"]]
        return QueryResponse(
            trace_id=result["trace_id"],
            final_answer=result["final_answer"],
            plan=result["plan"],
            steps=steps,
            warnings=result.get("warnings", []),
        )
    except Exception as e:  # noqa: BLE001
        logger.exception("/query failed")
        raise HTTPException(status_code=500, detail=str(e)) from e
