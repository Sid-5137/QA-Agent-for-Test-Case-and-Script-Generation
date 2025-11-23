import ast
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from bs4 import BeautifulSoup


class ScriptValidationError(ValueError):
    """Raised when a script cannot be parsed or validated."""


@dataclass
class Locator:
    by: str
    value: str
    lineno: int


class _LocatorExtractor(ast.NodeVisitor):
    """AST visitor that extracts locator tuples from Selenium-style code."""

    def __init__(self) -> None:
        self.locators: List[Locator] = []

    def visit_Call(self, node: ast.Call) -> Any:
        attr = getattr(getattr(node, "func", None), "attr", "")
        if attr in {"find_element", "find_element_by_id", "find_element_by_name", "find_element_by_css_selector"}:
            locator = self._from_args(node)
            if locator:
                self.locators.append(locator)

        for arg in list(node.args) + [kw.value for kw in node.keywords]:
            locator = self._from_tuple(arg, node)
            if locator:
                self.locators.append(locator)

        self.generic_visit(node)

    def _from_args(self, node: ast.Call) -> Optional[Locator]:
        if len(node.args) < 2:
            return None
        by = self._resolve_by(node.args[0])
        value = self._resolve_value(node.args[1])
        if by and value:
            return Locator(by=by, value=value, lineno=getattr(node, "lineno", 0))
        return None

    def _from_tuple(self, arg: ast.AST, node: ast.Call) -> Optional[Locator]:
        if not isinstance(arg, ast.Tuple) or len(arg.elts) != 2:
            return None
        by = self._resolve_by(arg.elts[0])
        value = self._resolve_value(arg.elts[1])
        if by and value:
            return Locator(by=by, value=value, lineno=getattr(node, "lineno", 0))
        return None

    @staticmethod
    def _resolve_by(node: ast.AST) -> Optional[str]:
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id == "By":
            return node.attr
        return None

    @staticmethod
    def _resolve_value(node: ast.AST) -> Optional[str]:
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return node.value
        return None


class SeleniumScriptValidator:
    """Lightweight validator that simulates running Selenium selectors against static HTML."""

    def __init__(self, script: str, html: str) -> None:
        self.original_script = script or ""
        self.html = html or ""
        if not self.html.strip():
            raise ScriptValidationError("Checkout HTML is required for validation.")
        self.cleaned_script = self._clean_script(self.original_script)
        self.soup = BeautifulSoup(self.html, "html.parser")

    def _clean_script(self, script: str) -> str:
        stripped = script.strip()
        if stripped.startswith("```"):
            lines = [line for line in stripped.splitlines() if line.strip()]
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            stripped = "\n".join(lines)
        return stripped

    def _parse_tree(self) -> ast.AST:
        try:
            return ast.parse(self.cleaned_script)
        except SyntaxError as exc:
            raise ScriptValidationError(f"Selenium script contains syntax errors: {exc}") from exc

    def _extract_locators(self, tree: ast.AST) -> List[Locator]:
        extractor = _LocatorExtractor()
        extractor.visit(tree)
        return extractor.locators

    def _check_locator(self, locator: Locator) -> Dict[str, Any]:
        by = locator.by.upper()
        value = locator.value
        exists = False
        message = ""
        status = "failed"

        try:
            if by == "ID":
                exists = bool(self.soup.find(id=value))
            elif by == "NAME":
                exists = bool(self.soup.find(attrs={"name": value}))
            elif by == "CSS_SELECTOR":
                exists = bool(self.soup.select(value))
            elif by == "CLASS_NAME":
                exists = bool(self.soup.select(f".{value.replace(' ', '.')}"))
            elif by == "TAG_NAME":
                exists = bool(self.soup.find_all(value))
            elif by == "LINK_TEXT":
                exists = bool(self.soup.find("a", string=lambda text: text and text.strip() == value.strip()))
            elif by == "PARTIAL_LINK_TEXT":
                exists = bool(self.soup.find("a", string=lambda text: text and value.strip() in text))
            elif by == "XPATH":
                status = "skipped"
                message = "XPath validation is skipped; supply CSS/ID selectors for static checks."
            else:
                status = "skipped"
                message = f"Locator strategy {by} is not supported in static validation."
        except Exception as exc:  # pragma: no cover - defensive
            message = f"Error evaluating selector: {exc}"

        if status == "skipped":
            return {
                "lineno": locator.lineno,
                "by": by,
                "value": value,
                "status": status,
                "message": message or "Locator strategy skipped.",
            }

        if exists:
            status = "passed"
            message = "Locator matched element(s) in checkout.html."
        else:
            status = "failed"
            message = "No matching elements found in checkout.html."

        return {
            "lineno": locator.lineno,
            "by": by,
            "value": value,
            "status": status,
            "message": message,
        }

    def _html_checks(self) -> List[Dict[str, Any]]:
        forms = len(self.soup.find_all("form"))
        inputs = len(self.soup.find_all("input"))
        buttons = len(self.soup.select("button, input[type='submit'], .btn, .button"))
        totals = len(self.soup.select("[id*='total'], [class*='total']"))

        def pack(name: str, count: int, minimum: int = 1, detail: str = "") -> Dict[str, Any]:
            status = "ok" if count >= minimum else "warn"
            message = detail or ("Found" if count else "Missing")
            return {"check": name, "count": count, "status": status, "message": message}

        return [
            pack("Forms", forms, 1, "Checkout form present" if forms else "No <form> tag detected"),
            pack("Inputs", inputs, 2, "Input fields available" if inputs else "No <input> controls located"),
            pack("CTA Buttons", buttons, 1, "Button/submit control present" if buttons else "No actionable button found"),
            pack("Total Summary", totals, 1, "Total/summary block present" if totals else "No pricing summary detected"),
        ]

    def run(self) -> Dict[str, Any]:
        tree = self._parse_tree()
        locators = self._extract_locators(tree)

        locator_results = [self._check_locator(locator) for locator in locators]
        summary = {
            "total_locators": len(locator_results),
            "passed_locators": sum(1 for item in locator_results if item["status"] == "passed"),
            "failed_locators": sum(1 for item in locator_results if item["status"] == "failed"),
            "skipped_locators": sum(1 for item in locator_results if item["status"] == "skipped"),
        }
        summary["overall_status"] = "ok" if summary["failed_locators"] == 0 else "warn"

        return {
            "summary": summary,
            "locator_results": locator_results,
            "html_checks": self._html_checks(),
        }