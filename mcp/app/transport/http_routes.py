from datetime import date
from html import escape
from decimal import Decimal
from mcp.server.fastmcp import FastMCP
from pydantic import ValidationError
from starlette.responses import JSONResponse, HTMLResponse
from app.transport.auth import APIAuthenticator

class FioraHTTPRoutes:
    def __init__(self,server:FastMCP,service,imports,oauth,token):
        self.server=server; self.service=service; self.imports=imports; self.oauth=oauth
        self.auth=APIAuthenticator(token); self.register()
    @classmethod
    def json(cls,value):
        if isinstance(value,dict): return {k:cls.json(v) for k,v in value.items()}
        if isinstance(value,(list,tuple)): return [cls.json(v) for v in value]
        if isinstance(value,Decimal): return float(value)
        if hasattr(value,"isoformat"): return value.isoformat()
        return value
    def route(self,method,path,handler,public=False):
        async def endpoint(request):
            if not public:
                rejection=self.auth.rejection(request)
                if rejection:return rejection
            try:return JSONResponse(self.json(await handler(request)))
            except ValidationError as e:return JSONResponse({"error":"Invalid request","details":e.errors()},status_code=422)
            except Exception as e:return JSONResponse({"error":str(e)},status_code=400)
        self.server.custom_route(path,methods=[method])(endpoint)
    def register(self):
        async def health(r): return {"status":"ok","service":"luna-fiora"}
        self.route("GET","/health",health,True)
        self.route("GET","/api/dashboard",self.dashboard)
        for resource in ("transactions","commitments","goals","reminders"):
            self.route("GET",f"/api/{resource}",lambda r,x=resource:self.list_resource(r,x))
            self.route("POST",f"/api/{resource}",lambda r,x=resource:self.create_resource(r,x))
            self.route("PUT",f"/api/{resource}/{{item_id}}",lambda r,x=resource:self.update_resource(r,x))
            self.route("DELETE",f"/api/{resource}/{{item_id}}",lambda r,x=resource:self.delete_resource(r,x))
        self.route("GET","/api/analytics",self.analytics)
        self.route("GET","/api/goals/{item_id}/projection",self.projection)
        self.route("POST","/api/gmail/sync",self.sync)
        self.route("GET","/api/gmail/authorization-url",self.authorization_url)
        self.server.custom_route("/api/gmail/callback",methods=["GET"])(self.callback)
    def dates(self,r):
        today=date.today(); start=r.query_params.get("start",today.replace(day=1).isoformat()); end=r.query_params.get("end",today.isoformat())
        return date.fromisoformat(start),date.fromisoformat(end)
    async def dashboard(self,r): start,end=self.dates(r); return self.service.dashboard(start,end)
    async def analytics(self,r): start,end=self.dates(r); return self.service.analytics(start,end)
    async def list_resource(self,r,resource):
        start,end=self.dates(r); return self.service.list(resource,start,end) if resource=="transactions" else self.service.list(resource)
    async def create_resource(self,r,resource): return self.service.create(resource,await r.json())
    async def update_resource(self,r,resource): return self.service.update(resource,int(r.path_params["item_id"]),await r.json())
    async def delete_resource(self,r,resource): return self.service.delete(resource,int(r.path_params["item_id"]))
    async def projection(self,r): return self.service.goal_projection(int(r.path_params["item_id"]))
    async def sync(self,r): return self.imports.sync_all(self.service)
    async def authorization_url(self,r): return {"url":self.oauth.authorization_url(),"configured":self.oauth.configured}
    async def callback(self,request):
        try:
            email,token=self.oauth.exchange(str(request.url),request.query_params["state"])
            self.imports.save_connection(email,token)
            return HTMLResponse("<h2>Gmail connected to Luna Fiora.</h2><p>You may close this window.</p>")
        except Exception as e:return HTMLResponse(f"<h2>Connection failed</h2><p>{escape(str(e))}</p>",status_code=400)