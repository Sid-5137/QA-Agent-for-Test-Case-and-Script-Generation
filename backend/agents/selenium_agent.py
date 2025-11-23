import json
from textwrap import indent

from backend.utils.model_selector import ModelSelector


class SeleniumAgent:
    def __init__(self):
        self.llm = ModelSelector().choose(task="selenium")

    def generate(self, test_cases: list, html: str, docs: str):
        formatted_cases = []
        for case in test_cases:
            grounded = ", ".join(case.get("grounded_in", [])) or "n/a"
            formatted_cases.append(
                "\n".join(
                    [
                        f"Test_ID: {case.get('id')}",
                        f"Feature: {case.get('feature')}",
                        f"Scenario: {case.get('scenario')}",
                        f"Expected_Result: {case.get('expected_result')}",
                        f"Grounded_In: {grounded}",
                    ]
                )
            )

        cases_json = json.dumps(test_cases, indent=2)
        pretty_cases = indent(cases_json, " " * 12)

        prompt = f"""
            You are an expert Selenium (Python) automation engineer.

            Selected test cases:
            {"\n\n".join(formatted_cases)}

            Use the structured metadata below inside the Python script:

            TEST_CASES = [
{pretty_cases}
            ]

            Checkout HTML:
            {html}

            Documentation (for grounding):
            {docs}

            Produce a runnable Python Selenium script that **executes every entry in TEST_CASES sequentially**:
            - Load the checkout HTML path from the CHECKOUT_HTML_PATH environment variable (raise a helpful error if it is missing).
            - Define a helper like `def run_case(driver, case_meta): ...` that receives a single test case dictionary and performs the steps.
            - Provide `def run_all_cases():` that launches one ChromeDriver instance per case (or reuses one) and iterates through TEST_CASES in order, logging which case is in progress so the console output matches the playback.
            - Under the `if __name__ == "__main__"` guard, call `run_all_cases()`—never exit after the first test.
            - Use robust selectors (IDs preferred, fallback to CSS/XPath present in the HTML) plus WebDriverWait.
            - Configure Chrome with a headless flag controlled by HEADLESS env var (default "1" = headless).
            - Include try/finally to ensure `driver.quit()` runs even if a case fails so subsequent cases can launch their own driver if needed.
            - Print pass/fail information per case so downstream logs are informative.
            - Assume ChromeDriver is on PATH.
            Return only a Python code block.
            """
        result = self.llm.invoke(prompt)
        return {"selenium_script": result.content}
