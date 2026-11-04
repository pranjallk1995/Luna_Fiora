import unittest
from unittest import mock
from cryptography.fernet import Fernet
from app.integrations.drive import DriveClient, DriveFile, DriveOAuth, DriveSignInExpired, FOLDER_TYPE, SHEET_TYPE
from app.integrations.statements import StatementLocked, statement_chunks, statement_text
from app.services.drive_import import DriveImportService

class FakeRepo:
    def __init__(self): self.conn=None; self.job_rows={}; self.file_rows=[]; self.rows={}
    def connection(self): return self.conn
    def save_connection(self,email,encrypted): self.conn={"email":email,"encrypted_refresh_token":encrypted}
    def delete_connection(self): self.conn=None
    def create_job(self,folder_id,folder_name,recursive):
        job_id=f"job-{len(self.job_rows)}"; self.job_rows[job_id]={"job_id":job_id,"folder_id":folder_id,"folder_name":folder_name,"recursive":recursive,"status":"queued"}; return job_id
    def job_request(self,job_id): return self.job_rows[job_id]
    def job(self,job_id): return self.job_rows.get(job_id)
    def unfinished_jobs(self): return [k for k,v in self.job_rows.items() if v["status"] in ("queued","listing","running")]
    def update_job(self,job_id,started=False,finished=False,**fields): self.job_rows[job_id].update(fields)
    def files(self,job_id): return [f for f in self.file_rows if f["job_id"]==job_id]
    def file_recorded(self,job_id,file_id): return any(f["job_id"]==job_id and f["file_id"]==file_id for f in self.file_rows)
    def already_imported(self,file_id,version): return any(f["file_id"]==file_id and f["version"]==version and f["outcome"]=="imported" for f in self.file_rows)
    def record_file(self,job_id,file): self.file_rows.append({"job_id":job_id,**file})
    def add_new_transactions(self,rows,own_ids):
        added=matched=0; prefix=own_ids[:-1]
        for row in rows:
            if any(o["occurred_at"].date()==row["occurred_at"].date() and o["amount"]==row["amount"] and o["kind"]==row["kind"] and not o["external_id"].startswith(prefix) for o in self.rows.values()): matched+=1; continue
            if row["external_id"] not in self.rows: self.rows[row["external_id"]]=row; added+=1
        return added,matched

class FakeDrive:
    def __init__(self,files): self.files=files
    def account_email(self): return "me@example.com"
    def resolve_folder(self,spec): return {"folder_id":"f1","name":spec}
    def folders(self,parent=None): return [{"folder_id":"f1","name":"Statements"}]
    def walk(self,folder_id,recursive=True): return [file for file,_ in self.files]
    def download(self,file): return dict((f.file_id,d) for f,d in self.files)[file.file_id]

class FakeExtractor:
    def __init__(self,rows): self.rows=rows; self.calls=0
    def transactions(self,name,text):
        self.calls+=1
        if isinstance(self.rows,Exception): raise self.rows
        return self.rows

ROW={"date":"2026-03-12","description":"AMAZON","amount":"1,250.50","kind":"expense"}
CSV=DriveFile("a","march.csv","text/csv","md5-a")

def make(files=(),rows=(ROW,)):
    repo=FakeRepo(); extractor=FakeExtractor(list(rows) if not isinstance(rows,Exception) else rows); client=FakeDrive(list(files))
    service=DriveImportService(repo,DriveOAuth("client","secret","https://x.test/api/drive/callback","x"*32),extractor,Fernet.generate_key().decode(),drive_factory=lambda token:client,run_inline=True)
    service.repo.save_connection("me@example.com",service.cipher.encrypt(b"refresh-token").decode())
    return service,repo,extractor,client

