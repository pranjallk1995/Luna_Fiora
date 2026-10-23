import threading
class GmailWorker:
    def __init__(self,imports,finance,interval): self.imports=imports; self.finance=finance; self.interval=interval; self.stop_event=threading.Event()
    def start(self): threading.Thread(target=self.run,daemon=True,name="fiora-gmail-sync").start()
    def stop(self): self.stop_event.set()
    def run(self):
        while not self.stop_event.wait(self.interval):
            try: self.imports.sync_all(self.finance)
            except Exception: continue