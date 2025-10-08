import json
from pathlib import Path

here = Path(__file__).parent
questions_path = here / "questions.jsonl"

print("[eval] Loading questions from:", questions_path)
for line in questions_path.read_text(encoding="utf-8").splitlines():
    q = json.loads(line)
    print(f"- {q['id']}: {q['question']} (expected: {q.get('expected','')})")

print("[eval] This is a placeholder. Integrate with NAT front-end API to automate scoring.")