class ConnectionTests(unittest.TestCase):
    def test_status_and_encrypted_token(self):
        service,repo,_,_=make(); status=service.status()
        self.assertEqual((status["configured"],status["connected"],status["email"],status["sign_in_expired"]),(True,True,"me@example.com",False))
        self.assertNotIn("refresh-token",repo.conn["encrypted_refresh_token"])
    def test_disconnecting_stops_imports(self):
        service,_,_,_=make(); service.disconnect()
        self.assertFalse(service.status()["connected"])
        with self.assertRaisesRegex(ValueError,"not connected"): service.import_folder("Statements")
    def test_expiry_and_outage_are_told_apart(self):
        service,_,_,client=make()
        client.account_email=mock.Mock(side_effect=DriveSignInExpired()); self.assertTrue(service.status()["sign_in_expired"])
        client.account_email=mock.Mock(side_effect=ConnectionError()); self.assertFalse(service.status()["sign_in_expired"])
    def test_a_token_that_cannot_be_read_is_an_expiry(self):
        service,_,_,_=make(); service.cipher=Fernet(Fernet.generate_key())
        self.assertTrue(service.status()["sign_in_expired"])
    def test_the_sign_in_is_read_only_and_signed_separately_from_gmail(self):
        from app.integrations.gmail_oauth import GmailOAuth
        oauth=DriveOAuth("client","secret","https://x.test/api/drive/callback","x"*32); url=oauth.authorization_url()
        self.assertIn("drive.readonly",url); self.assertNotIn("code_challenge",url)
        with self.assertRaises(PermissionError): oauth.user_of(GmailOAuth("c","s","https://x.test/cb","x"*32).signer.dumps({"user":"owner"}))

class ImportTests(unittest.TestCase):
    def run_import(self,files,rows=(ROW,),**kwargs):
        service,repo,extractor,client=make(files,rows); job=service.import_folder("Statements",**kwargs)
        return service,repo,extractor,client,job
    def test_a_statements_rows_become_transactions(self):
        _,repo,_,_,job=self.run_import([(CSV,b"date,desc,amt\n12/03/2026,AMAZON,1250.50\n")])
        self.assertEqual(repo.job_rows[job["job_id"]]["status"],"done")
        row=next(iter(repo.rows.values()))
        self.assertEqual((str(row["amount"]),row["kind"],row["merchant"],row["source"]),("1250.50","expense","AMAZON","drive"))
        self.assertEqual(repo.file_rows[0]["added"],1)
    def test_importing_again_only_reads_what_changed(self):
        service,repo,extractor,client,_=self.run_import([(CSV,b"h\nrow\n")])
        service.import_folder("Statements"); self.assertEqual(extractor.calls,1)
        self.assertEqual(repo.file_rows[-1]["outcome"],"skipped")
        changed=DriveFile("a","march.csv","text/csv","md5-new"); client.files=[(changed,b"h\nrow\n")]
        service.import_folder("Statements")
        self.assertEqual(extractor.calls,2); self.assertEqual(len(repo.rows),1)
    def test_repeats_within_a_file_are_kept(self):
        _,repo,_,_,_=self.run_import([(CSV,b"h\nrow\n")],[ROW,ROW])
        self.assertEqual(len(repo.rows),2)
    def test_rows_fiora_has_from_elsewhere_are_matched_not_added(self):
        service,repo,extractor,client=make([(CSV,b"h\nrow\n"),(DriveFile("b","other.csv","text/csv","md5-b"),b"h\nrow\n")])
        service.import_folder("Statements")
        self.assertEqual((repo.file_rows[0]["added"],repo.file_rows[1]["added"],repo.file_rows[1]["matched"]),(1,0,1))
    def test_bad_rows_are_rejected_and_counted(self):
        rows=[ROW,{**ROW,"amount":"n/a"},{**ROW,"date":"soon"},{**ROW,"kind":"maybe"},{**ROW,"date":"2999-01-01"},{**ROW,"description":""}]
        _,repo,_,_,_=self.run_import([(CSV,b"h\nrow\n")],rows)
        self.assertEqual((repo.file_rows[0]["added"],repo.file_rows[0]["rejected"]),(1,5))
    def test_balances_totals_and_card_bill_payments_are_not_transactions(self):
        lines=["Opening Balance","Closing Balance","Balance B/F","Carried Forward","Total Amount Due","PAYMENT RECEIVED THANK YOU"]
        rows=[{**ROW,"description":line,"kind":"income"} for line in lines]+[{**ROW,"description":"TOTAL ENERGIES FUEL"},{**ROW,"description":"SALARY MARCH ACME","kind":"income"}]
        _,repo,_,_,_=self.run_import([(CSV,b"h\nrow\n")],rows)
        self.assertEqual(repo.file_rows[0]["rejected"],6)
        self.assertEqual({row["merchant"] for row in repo.rows.values()},{"TOTAL ENERGIES FUEL","SALARY MARCH ACME"})
    def test_a_failure_adds_nothing_and_the_next_import_retries(self):
        service,repo,extractor,_,_=self.run_import([(CSV,b"h\nrow\n")],RuntimeError("model down"))
        self.assertEqual((repo.file_rows[0]["outcome"],repo.rows),("failed",{}))
        extractor.rows=[ROW]; service.import_folder("Statements")
        self.assertEqual(repo.file_rows[-1]["outcome"],"imported")
    def test_unreadable_files_are_reported_without_downloading(self):
        zip_file=DriveFile("z","x.zip","application/zip","m")
        _,repo,extractor,_,_=self.run_import([(zip_file,b"")])
        self.assertEqual(repo.file_rows[0]["outcome"],"unsupported"); self.assertEqual(extractor.calls,0)
    def test_a_locked_pdf_needs_its_password_which_is_not_kept(self):
        pdf=DriveFile("p","s.pdf","application/pdf","m")
        with mock.patch("app.services.drive_import.statement_text",side_effect=StatementLocked("locked")) as text:
            service,repo,_,_,job=self.run_import([(pdf,b"%PDF")],password="secret")
        self.assertEqual(text.call_args.args[2],"secret")
        self.assertEqual(repo.file_rows[0]["outcome"],"needs_password")
        self.assertEqual(service._passwords,{}); self.assertNotIn("secret",repr((repo.job_rows,repo.file_rows)))
    def test_a_folder_too_large_stops_before_reading(self):
        service,repo,extractor,_=make([(DriveFile(str(i),"a.csv","text/csv","m"),b"h\nr\n") for i in range(3)]); service.max_files=2
        job=service.import_folder("Statements")
        self.assertEqual(repo.job_rows[job["job_id"]]["status"],"failed"); self.assertEqual(extractor.calls,0)
    def test_a_folder_is_required(self):
        with self.assertRaisesRegex(ValueError,"Choose"): make()[0].import_folder("  ")
    def test_interrupted_jobs_resume_past_what_they_recorded(self):
        service,repo,extractor,client=make([(CSV,b"h\nrow\n")])
        job_id=repo.create_job("f1","Statements",True); repo.update_job(job_id,status="running")
        service.resume()
        self.assertEqual(repo.job_rows[job_id]["status"],"done"); self.assertEqual(extractor.calls,1)

