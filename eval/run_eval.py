"""Run the evaluation set through the full pipeline and report routing, retrieval and answer quality.

Run: python -m eval.run_eval
Makes real API calls (about 2-3 per question).
"""

import json
import re
import statistics
import time
from pathlib import Path

from src.agent import Agent
from src.retrieval import Retriever

EVAL_DIR = Path("eval")
QUESTIONS_PATH = EVAL_DIR / "questions.jsonl"
RESULTS_JSON = EVAL_DIR / "results.json"
RESULTS_MD = EVAL_DIR / "results.md"
TOP_K = 5


def load_cases() -> list[dict]:
    return [json.loads(line) for line in QUESTIONS_PATH.read_text(encoding="utf-8").splitlines() if line.strip()]


def matches_any(texts: list[str], patterns: list[str]) -> bool:
    """True if any expected section substring appears in any of the given section names."""
    return any(p.lower() in t.lower() for t in texts for p in patterns)


def run_case(case: dict, retriever: Retriever) -> dict:
    """Run one case through a fresh agent and score it."""
    agent = Agent(retriever=retriever)
    for earlier in case.get("history", []):
        agent.handle(earlier)

    standalone = agent.rewrite_followup(case["question"]) if agent.history else case["question"]
    start = time.perf_counter()
    response = agent.handle(case["question"])
    seconds = time.perf_counter() - start

    actual_route = response.escalation.category.value if response.escalation.escalate else "answer"
    result = {
        "id": case["id"],
        "question": case["question"],
        "expected_route": case["expected_route"],
        "actual_route": actual_route,
        "route_ok": actual_route == case["expected_route"],
        "reason": response.escalation.reason,
        "seconds": round(seconds, 1),
        "answer": response.answer.text if response.answer else None,
        "confidence": response.answer.confidence if response.answer else None,
        "retrieval_hit": None,
        "citation_hit": None,
        "facts_ok": None,
    }

    if case["expected_sections"]:
        # Score the query the agent actually searched with; if it escalated before searching,
        # still score retrieval on the standalone question.
        query = agent.last_search_query or standalone
        retrieved = [rc.chunk.section for rc in retriever.retrieve(query, top_k=TOP_K)]
        result["retrieval_hit"] = matches_any(retrieved, case["expected_sections"])
        if response.answer:
            cited = [c.section for c in response.answer.citations]
            result["citation_hit"] = matches_any(cited, case["expected_sections"])

    if case["expected_facts"] and response.answer:
        result["facts_ok"] = all(re.search(p, response.answer.text, re.IGNORECASE) for p in case["expected_facts"])
    elif case["expected_facts"]:
        result["facts_ok"] = False

    return result


def rate(results: list[dict], key: str) -> tuple[int, int]:
    """(passed, scored) for a metric, ignoring cases where it does not apply (None)."""
    scored = [r[key] for r in results if r[key] is not None]
    return sum(scored), len(scored)


def summarise(results: list[dict]) -> dict:
    should_escalate = [r for r in results if r["expected_route"] != "answer"]
    did_escalate = [r for r in results if r["actual_route"] != "answer"]
    true_escalations = [r for r in did_escalate if r["expected_route"] != "answer"]
    times = [r["seconds"] for r in results]
    return {
        "routing": rate(results, "route_ok"),
        "escalation_precision": (len(true_escalations), len(did_escalate)),
        "escalation_recall": (len(true_escalations), len(should_escalate)),
        "retrieval_hit_at_5": rate(results, "retrieval_hit"),
        "citation_hit": rate(results, "citation_hit"),
        "facts_ok": rate(results, "facts_ok"),
        "median_seconds": round(statistics.median(times), 1),
        "max_seconds": max(times),
    }


def pct(pair: tuple[int, int]) -> str:
    passed, total = pair
    return f"{passed}/{total} ({100 * passed / total:.0f}%)" if total else "n/a"


def write_report(summary: dict, results: list[dict]) -> str:
    tick = {True: "✅", False: "❌", None: "–"}
    lines = [
        "# Evaluation results",
        "",
        f"{len(results)} cases: {sum(r['expected_route'] == 'answer' for r in results)} answerable, "
        f"{sum(r['expected_route'] != 'answer' for r in results)} that should be escalated.",
        "",
        "| Metric | Result | What it measures |",
        "|---|---|---|",
        f"| Routing accuracy | {pct(summary['routing'])} | answered vs escalated, and the right escalation category |",
        f"| Escalation precision | {pct(summary['escalation_precision'])} | of the questions escalated, how many should have been |",
        f"| Escalation recall | {pct(summary['escalation_recall'])} | of the questions that should be escalated, how many were |",
        f"| Retrieval hit@{TOP_K} | {pct(summary['retrieval_hit_at_5'])} | an expected section is in the top {TOP_K} chunks |",
        f"| Citation accuracy | {pct(summary['citation_hit'])} | the answer cites an expected section |",
        f"| Key facts present | {pct(summary['facts_ok'])} | the answer contains the expected fact (e.g. '12 months') |",
        f"| Latency | median {summary['median_seconds']}s, max {summary['max_seconds']}s | time per question, end to end |",
        "",
        "| ID | Question | Expected | Actual | Route | Retrieval | Citation | Facts | Time |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for r in results:
        lines.append(
            f"| {r['id']} | {r['question']} | {r['expected_route']} | {r['actual_route']} | {tick[r['route_ok']]} | "
            f"{tick[r['retrieval_hit']]} | {tick[r['citation_hit']]} | {tick[r['facts_ok']]} | {r['seconds']}s |"
        )
    return "\n".join(lines) + "\n"


def main() -> None:
    cases = load_cases()
    retriever = Retriever()
    results = []
    for case in cases:
        r = run_case(case, retriever)
        flag = "ok  " if r["route_ok"] else "FAIL"
        print(f"{flag} {r['id']}  {r['actual_route']:<17} {r['seconds']:>5}s  {r['question']}")
        results.append(r)

    summary = summarise(results)
    report = write_report(summary, results)
    RESULTS_MD.write_text(report, encoding="utf-8")
    RESULTS_JSON.write_text(json.dumps({"summary": summary, "results": results}, indent=2), encoding="utf-8")
    print("\n" + "\n".join(report.splitlines()[:13]))
    print(f"\nSaved {RESULTS_MD} and {RESULTS_JSON}")


if __name__ == "__main__":
    main()
