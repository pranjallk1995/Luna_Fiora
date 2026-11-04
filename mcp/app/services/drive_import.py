"""Bulk transaction imports from Google Drive folders, as background jobs.

Each statement in a folder (a PDF with text, CSV, plain text, or Google Sheet) is read
by the local model, one piece at a time, and its rows are added together or not at all.
Files imported before unchanged are skipped, so running a folder again adds only what
is new and retries what failed, and a job a restart cut off resumes the same way. A row
Fiora already has from elsewhere, with the same day, amount, and direction, is counted
as matched rather than added, so a statement does not double what Gmail imported. Jobs
run one at a time because each piece takes model time. A job's PDF password stays in
memory only, so one a restart cuts off reports its locked files as needs_password.
"""
import hashlib, logging, queue, re, threading
from collections import Counter
from dataclasses import asdict
from datetime import date
from decimal import Decimal, InvalidOperation
from cryptography.fernet import Fernet, InvalidToken
from pydantic import ValidationError
from app.core import tenancy
from app.core.config import AppConfig
from app.core.models import TransactionInput
from app.integrations.drive import DriveClient, DriveFile, DriveSignInExpired
from app.integrations.statements import StatementLocked, statement_chunks, statement_text

logger=logging.getLogger(__name__)
# Lines a statement prints that are not transactions. The model is told to leave them out
# but does not always, and a balance read as income would wreck the month's figures.
NOT_A_TRANSACTION=re.compile(r"\b(opening|closing|available|ledger)\s+balance\b|\bbalance\s+(b/?f|c/?f|brought|carried)\b|\b(brought|carried)\s+forward\b|^\s*(sub\s*)?total\s*$|\b(sub\s*)?total\s+(amount|debits?|credits?|due|payable|balance|purchases?|spends?)\b|\b(minimum|amount)\s+(amount\s+)?due\b|\bpayment\s+received\b|\bthank\s+you\b",re.IGNORECASE)

