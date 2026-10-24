import unittest
from contextlib import contextmanager
from datetime import datetime, timezone
from app.services.import_graph import MessageImportGraph

class FakeCursor:
    def __init__(self,db): self.db=db; self.result=None
    def execute(self,sql,params=()):
        if sql.startswith("SELECT 1 FROM gmail_imports"): self.result=(1,) if params[0] in self.db.imports else None
        elif "INSERT INTO gmail_imports" in sql: self.db.imports[params[0]]={"status":params[5],"transaction_id":params[7]}
    def fetchone(self): return self.result

class FakeDB:
    def __init__(self): self.imports={}
    @contextmanager
    def cursor(self): yield FakeCursor(self)

class FakeRepo:
    def __init__(self): self.created=[]
    def create(self,resource,item): self.created.append(item); return {"id":len(self.created),**item}

class FakeFinance:
    def __init__(self): self.repo=FakeRepo()

class FakeExtractor:
    def __init__(self,reply): self.reply=reply; self.calls=0
    def extract(self,subject,body):
        self.calls+=1
        if isinstance(self.reply,Exception): raise self.reply
        return dict(self.reply) if self.reply else None

def message(message_id,body,subject="Alert"):
    return {"id":message_id,"subject":subject,"sender":"bank@example.com",
            "received_at":datetime(2026,1,2,tzinfo=timezone.utc),"body":body}

MODEL_REPLY={"kind":"expense","amount":499,"currency":"INR","merchant":"Netflix",
             "category":"Subscriptions","occurred_at":"2026-01-02T10:00:00+00:00"}

class MessageImportGraphTest(unittest.TestCase):
    def run_graph(self,msg,reply=None):
        self.db,self.finance,self.extractor=FakeDB(),FakeFinance(),FakeExtractor(reply)
        self.graph=MessageImportGraph(self.db,self.extractor)
        return self.graph.run(msg,self.finance,"me@example.com")
    def test_bank_alert_is_parsed_without_the_model(self):
        self.assertEqual(self.run_graph(message("m1","Rs. 1,250.50 debited from your account")),"imported")
        self.assertEqual(self.extractor.calls,0)
        self.assertEqual(self.finance.repo.created[0]["merchant"],"Alert")
        self.assertEqual(self.db.imports["m1"]["status"],"imported")
    def test_unreadable_message_goes_to_the_model(self):
        self.assertEqual(self.run_graph(message("m2","Your monthly plan renewed"),MODEL_REPLY),"imported")
        self.assertEqual(self.extractor.calls,1)
        self.assertEqual(self.finance.repo.created[0]["notes"],"Imported from Gmail using local Ollama")
    def test_model_without_transaction_records_review(self):
        self.assertEqual(self.run_graph(message("m3","Newsletter"),None),"review")
        self.assertEqual(self.db.imports["m3"],{"status":"review","transaction_id":None})
        self.assertEqual(self.finance.repo.created,[])
    def test_model_errors_and_invalid_replies_record_review(self):
        self.assertEqual(self.run_graph(message("m4","Hello"),RuntimeError("ollama down")),"review")
        self.assertEqual(self.run_graph(message("m5","Hello"),{**MODEL_REPLY,"amount":-5}),"review")
    def test_already_imported_messages_are_skipped(self):
        self.run_graph(message("m6","Rs. 100 debited"))
        self.assertEqual(self.graph.run(message("m6","Rs. 100 debited"),self.finance,"me@example.com"),"skipped")
        self.assertEqual(len(self.finance.repo.created),1)

if __name__=="__main__": unittest.main()
