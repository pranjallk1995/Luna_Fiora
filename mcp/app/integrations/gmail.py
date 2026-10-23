import base64, re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

SCOPES=["https://www.googleapis.com/auth/gmail.readonly"]
AMOUNT=re.compile(r"(?:INR|Rs\.?|₹)\s*([\d,]+(?:\.\d{1,2})?)",re.I)
DEBIT=re.compile(r"\b(debited|spent|purchase|paid|sent)\b",re.I)
CREDIT=re.compile(r"\b(credited|received|salary)\b",re.I)

class GmailReader:
    QUERY='newer_than:45d (UPI OR debited OR credited OR transaction OR purchase OR EMI OR SIP)'
    def __init__(self,client_id,client_secret): self.client_id=client_id; self.client_secret=client_secret
    def service(self,refresh_token):
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
        credentials=Credentials(None,refresh_token=refresh_token,token_uri="https://oauth2.googleapis.com/token",
            client_id=self.client_id,client_secret=self.client_secret,scopes=SCOPES)
        return build("gmail","v1",credentials=credentials,cache_discovery=False)
    def messages(self,refresh_token,max_results=100):
        service=self.service(refresh_token)
        refs=service.users().messages().list(userId="me",q=self.QUERY,maxResults=max_results).execute().get("messages",[])
        return [self._decode(service.users().messages().get(userId="me",id=r["id"],format="full").execute()) for r in refs]
    def _decode(self,msg):
        headers={h["name"].lower():h["value"] for h in msg.get("payload",{}).get("headers",[])}
        parts=msg.get("payload",{}).get("parts") or [msg.get("payload",{})]; body=""
        for part in parts:
            if part.get("mimeType")=="text/plain" and part.get("body",{}).get("data"):
                data=part["body"]["data"]
                body+=base64.urlsafe_b64decode(data + "=" * (-len(data) % 4)).decode(errors="replace")
        received=parsedate_to_datetime(headers.get("date")) if headers.get("date") else datetime.now(timezone.utc)
        return {"id":msg["id"],"subject":headers.get("subject",""),"sender":headers.get("from",""),
                "received_at":received,"body":body or msg.get("snippet","")}

def deterministic_extract(message):
    text=f'{message["subject"]} {message["body"]}'
    match=AMOUNT.search(text)
    if not match or not (DEBIT.search(text) or CREDIT.search(text)): return None
    kind="income" if CREDIT.search(text) and not DEBIT.search(text) else "expense"
    merchant=(message["subject"] or message["sender"])[:120]
    category="Income" if kind=="income" else "Uncategorized"
    return {"occurred_at":message["received_at"],"kind":kind,"amount":match.group(1).replace(",",""),
            "currency":"INR","merchant":merchant,"category":category,"account":None,
            "notes":"Imported from Gmail","source":"gmail","external_id":message["id"]}