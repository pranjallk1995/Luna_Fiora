from datetime import date
from html import escape
from decimal import Decimal
import anyio
from mcp.server.fastmcp import FastMCP
from pydantic import ValidationError
from starlette.responses import JSONResponse, HTMLResponse
from app.core import tenancy
from app.transport.auth import APIAuthenticator

class FioraHTTPRoutes:
    def __init__(self,server:FastMCP,service,imports,drive,token):
        self.server=server; self.service=service; self.imports=imports; self.drive=drive
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
        self.route("GET","/api/gmail/status",self.gmail_status)
        self.route("POST","/api/gmail/disconnect",self.disconnect)
        self.route("GET","/api/gmail/authorization-url",self.authorization_url)
        self.server.custom_route("/api/gmail/callback",methods=["GET"])(self.callback)
        self.route("GET","/api/drive/status",self.drive_status)
        self.route("GET","/api/drive/authorization-url",self.drive_authorization_url)
        self.route("POST","/api/drive/disconnect",self.drive_disconnect)
        self.route("GET","/api/drive/folders",self.drive_folders)
        self.route("POST","/api/imports/drive-folder",self.drive_import)
        self.route("GET","/api/imports",self.drive_jobs)
        self.route("GET","/api/imports/{job_id}",self.drive_job)
        self.server.custom_route("/api/drive/callback",methods=["GET"])(self.drive_callback)
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
    async def sync(self,r): return await anyio.to_thread.run_sync(self.imports.sync_all,self.service)
    async def gmail_status(self,r): return await anyio.to_thread.run_sync(self.imports.status)
    async def disconnect(self,r): return self.imports.disconnect()
    async def authorization_url(self,r): return {"url":self.imports.oauth.authorization_url()}
    async def drive_status(self,r): return await anyio.to_thread.run_sync(self.drive.status)
    async def drive_authorization_url(self,r): return {"url":self.drive.oauth.authorization_url()}
    async def drive_disconnect(self,r): return self.drive.disconnect()
    async def drive_folders(self,r): return {"folders":await anyio.to_thread.run_sync(self.drive.folders,r.query_params.get("parent") or None)}
    async def drive_import(self,r):
        payload=await r.json()
        return await anyio.to_thread.run_sync(self.drive.import_folder,payload.get("folder",""),bool(payload.get("recursive",True)),payload.get("password") or None)
    async def drive_jobs(self,r): return {"jobs":self.drive.jobs(int(r.query_params.get("limit",10)))}
    async def drive_job(self,r): return self.drive.job(r.path_params["job_id"])
    async def drive_callback(self,request):
        if request.query_params.get("error"):
            return HTMLResponse(f"<h2>Google Drive was not connected</h2><p>{escape(request.query_params['error'])}</p>",status_code=400)
        try:
            state=request.query_params.get("state","")
            # Google's redirect carries no session: the signed state says who started it.
            with tenancy.acting_as(self.drive.oauth.user_of(state)):
                email=await anyio.to_thread.run_sync(self.drive.connect,str(request.url),state)
            return HTMLResponse(f"<h2>Google Drive connected to Luna Fiora.</h2><p>Signed in as {escape(email)}. You can close this tab.</p>")
        except Exception as e:return HTMLResponse(f"<h2>Google Drive was not connected</h2><p>{escape(str(e))}</p>",status_code=400)
    async def callback(self,request):
        if request.query_params.get("error"):
            return HTMLResponse(f"<h2>Gmail was not connected</h2><p>{escape(request.query_params['error'])}</p>",status_code=400)
        try:
            state=request.query_params.get("state","")
            # Google's redirect carries no session: the signed state says who started it.
            with tenancy.acting_as(self.imports.oauth.user_of(state)):
                email=await anyio.to_thread.run_sync(self.imports.connect,str(request.url),state)
            return HTMLResponse(f"<h2>Gmail connected to Luna Fiora.</h2><p>Signed in as {escape(email)}. You can close this tab.</p>")
        except Exception as e:return HTMLResponse(f"<h2>Gmail was not connected</h2><p>{escape(str(e))}</p>",status_code=400)