class DriveImportService:
    def __init__(self,repo,oauth,extractor,key,max_files=AppConfig.DRIVE_MAX_FILES,drive_factory=None,run_inline=False):
        self.repo=repo; self.oauth=oauth; self.extractor=extractor; self.cipher=Fernet(key.encode()); self.max_files=max_files
        self.drive_factory=drive_factory or (lambda token:DriveClient.from_refresh_token(token,oauth.client_id,oauth.client_secret))
        self.run_inline=run_inline; self._passwords={}; self._queue=queue.Queue(); self._worker=None; self._lock=threading.Lock()
    # Connection
    def status(self):
        connection=self.repo.connection()
        return {"configured":self.oauth.configured,"connected":connection is not None,
                "email":connection["email"] if connection else None,
                "sign_in_expired":connection is not None and self.sign_in_expired()}
    def sign_in_expired(self):
        """Ask Google whether the saved sign-in still works; other trouble is not an expiry."""
        try: self.drive().account_email()
        except DriveSignInExpired: return True
        except Exception as error:  # An outage must not look like a lost sign-in.
            logger.warning("Could not check the Google Drive sign-in: %s",type(error).__name__)
        return False
    def connect(self,url,state):
        email,refresh_token=self.oauth.exchange(url,state)
        self.repo.save_connection(email,self.cipher.encrypt(refresh_token.encode()).decode())
        return email
    def disconnect(self):
        """Forget the saved sign-in; transactions and past imports stay."""
        self.repo.delete_connection(); return {"status":"disconnected"}
    def drive(self):
        connection=self.repo.connection()
        if connection is None: raise ValueError("Google Drive is not connected; connect it from Fiora's overview first.")
        try: token=self.cipher.decrypt(connection["encrypted_refresh_token"].encode()).decode()
        except InvalidToken as error:
            raise DriveSignInExpired("The saved Google Drive sign-in cannot be read. Reconnect Google Drive from Fiora's overview to continue; your transactions are safe.") from error
        return self.drive_factory(token)
    def folders(self,parent_id=None): return self.drive().folders(parent_id)
    # Jobs
    def import_folder(self,folder,recursive=True,password=None):
        """Queue every statement under a Drive folder (link, ID, or exact name)."""
        if not (folder or "").strip(): raise ValueError("Choose a Drive folder to import.")
        target=self.drive().resolve_folder(folder)
        job_id=self.repo.create_job(target["folder_id"],target["name"],recursive)
        if password: self._passwords[job_id]=password
        self._enqueue(job_id)
        return self.repo.job(job_id)
    def job(self,job_id):
        job=self.repo.job(job_id)
        if job is None: raise FileNotFoundError(f"No import job has ID {job_id}.")
        return {**job,"files":self.repo.files(job_id)}
    def jobs(self,limit=10): return self.repo.jobs(max(1,min(limit,50)))
    def resume(self):
        """Queue the current person's jobs that a restart interrupted, oldest first."""
        for job_id in self.repo.unfinished_jobs(): self._enqueue(job_id)
    def _enqueue(self,job_id):
        if self.run_inline: self._run(job_id); return
        self._queue.put((tenancy.current(),job_id))
        with self._lock:
            if self._worker is None or not self._worker.is_alive():
                self._worker=threading.Thread(target=self._loop,name="fiora-drive-imports",daemon=True); self._worker.start()
    def _loop(self):
        while True:
            user_id,job_id=self._queue.get()
            try:
                with tenancy.acting_as(user_id):
                    try: self._run(job_id)
                    except Exception:  # One broken job never stops the worker.
                        logger.exception("Drive import job failed")
                        self.repo.update_job(job_id,status="failed",error="Unexpected error; see the logs.",current_item=None,finished=True)
            except tenancy.NoUserError: logger.info("Dropped an import job of someone deleted.")
            finally: self._queue.task_done()
    def _run(self,job_id):
        try: self._work(job_id)
        finally: self._passwords.pop(job_id,None)
    def _work(self,job_id):
        job=self.repo.job_request(job_id)
        self.repo.update_job(job_id,status="listing",started=True)
        try:
            drive=self.drive(); files=drive.walk(job["folder_id"],job["recursive"])
            if len(files)>self.max_files: raise ValueError(f"One import may hold at most {self.max_files} files; this folder has {len(files)}.")
        except Exception as error:
            self.repo.update_job(job_id,status="failed",error=str(error)[:1000],finished=True); return
        self.repo.update_job(job_id,status="running",total=len(files))
        for file in files:
            if self.repo.file_recorded(job_id,file.file_id): continue
            self.repo.update_job(job_id,current_item=f"{file.path}{file.name}"[:300])
            try: result=self.import_file(job_id,file,drive)
            except Exception as error:  # One bad file never stops the job.
                logger.warning("Could not import a Drive file: %s",type(error).__name__)
                result={"outcome":"failed","error":str(error)[:500]}
            self.repo.record_file(job_id,{**asdict(file),"version":file.version,"added":0,"matched":0,"rejected":0,"error":None,**result})
        self.repo.update_job(job_id,status="done",current_item=None,finished=True)
    def import_file(self,job_id,file,drive):
        if not file.readable: return {"outcome":"unsupported","error":f"{file.mime_type} files are not read; Fiora reads PDFs with text, CSV, plain text, and Google Sheets."}
        if self.repo.already_imported(file.file_id,file.version): return {"outcome":"skipped"}
        mime_type="text/csv" if file.mime_type!="application/pdf" and file.mime_type!="text/plain" else file.mime_type
        try: text=statement_text(drive.download(file),mime_type,self._passwords.get(job_id))
        except StatementLocked as error: return {"outcome":"needs_password","error":str(error)}
        chunks=statement_chunks(text,mime_type,AppConfig.STATEMENT_CHUNK_CHARS)
        if not chunks: return {"outcome":"no_text","error":"This file has no readable text; it may be a scan."}
        rows=[row for chunk in chunks for row in self.extractor.transactions(file.name,chunk)]
        transactions,rejected=self.transactions(file,rows)
        if not transactions: return {"outcome":"no_transactions","rejected":rejected,"error":"No transactions were found in this file."}
        added,matched=self.repo.add_new_transactions(transactions,f"drive:{file.file_id}:%")
        return {"outcome":"imported","added":added,"matched":matched,"rejected":rejected}
    @staticmethod
    def transactions(file,rows):
        """The rows that are valid transactions, each with an ID stable across imports of the file."""
        valid,rejected,seen=[],0,Counter()
        for row in rows:
            try:
                amount=abs(Decimal(str(row.get("amount")).replace(",","")))
                item=TransactionInput.model_validate({"occurred_at":row.get("date"),"kind":row.get("kind"),"amount":amount,
                    "currency":row.get("currency") or "INR","merchant":str(row.get("description") or "")[:120].strip(),"category":row.get("category") or "Uncategorized",
                    "notes":f"Imported from {file.name} on Google Drive"[:500],"source":"drive"})
                if item.occurred_at.date()>date.today(): raise ValueError("A statement cannot list a future date.")
                if NOT_A_TRANSACTION.search(item.merchant): raise ValueError("This line is a summary, not a transaction.")
            except (ValidationError,ValueError,InvalidOperation,TypeError,AttributeError): rejected+=1; continue
            key=f"{item.occurred_at.date()}|{item.amount}|{item.kind}|{item.merchant}"; seen[key]+=1
            digest=hashlib.sha256(f"{key}|{seen[key]}".encode()).hexdigest()[:24]
            valid.append(item.model_copy(update={"external_id":f"drive:{file.file_id}:{digest}"}).model_dump())
        return valid,rejected
