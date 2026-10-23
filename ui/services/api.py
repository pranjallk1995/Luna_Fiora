from datetime import date
import httpx
class FioraAPI:
    def __init__(self,config): self.base=config.api_url; self.headers={"Authorization":f"Bearer {config.api_token}"}
    def request(self,method,path,**kwargs):
        r=httpx.request(method,f"{self.base}{path}",headers=self.headers,timeout=90,**kwargs); r.raise_for_status(); return r.json()
    def dashboard(self,start:date,end:date): return self.request("GET","/api/dashboard",params={"start":start.isoformat(),"end":end.isoformat()})
    def create(self,resource,payload): return self.request("POST",f"/api/{resource}",json=payload)
    def update(self,resource,item_id,payload): return self.request("PUT",f"/api/{resource}/{item_id}",json=payload)
    def delete(self,resource,item_id): return self.request("DELETE",f"/api/{resource}/{item_id}")
    def gmail_url(self): return self.request("GET","/api/gmail/authorization-url")["url"]
    def sync_gmail(self): return self.request("POST","/api/gmail/sync")