import asyncio
import json
import logging
import uuid
from typing import Optional

from agents.crawler_agent import crawl_papers
from agents.extractor_agent import extract_all_papers
from agents.graph_agent import build_knowledge_graph
from agents.synthesis_agent import generate_all_outputs
from agents.confidence_agent import score_claims
from vector.chroma_store import store_papers
from graph.knowledge_graph import get_graph

logger = logging.getLogger(__name__)

_sessions: dict[str, dict] = {}
_status_queues: dict[str, asyncio.Queue] = {}


def get_session(session_id: str) -> Optional[dict]:
    return _sessions.get(session_id)


def create_session(question: str) -> str:
    session_id = str(uuid.uuid4())
    _sessions[session_id] = {
        "session_id": session_id,
        "question": question,
        "status": "pending",
        "papers": [],
        "summary": "",
        "contradictions": "",
        "gaps": "",
        "error": None,
    }
    _status_queues[session_id] = asyncio.Queue()
    logger.info(f"Created session {session_id} for question: '{question[:60]}'")
    return session_id


def get_status_queue(session_id: str) -> Optional[asyncio.Queue]:
    return _status_queues.get(session_id)


def _filter_relevant_papers(papers: list[dict], query: str) -> tuple[list[dict], list[dict]]:
    from embeddings_client import embed_text, embed_texts, cosine_similarity

    query_emb = embed_text(query)
    texts = [f"{p.get('title', '')}. {p.get('abstract', '')[:300]}" for p in papers]
    all_embeddings = embed_texts(texts)

    scored = []
    for paper, emb in zip(papers, all_embeddings):
        score = cosine_similarity(query_emb, emb)
        paper["relevance_score"] = round(score, 3)
        scored.append((score, paper))

    scored.sort(key=lambda x: x[0], reverse=True)

    relevant = [p for s, p in scored if s >= 0.35]
    if len(relevant) < 3:
        relevant = [p for s, p in scored if s >= 0.20][:5]

    all_papers = [p for _, p in scored]

    logger.info(f"Relevance filter: {len(relevant)}/{len(papers)} papers passed")
    return relevant, all_papers


async def run_research_pipeline(
    session_id: str,
    max_papers: int = 30,
    depth: int = 2,
):
    session = _sessions.get(session_id)
    if not session:
        logger.error(f"Session {session_id} not found")
        return

    session["status"] = "running"
    queue = _status_queues.get(session_id)
    loop = asyncio.get_event_loop()

    async def status_callback(event: str, detail: str, progress: int):
        if queue:
            await queue.put({"event": event, "detail": detail, "progress": progress})

    try:
        question = session["question"]

        await status_callback("started", f"🚀 Starting research on: {question[:80]}", 1)
        papers = await crawl_papers(
            query=question, max_papers=max_papers, depth=depth,
            status_callback=status_callback,
        )
        if not papers:
            raise Exception("No papers found. Try a different search term.")

        await status_callback("crawling", "📄 Downloading PDF text from arXiv papers...", 52)
        from tools.pdf_extractor import enrich_papers_with_pdf
        papers = await loop.run_in_executor(None, enrich_papers_with_pdf, papers)

        await status_callback("filtering", "🎯 Filtering for relevant papers...", 54)
        relevant_papers, all_papers_scored = _filter_relevant_papers(papers, question)
        await status_callback(
            "filtering",
            f"🎯 Kept {len(relevant_papers)} relevant, filtered {len(papers) - len(relevant_papers)} off-topic",
            56,
        )
        session["papers"] = all_papers_scored

        relevant_papers = await extract_all_papers(
            papers=relevant_papers, status_callback=status_callback,
        )

        relevant_ids = {p.get("title", "")[:60] for p in relevant_papers}
        final_papers = list(relevant_papers)
        for p in all_papers_scored:
            if p.get("title", "")[:60] not in relevant_ids:
                final_papers.append(p)
        session["papers"] = final_papers

        await status_callback("scoring", "📊 Scoring claim confidence...", 72)
        relevant_papers = score_claims(relevant_papers)
        scored_map = {p.get("title", ""): p.get("scored_claims", []) for p in relevant_papers}
        for p in final_papers:
            if p.get("title", "") in scored_map:
                p["scored_claims"] = scored_map[p["title"]]

        await status_callback("indexing", "📂 Indexing in vector database...", 74)
        store_papers(session_id, relevant_papers)

        graph_result = await build_knowledge_graph(
            session_id=session_id, papers=relevant_papers,
            status_callback=status_callback,
        )

        outputs = await generate_all_outputs(
            question=question,
            papers=relevant_papers,
            contradictions=graph_result.get("contradictions", []),
            status_callback=status_callback,
        )

        session["summary"] = outputs["summary"]
        session["contradictions"] = outputs["contradictions"]
        session["gaps"] = outputs["gaps"]
        session["status"] = "completed"
        session["papers"] = [
            {k: v for k, v in p.items() if k != "embedding"}
            for p in final_papers
        ]

        await status_callback(
            "completed",
            f"🎉 Done! {len(relevant_papers)} relevant papers analyzed.",
            100,
        )
        logger.info(f"Session {session_id} completed: {len(relevant_papers)} papers")

    except Exception as e:
        logger.error(f"Pipeline error for session {session_id}: {e}", exc_info=True)
        session["status"] = "failed"
        session["error"] = str(e)
        if queue:
            await queue.put({"event": "error", "detail": f"❌ {str(e)}", "progress": -1})
    finally:
        if queue:
            await queue.put(None)
