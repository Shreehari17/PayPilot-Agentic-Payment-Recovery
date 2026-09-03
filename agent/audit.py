import json
from datetime import datetime
from pathlib import Path


AUDIT_DIR = Path("audit")
AUDIT_FILE = AUDIT_DIR / "audit_log.jsonl"


def log_investigation(
    user_query: str,
    tools_used: list[str],
    final_response: str
):
    AUDIT_DIR.mkdir(exist_ok=True)

    record = {
        "timestamp": datetime.now().isoformat(),
        "user_query": user_query,
        "tools_used": tools_used,
        "final_response": final_response,
        "recovery_executed": False
    }

    with open(AUDIT_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")