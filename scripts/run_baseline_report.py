from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from statistics import mean

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from ontology_negotiator.benchmark import run_full_pipeline_benchmark
from ontology_negotiator.text_graph_pipeline import build_graph_from_agent_summary

DATASETS = ["fish_home", "test"]
RUNS_PER_DATASET = 5

CONFIG_PATH = PROJECT_ROOT / "config" / "ontology_negotiator.toml"
ARTIFACT_ROOT = PROJECT_ROOT / "artifacts" / "baseline_report"


def _load_text(dataset_name: str) -> str:
    path = PROJECT_ROOT / "tests" / f"{dataset_name}.txt"
    if not path.exists():
        raise FileNotFoundError(f"Missing dataset text: {path}")
    return path.read_text(encoding="utf-8")


def _build_summary(report: dict[str, object]) -> str:
    lines = [
        "Baseline benchmark summary",
        f"Generated at: {report['generated_at']}",
        "",
    ]

    for dataset_report in report["datasets"]:
        lines.append(f"Dataset: {dataset_report['dataset']}")
        lines.append(f"- runs: {dataset_report['runs']}")
        lines.append(f"- avg_total_seconds: {dataset_report['avg_total_seconds']}")
        lines.append(f"- avg_rounds_per_node: {dataset_report['avg_rounds_per_node']}")
        lines.append(f"- avg_tool_call_success_rate: {dataset_report['avg_tool_call_success_rate']}")
        lines.append(f"- avg_schema_repair_rate: {dataset_report['avg_schema_repair_rate']}")
        lines.append(f"- avg_cache_hit_rate: {dataset_report['avg_cache_hit_rate']}")
        lines.append("")

    return "\n".join(lines)


def main() -> int:
    ARTIFACT_ROOT.mkdir(parents=True, exist_ok=True)
    aggregate: list[dict[str, object]] = []

    for dataset_name in DATASETS:
        text = _load_text(dataset_name)
        graph = build_graph_from_agent_summary(
            text,
            project_key=dataset_name,
            project_name=f"{dataset_name} system",
        )

        run_reports: list[dict[str, object]] = []
        for run_idx in range(1, RUNS_PER_DATASET + 1):
            run_root = ARTIFACT_ROOT / dataset_name / f"run_{run_idx}"
            report = run_full_pipeline_benchmark(
                graph,
                artifact_root=run_root,
                config_path=CONFIG_PATH,
            )
            run_reports.append(report)

        aggregate.append(
            {
                "dataset": dataset_name,
                "runs": RUNS_PER_DATASET,
                "avg_total_seconds": round(mean(float(item["total_seconds"]) for item in run_reports), 6),
                "avg_rounds_per_node": round(mean(float(item.get("avg_rounds_per_node", 0.0)) for item in run_reports), 6),
                "avg_tool_call_success_rate": round(mean(float(item.get("tool_call_success_rate", 0.0)) for item in run_reports), 6),
                "avg_schema_repair_rate": round(mean(float(item.get("schema_repair_rate", 0.0)) for item in run_reports), 6),
                "avg_cache_hit_rate": round(mean(float(item.get("cache_hit_rate", 0.0)) for item in run_reports), 6),
                "runs_detail": run_reports,
            }
        )

    full_report = {
        "generated_at": datetime.now(UTC).isoformat(),
        "datasets": aggregate,
    }

    json_path = ARTIFACT_ROOT / "baseline_report.json"
    summary_path = ARTIFACT_ROOT / "baseline_summary.txt"
    json_path.write_text(json.dumps(full_report, ensure_ascii=False, indent=2), encoding="utf-8")
    summary_path.write_text(_build_summary(full_report), encoding="utf-8")

    print(f"Wrote: {json_path}")
    print(f"Wrote: {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
