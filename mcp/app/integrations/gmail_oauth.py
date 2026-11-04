from app.integrations.gmail import SCOPES
from app.integrations.google_oauth import GoogleOAuth

class GmailOAuth(GoogleOAuth):
    SCOPES=SCOPES; SALT="fiora-gmail"; PURPOSE="gmail"; LABEL="Gmail"
    def account_email(self,credentials):
        from googleapiclient.discovery import build
        return build("gmail","v1",credentials=credentials,cache_discovery=False).users().getProfile(userId="me").execute()["emailAddress"]
