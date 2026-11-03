import threading
from app.core import tenancy
class GmailWorker:
    def __init__(self,imports,finance,interval,users): self.imports=imports; self.finance=finance; self.interval=interval; self.users=users; self.stop_event=threading.Event()
    def start(self): threading.Thread(target=self.run,daemon=True,name="fiora-gmail-sync").start()
    def stop(self): self.stop_event.set()
    def run(self):
        while not self.stop_event.wait(self.interval):
            try: users=self.users()
            except Exception: continue
            for user_id in users:
                try:
                    with tenancy.acting_as(user_id): self.imports.sync_all(self.finance)
                except Exception: continue
