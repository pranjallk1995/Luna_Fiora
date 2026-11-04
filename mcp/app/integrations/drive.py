"""Read-only Google Drive access: the sign-in and a client that lists and downloads statements."""
import re
from dataclasses import dataclass
from app.integrations.google_oauth import GoogleOAuth, renewing_credentials

SCOPES=["https://www.googleapis.com/auth/drive.readonly"]
FOLDER_TYPE="application/vnd.google-apps.folder"
SHEET_TYPE="application/vnd.google-apps.spreadsheet"
# Files Fiora can read rows from; a Google Sheet is exported as CSV.
READABLE=frozenset({"application/pdf","text/csv","text/plain",SHEET_TYPE})
FILE_FIELDS="id, name, mimeType, md5Checksum, modifiedTime"
FOLDER_LINK=re.compile(r"/folders/([A-Za-z0-9_-]{10,})")
DRIVE_ID=re.compile(r"[A-Za-z0-9_-]{25,}")

class DriveSignInExpired(ValueError):
    """Google no longer accepts the saved sign-in; the person has to connect Drive again."""
    def __init__(self,message="Your Google Drive sign-in has expired. Reconnect Google Drive from Fiora's overview to continue; your transactions are safe."):
        super().__init__(message)

@dataclass(frozen=True)
class DriveFile:
    """One Drive file and where it sits under the imported folder."""
    file_id:str; name:str; mime_type:str; md5:str|None=None; modified:str|None=None; path:str=""
    @property
    def version(self):
        """What identifies this version: the checksum, or for Google files the edit time."""
        return self.md5 or (f"modified:{self.modified}" if self.modified else None)
    @property
    def readable(self): return self.mime_type in READABLE
    @classmethod
    def from_api(cls,item,path=""):
        return cls(item["id"],item["name"],item["mimeType"],item.get("md5Checksum"),item.get("modifiedTime"),path)

class DriveOAuth(GoogleOAuth):
    SCOPES=SCOPES; SALT="fiora-drive"; PURPOSE="drive"; LABEL="Google Drive"
    def account_email(self,credentials): return DriveClient.from_credentials(credentials).account_email()

class DriveClient:
    """List folders and download files from one connected Drive account."""
    def __init__(self,service): self.service=service
    @classmethod
    def from_credentials(cls,credentials):
        from googleapiclient.discovery import build
        return cls(build("drive","v3",credentials=credentials,cache_discovery=False))
    @classmethod
    def from_refresh_token(cls,refresh_token,client_id,client_secret):
        return cls.from_credentials(renewing_credentials(refresh_token,client_id,client_secret,SCOPES,DriveSignInExpired))
    def account_email(self): return self.service.about().get(fields="user(emailAddress)").execute()["user"]["emailAddress"]
    def _list(self,query,fields=FILE_FIELDS):
        items,token=[],None
        while True:
            response=self.service.files().list(q=query,fields=f"nextPageToken, files({fields}, parents)",pageSize=1000,pageToken=token,orderBy="folder,name").execute()
            items.extend(response.get("files",[])); token=response.get("nextPageToken")
            if not token: return items
    def folders(self,parent_id=None):
        """Subfolders of parent_id, or of My Drive's root."""
        return [{"folder_id":item["id"],"name":item["name"]} for item in self._list(f"'{parent_id or 'root'}' in parents and mimeType = '{FOLDER_TYPE}' and trashed = false")]
    def resolve_folder(self,spec):
        """Accept a folder link, ID, or exact name; reject a name several folders share."""
        spec=spec.strip(); match=FOLDER_LINK.search(spec)
        if match or DRIVE_ID.fullmatch(spec):
            folder=self.service.files().get(fileId=match[1] if match else spec,fields="id, name, mimeType").execute()
            if folder["mimeType"]!=FOLDER_TYPE: raise ValueError(f"{folder['name']!r} is a file, not a folder.")
            return {"folder_id":folder["id"],"name":folder["name"]}
        escaped=spec.replace("\\","\\\\").replace("'","\\'")
        matches=self._list(f"name = '{escaped}' and mimeType = '{FOLDER_TYPE}' and trashed = false","id, name")
        if not matches: raise FileNotFoundError(f"No Drive folder is named {spec!r}.")
        if len(matches)>1: raise ValueError(f"{len(matches)} folders are named {spec!r}; pass one folder ID instead: {', '.join(item['id'] for item in matches)}.")
        return {"folder_id":matches[0]["id"],"name":matches[0]["name"]}
    def walk(self,folder_id,recursive=True,path=""):
        """Every file under the folder (including unreadable ones), with its subfolder path."""
        files=[]
        for item in self._list(f"'{folder_id}' in parents and trashed = false"):
            if item["mimeType"]==FOLDER_TYPE:
                if recursive: files.extend(self.walk(item["id"],True,f"{path}{item['name']}/"))
            else: files.append(DriveFile.from_api(item,path))
        return files
    def download(self,file):
        if file.mime_type==SHEET_TYPE: return self.service.files().export(fileId=file.file_id,mimeType="text/csv").execute()
        return self.service.files().get_media(fileId=file.file_id).execute()
