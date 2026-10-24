"""One Gmail message's path to a transaction, as a LangGraph state graph.

    check_seen ─┬─▶ END (already imported)
                └─▶ parse ─┬─────────────▶ record
                           └─▶ ask_model ─▶ record

Bank alerts are parsed deterministically first; only messages the parser cannot
read go to the local Ollama model. A message neither can turn into a valid
transaction is recorded for review instead of being imported.
"""
from dataclasses import dataclass
from typing import Any, TypedDict
from langgraph.graph import END, START, StateGraph
from langgraph.runtime import Runtime
from app.core.models import TransactionInput
from app.integrations.gmail import deterministic_extract

@dataclass(frozen=True)
class ImportContext:
    finance: Any
    email: str

class MessageState(TypedDict, total=False):
    message: dict; seen: bool; item: dict | None; transaction: dict | None; outcome: str

class MessageImportGraph:
    def __init__(self,db,extractor):
        self.db=db; self.extractor=extractor
        graph=StateGraph(MessageState,context_schema=ImportContext)
        graph.add_node("check_seen",self.check_seen); graph.add_node("parse",self.parse)
        graph.add_node("ask_model",self.ask_model); graph.add_node("record",self.record)
        graph.add_edge(START,"check_seen")
        graph.add_conditional_edges("check_seen",lambda s:END if s["seen"] else "parse",[END,"parse"])
        graph.add_conditional_edges("parse",lambda s:"record" if s["item"] else "ask_model",["record","ask_model"])
        graph.add_edge("ask_model","record"); graph.add_edge("record",END)
        self.graph=graph.compile(name="fiora-gmail-import")
    def run(self,message,finance,email):
        """Import one message; return "imported", "review", or "skipped"."""
        return self.graph.invoke({"message":message},context=ImportContext(finance,email)).get("outcome","skipped")
    def check_seen(self,state):
        with self.db.cursor() as c:
            c.execute("SELECT 1 FROM gmail_imports WHERE message_id=%s",(state["message"]["id"],))
            return {"seen":c.fetchone() is not None}
    def parse(self,state): return {"item":deterministic_extract(state["message"])}
    def ask_model(self,state):
        message=state["message"]
        try:
            raw=self.extractor.extract(message["subject"],message["body"])
            if not raw: return {"item":None}
            raw.update({"source":"gmail","external_id":message["id"],"notes":"Imported from Gmail using local Ollama"})
            return {"item":TransactionInput.model_validate(raw).model_dump()}
        except Exception: return {"item":None}
    def record(self,state,runtime:Runtime[ImportContext]):
        message,item=state["message"],state.get("item"); transaction=None
        if item: transaction=runtime.context.finance.repo.create("transactions",TransactionInput.model_validate(item).model_dump())
        with self.db.cursor() as c:
            c.execute("""INSERT INTO gmail_imports(message_id,email,subject,sender,received_at,status,excerpt,transaction_id)
            VALUES(%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING""",
            (message["id"],runtime.context.email,message["subject"],message["sender"],message["received_at"],
             "imported" if transaction else "review",message["body"][:500],transaction["id"] if transaction else None))
        return {"transaction":transaction,"outcome":"imported" if transaction else "review"}
