import os
from urllib.parse import urlparse
from itsdangerous import BadSignature, URLSafeTimedSerializer
from app.core import tenancy
from app.core.config import AppConfig

def renewing_credentials(refresh_token,client_id,client_secret,scopes,expired):
    """Google credentials that raise expired when Google has expired or revoked the sign-in."""
    from google.auth.exceptions import RefreshError
    from google.oauth2.credentials import Credentials
    class RenewingCredentials(Credentials):
        def refresh(self,request):
            try: super().refresh(request)
            except RefreshError as error:
                if "invalid_grant" in str(error): raise expired() from error
                raise
    return RenewingCredentials(None,refresh_token=refresh_token,token_uri=AppConfig.GOOGLE_TOKEN_URI,
        client_id=client_id,client_secret=client_secret,scopes=scopes)

class GoogleOAuth:
    """A one-time read-only Google sign-in, run by Fiora's backend callback.

    The state round-trip is signed with the API token so only a sign-in that Fiora
    started can complete. PKCE is off because the client is confidential (it holds a
    secret) and the callback runs in a different request than the start.
    """
    SCOPES=[]; SALT=""; PURPOSE=""; LABEL=""
    def __init__(self,client_id,client_secret,redirect_uri,state_secret):
        self.client_id=client_id; self.client_secret=client_secret; self.redirect_uri=redirect_uri
        self.signer=URLSafeTimedSerializer(state_secret,salt=self.SALT)
        # The client may be shared with Sentia's sign-in, so Google may return its openid,
        # email, and profile scopes too; oauthlib would otherwise reject the extra scopes.
        os.environ.setdefault("OAUTHLIB_RELAX_TOKEN_SCOPE","1")
        if urlparse(redirect_uri).hostname in {"localhost","127.0.0.1"}:
            # oauthlib refuses plain-HTTP callbacks unless told this is local development.
            os.environ.setdefault("OAUTHLIB_INSECURE_TRANSPORT","1")
    @property
    def configured(self): return bool(self.client_id and self.client_secret)
    def flow(self,state=None):
        from google_auth_oauthlib.flow import Flow
        config={"web":{"client_id":self.client_id,"client_secret":self.client_secret,
          "auth_uri":AppConfig.GOOGLE_AUTH_URI,"token_uri":AppConfig.GOOGLE_TOKEN_URI}}
        return Flow.from_client_config(config,scopes=self.SCOPES,redirect_uri=self.redirect_uri,state=state,autogenerate_code_verifier=False)
    def authorization_url(self):
        if not self.configured: raise ValueError(f"{self.LABEL} is not configured; set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET.")
        state=self.signer.dumps({"purpose":self.PURPOSE,"user":tenancy.current()})
        url,_=self.flow(state).authorization_url(access_type="offline",prompt="consent",state=state)
        return url
    def user_of(self,state):
        """Who started this sign-in, from the state only Fiora can sign."""
        try: return self.signer.loads(state,max_age=AppConfig.GOOGLE_STATE_MAX_AGE_SECONDS)["user"]
        except (BadSignature,KeyError,TypeError) as error:
            raise PermissionError(f"This {self.LABEL} sign-in link expired or was not started by Fiora.") from error
    def callback_response(self,callback_url):
        """The callback as Google sent it: behind a TLS-terminating proxy the request
        arrives as plain HTTP, which oauthlib rejects, so keep only its query."""
        return f"{self.redirect_uri}?{urlparse(callback_url).query}"
    def account_email(self,credentials): raise NotImplementedError
    def exchange(self,url,state):
        """Finish the sign-in; return the account email and its refresh token."""
        self.user_of(state)
        flow=self.flow(state); flow.fetch_token(authorization_response=self.callback_response(url))
        credentials=flow.credentials
        if not credentials.refresh_token: raise ValueError("Google did not return a refresh token; remove Fiora's access and connect again.")
        return self.account_email(credentials),credentials.refresh_token
