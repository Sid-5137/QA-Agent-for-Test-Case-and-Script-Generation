import json
import os
from textwrap import dedent

from backend.vector_store.chroma_store import ChromaDB
from backend.utils.model_selector import ModelSelector


class TestGenerationAgent:
    def __init__(self):
        self.llm = ModelSelector().choose(task="test")

    def _format_context(self, docs):
        formatted = []
        for idx, doc in enumerate(docs, 1):
            meta = doc.get("metadata", {})
            source = meta.get("source_document") or meta.get("source") or "unknown"
            formatted.append(f"[Doc {idx}: {source}]\n{doc['text']}")
        return "\n\n".join(formatted)

    def _parse_cases(self, raw_text):
        cleaned = raw_text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`")
            if "json" in cleaned[:10].lower():
                cleaned = cleaned.split("\n", 1)[-1]

        if '[' in cleaned and ']' in cleaned:
            start = cleaned.find('[')
            end = cleaned.rfind(']')
            cleaned = cleaned[start:end+1]

        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError:
            return []

        normalized = []
        for idx, case in enumerate(data, 1):
            if isinstance(case, str):
                parsed = {}
                for line in case.splitlines():
                    if ":" not in line:
                        continue
                    key, value = line.split(":", 1)
                    parsed[key.strip()] = value.strip()
                case = parsed
            if not isinstance(case, dict):
                continue

            tid = case.get("Test_ID") or case.get("id") or f"TC-{idx:03d}"
            grounded = case.get("Grounded_In", [])
            if isinstance(grounded, str):
                grounded = [grounded]
            feature = self._pick_field(case, ["Feature", "feature", "Title", "Test_Title"]) or ""
            scenario = self._pick_field(
                case,
                ["Test_Scenario", "Scenario", "Steps", "Description", "Flow"],
            ) or ""
            expected_result = self._pick_field(
                case,
                ["Expected_Result", "Expected", "Outcome", "Result"],
            ) or ""
            normalized.append(
                {
                    "id": tid,
                    "feature": feature,
                    "scenario": scenario,
                    "expected_result": expected_result,
                    "grounded_in": grounded,
                    "raw_block": dedent(
                        f"""
                        Test_ID: {tid}
                        Feature: {feature}
                        Test_Scenario: {scenario}
                        Expected_Result: {expected_result}
                        Grounded_In: {case.get('Grounded_In', [])}
                        """
                    ).strip(),
                }
            )

        return normalized

    @staticmethod
    def _pick_field(case: dict, keys: list[str]):
        for key in keys:
            value = case.get(key)
            if value:
                return value
        return ""

    def generate(self, docs_path: str, query: str, k: int = 5):
        vector_path = os.path.join(docs_path, "vector_db")
        db = ChromaDB(persist_directory=vector_path)
        docs = db.similarity_search(query, k=k)

        if not docs:
            raise ValueError("No documentation context available for the query.")

        context = self._format_context(docs)
        prompt = dedent(
            f"""
            You are a senior QA engineer. Based strictly on the provided documentation chunks, produce
            a JSON array of comprehensive test cases that cover both positive and negative paths.

            Requirements:
            - Cite the exact source document(s) for every test via the "Grounded_In" field (array of filenames).
            - Do not invent functionality beyond the context.
            - Return ONLY raw JSON (no markdown fences, no commentary).
            - JSON schema per element:
              {{
                "Test_ID": "TC-XXX",
                "Feature": "...",
                "Test_Scenario": "...",
                "Expected_Result": "...",
                "Grounded_In": ["product_specs.md"]
              }}

            Documentation Chunks:
            {context}

            User Query: {query}
            """
        )

        result = self.llm.invoke(prompt)
        cases = self._parse_cases(result.content)
        if not cases:
            raise ValueError("Unable to parse structured test cases from the model response.")

        return {
            "query": query,
            "docs_used": docs,
            "test_cases": cases,
            "raw_response": result.content,
        }
