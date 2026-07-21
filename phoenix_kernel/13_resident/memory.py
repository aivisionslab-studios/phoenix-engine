import json
from pathlib import Path

class ResidentMemory:
    def __init__(self):
        self.file_path = Path("data/resident_memory.json")
        self.file_path.parent.mkdir(exist_ok=True)
        self.data = self._load()

    def _load(self):
        if self.file_path.exists():
            return json.loads(self.file_path.read_text(encoding="utf-8"))
        return {"machine": {}, "history": []}

    def save(self):
        self.file_path.write_text(json.dumps(self.data, indent=2), encoding="utf-8")

    def add_history(self, action: str):
        self.data["history"].append({"action": action})
        self.save()

    def update_machine(self, machine_info: dict):
        self.data["machine"] = machine_info
        self.save()
