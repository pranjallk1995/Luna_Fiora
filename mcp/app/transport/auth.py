import secrets
from starlette.responses import JSONResponse
class APIAuthenticator:
    def __init__(self,token): self.token=token
    def rejection(self,request):
        supplied=request.headers.get("authorization","").removeprefix("Bearer ").strip()
        if not secrets.compare_digest(supplied,self.token):
            return JSONResponse({"error":"Unauthorized"},status_code=401)