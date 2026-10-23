from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from itsdangerous import URLSafeTimedSerializer
from app.integrations.gmail import SCOPES

class GmailOAuth:
    def __init__(self,client_id,client_secret,redirect_uri,state_secret):
        self.client_id=client_id; self.client_secret=client_secret; self.redirect_uri=redirect_uri
        self.signer=URLSafeTimedSerializer(state_secret,salt="fiora-gmail")
    @property
    def configured(self): return bool(self.client_id and self.client_secret)
    def flow(self,state=None):
        config={"web":{"client_id":self.client_id,"client_secret":self.client_secret,
          "auth_uri":"https://accounts.google.com/o/oauth2/auth","token_uri":"https://oauth2.googleapis.com/token"}}
        return Flow.from_client_config(config,scopes=SCOPES,redirect_uri=self.redirect_uri,state=state)
    def authorization_url(self):
        if not self.configured: raise ValueError("Gmail OAuth is not configured")
        state=self.signer.dumps({"purpose":"gmail"})
        url,_=self.flow(state).authorization_url(access_type="offline",include_granted_scopes="true",prompt="consent",state=state)
        return url
    def exchange(self,url,state):
        self.signer.loads(state,max_age=900)
        flow=self.flow(state); flow.fetch_token(authorization_response=url)
        credentials=flow.credentials
        if not credentials.refresh_token: raise ValueError("Google did not return a refresh token")
        profile=build("gmail","v1",credentials=credentials,cache_discovery=False).users().getProfile(userId="me").execute()
        return profile["emailAddress"],credentials.refresh_token