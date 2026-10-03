from fastapi import APIRouter

from ..llm.schema import EnrichRequest, EnrichResponse
from ..llm.service import enrich

router = APIRouter()


@router.post("/enrich", response_model=EnrichResponse)
def post_enrich(payload: EnrichRequest) -> EnrichResponse:
    return enrich(payload)
