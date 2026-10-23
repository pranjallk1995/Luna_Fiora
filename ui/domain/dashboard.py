from dataclasses import dataclass
@dataclass(frozen=True)
class Dashboard:
    analytics:dict; transactions:list; commitments:list; goals:list; reminders:list
    @classmethod
    def from_payload(cls,p): return cls(p["analytics"],p["transactions"],p["commitments"],p["goals"],p["reminders"])