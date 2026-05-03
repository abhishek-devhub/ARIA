import logging

from fastapi import APIRouter, HTTPException

from agents.orchestrator import get_session
from graph.knowledge_graph import get_graph
from graph.graph_export import generate_summary_stats

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["graph"])


@router.get("/graph/{session_id}")
async def get_graph_data(session_id: str):
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    kg = get_graph(session_id)
    graph_data = kg.export()

    return graph_data


@router.get("/graph/{session_id}/stats")
async def get_graph_stats(session_id: str):
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    kg = get_graph(session_id)
    stats = generate_summary_stats(kg)

    return stats
