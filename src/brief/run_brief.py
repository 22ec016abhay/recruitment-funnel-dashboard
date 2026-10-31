"""Generate one live weekly brief (needs GROQ_API_KEY in .env) and save it to docs/sample_brief.md.

    python3 -m src.brief.run_brief
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.brief.brief_generator import generate_brief  # noqa: E402
from src.label_mapping.llm_mapper import get_client  # noqa: E402


def main():
    try:
        client = get_client(provider="groq")
    except RuntimeError as e:
        sys.exit(f"Cannot run live brief: {e}")
    try:
        out = generate_brief(client)
    except Exception as e:  # network, auth or quota errors are reported, not hidden
        sys.exit(f"Live call failed: {type(e).__name__}. Check your key, network and quota.")
    docs = ROOT / "docs"
    docs.mkdir(exist_ok=True)
    (docs / "sample_brief.md").write_text(out["brief"] + "\n", encoding="utf-8")
    (docs / "sample_brief_validation.json").write_text(json.dumps(
        {k: out[k] for k in ("status", "validation", "attempts", "model", "facts_sha256")}, indent=2))
    print(out["status"], "| attempts:", len(out["attempts"]), "| violations:", len(out["validation"]["violations"]))


if __name__ == "__main__":
    main()
