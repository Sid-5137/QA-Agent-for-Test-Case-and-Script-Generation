import os
from langgraph.graph import StateGraph

from backend.agents.ingestion_agent import IngestionAgent
from backend.agents.test_case_agent import TestGenerationAgent


class QAState(dict):
    docs_path: str | None = None
    query: str | None = None
    ingestion_result: dict | None = None
    test_cases: str | None = None
    retrieved_docs: list | None = None


def ingest_node(state: QAState):
    agent = IngestionAgent()
    docs_path = state.get("docs_path")

    if not docs_path or not os.path.exists(docs_path):
        state["ingestion_result"] = {
            "status": "error",
            "message": "docs_path missing or invalid"
        }
        return state

    state["ingestion_result"] = agent.ingest(docs_path)
    return state


def test_gen_node(state: QAState):
    if state["ingestion_result"].get("status") == "error":
        return state

    agent = TestGenerationAgent()
    query = state.get("query", "generate test cases")
    docs_path = state.get("docs_path")

    result = agent.generate(docs_path=docs_path, query=query)

    state["test_cases"] = result.get("test_cases")
    state["retrieved_docs"] = result.get("docs_used")
    return state


def build_workflow():
    wf = StateGraph(QAState)

    wf.add_node("ingest", ingest_node)
    wf.add_node("generate_tests", test_gen_node)

    wf.set_entry_point("ingest")
    wf.add_edge("ingest", "generate_tests")
    wf.set_finish_point("generate_tests")

    return wf.compile()