class StatementTests(unittest.TestCase):
    def test_a_csv_header_starts_every_piece(self):
        text="date,amount\n"+"\n".join(f"2026-01-{i:02},{i}" for i in range(1,30))
        chunks=statement_chunks(text,"text/csv",100)
        self.assertGreater(len(chunks),1); self.assertTrue(all(c.startswith("date,amount\n") for c in chunks))
        self.assertEqual(sum(c.count("2026-01-") for c in chunks),29)
    def test_a_pdf_has_no_header_and_empty_text_has_no_pieces(self):
        self.assertEqual(statement_chunks("a\nb\n","application/pdf",100),["a\nb\n"])
        self.assertEqual(statement_chunks("  \n","application/pdf",100),[])
    def test_text_is_decoded_whatever_its_encoding(self):
        self.assertEqual(statement_text("₹1".encode("utf-8-sig"),"text/csv"),"₹1")
        self.assertEqual(statement_text(b"caf\xe9","text/csv"),"café")
    def test_a_file_that_is_not_a_pdf_is_refused(self):
        with self.assertRaisesRegex(ValueError,"not a valid PDF"): statement_text(b"nope","application/pdf")

class ClientTests(unittest.TestCase):
    def test_a_sheet_is_exported_as_csv(self):
        service=mock.MagicMock(); DriveClient(service).download(DriveFile("s","Sheet",SHEET_TYPE))
        self.assertEqual(service.files.return_value.export.call_args.kwargs["mimeType"],"text/csv")
    def test_a_folder_link_is_resolved(self):
        service=mock.MagicMock(); service.files.return_value.get.return_value.execute.return_value={"id":"abc1234567","name":"S","mimeType":FOLDER_TYPE}
        self.assertEqual(DriveClient(service).resolve_folder("https://drive.google.com/drive/folders/abc1234567")["folder_id"],"abc1234567")
