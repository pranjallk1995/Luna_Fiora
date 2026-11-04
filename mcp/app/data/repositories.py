from datetime import date
from .database import Database

class FinanceRepository:
    TABLES={"transactions","commitments","goals","reminders"}
    def __init__(self, db: Database): self.db=db
    def list(self, table, start=None, end=None):
        if table not in self.TABLES: raise ValueError("Unsupported resource")
        query=f"SELECT * FROM {table}"
        params=[]
        if table=="transactions" and start and end:
            query+=" WHERE occurred_at::date BETWEEN %s AND %s"; params=[start,end]
        query+=" ORDER BY id DESC"
        with self.db.cursor() as c: c.execute(query,params); return c.fetchall()
    def create(self, table, values):
        if table not in self.TABLES: raise ValueError("Unsupported resource")
        keys=list(values); cols=",".join(keys); marks=",".join(["%s"]*len(keys))
        with self.db.cursor() as c:
            c.execute(f"INSERT INTO {table} ({cols}) VALUES ({marks}) RETURNING *",[values[k] for k in keys])
            return c.fetchone()
    def update(self, table, item_id, values):
        if table not in self.TABLES: raise ValueError("Unsupported resource")
        values={k:v for k,v in values.items() if v is not None}
        sets=",".join(f"{k}=%s" for k in values)
        with self.db.cursor() as c:
            c.execute(f"UPDATE {table} SET {sets} WHERE id=%s RETURNING *",[*values.values(),item_id])
            row=c.fetchone()
            if not row: raise ValueError(f"{table[:-1].title()} not found")
            return row
    def delete(self, table, item_id):
        if table not in self.TABLES: raise ValueError("Unsupported resource")
        with self.db.cursor() as c: c.execute(f"DELETE FROM {table} WHERE id=%s RETURNING id",[item_id]); return bool(c.fetchone())
    def analytics(self,start:date,end:date):
        with self.db.cursor() as c:
            c.execute("""SELECT kind, COALESCE(SUM(amount),0) total FROM transactions
                         WHERE occurred_at::date BETWEEN %s AND %s GROUP BY kind""",(start,end))
            totals={r["kind"]:r["total"] for r in c.fetchall()}
            c.execute("""SELECT category, SUM(amount) total FROM transactions
                         WHERE kind='expense' AND occurred_at::date BETWEEN %s AND %s
                         GROUP BY category ORDER BY total DESC""",(start,end))
            categories=c.fetchall()
            c.execute("""SELECT date_trunc('day',occurred_at)::date AS "day",
                         SUM(CASE WHEN kind='income' THEN amount ELSE 0 END) income,
                         SUM(CASE WHEN kind='expense' THEN amount ELSE 0 END) expense
                         FROM transactions WHERE occurred_at::date BETWEEN %s AND %s
                         GROUP BY day ORDER BY day""",(start,end))
            trend=c.fetchall()
        income=totals.get("income",0); expense=totals.get("expense",0)
        return {"start":start,"end":end,"income":income,"expense":expense,
                "net":income-expense,"categories":categories,"trend":trend}

class DriveImportRepository:
    """The Drive connection, import jobs, and the outcome of every file."""
    JOB_SELECT="""SELECT j.job_id::text AS job_id,j.folder_name,j.status,j.total,j.error,j.current_item,j.created_at,j.started_at,j.finished_at,
        (SELECT count(*) FROM drive_import_files f WHERE f.job_id=j.job_id) AS processed,
        (SELECT coalesce(sum(f.added),0)::int FROM drive_import_files f WHERE f.job_id=j.job_id) AS added,
        (SELECT coalesce(sum(f.matched),0)::int FROM drive_import_files f WHERE f.job_id=j.job_id) AS matched,
        coalesce((SELECT jsonb_object_agg(outcome,n) FROM (SELECT outcome,count(*) AS n FROM drive_import_files f WHERE f.job_id=j.job_id GROUP BY outcome) counts),'{}'::jsonb) AS outcomes
        FROM drive_import_jobs j"""
    def __init__(self,db:Database): self.db=db
    def _one(self,query,params=()):
        with self.db.cursor() as c: c.execute(query,params); return c.fetchone()
    def _all(self,query,params=()):
        with self.db.cursor() as c: c.execute(query,params); return c.fetchall()
    def connection(self): return self._one("SELECT email,encrypted_refresh_token FROM drive_connection")
    def save_connection(self,email,encrypted):
        with self.db.cursor() as c:
            c.execute("""INSERT INTO drive_connection(singleton,email,encrypted_refresh_token) VALUES(TRUE,%s,%s)
            ON CONFLICT(singleton) DO UPDATE SET email=EXCLUDED.email,encrypted_refresh_token=EXCLUDED.encrypted_refresh_token,connected_at=NOW()""",(email,encrypted))
    def delete_connection(self):
        with self.db.cursor() as c: c.execute("DELETE FROM drive_connection")
    def create_job(self,folder_id,folder_name,recursive):
        return self._one("INSERT INTO drive_import_jobs(folder_id,folder_name,recursive) VALUES(%s,%s,%s) RETURNING job_id::text AS job_id",(folder_id,folder_name,recursive))["job_id"]
    def job_request(self,job_id): return self._one("SELECT folder_id,recursive FROM drive_import_jobs WHERE job_id::text=%s",(job_id,))
    def job(self,job_id): return self._one(f"{self.JOB_SELECT} WHERE j.job_id::text=%s",(job_id,))
    def jobs(self,limit): return self._all(f"{self.JOB_SELECT} ORDER BY j.created_at DESC LIMIT %s",(limit,))
    def unfinished_jobs(self):
        return [row["job_id"] for row in self._all("SELECT job_id::text AS job_id FROM drive_import_jobs WHERE status IN ('queued','listing','running') ORDER BY created_at")]
    def update_job(self,job_id,started=False,finished=False,**fields):
        assignments=[f"{name}=%s" for name in fields]
        if started: assignments.append("started_at=COALESCE(started_at,NOW())")
        if finished: assignments.append("finished_at=NOW()")
        with self.db.cursor() as c: c.execute(f"UPDATE drive_import_jobs SET {','.join(assignments)} WHERE job_id::text=%s",(*fields.values(),job_id))
    def files(self,job_id):
        return self._all("SELECT file_id,name,path,outcome,added,matched,rejected,error FROM drive_import_files WHERE job_id::text=%s ORDER BY created_at",(job_id,))
    def file_recorded(self,job_id,file_id):
        return self._one("SELECT 1 AS found FROM drive_import_files WHERE job_id::text=%s AND file_id=%s",(job_id,file_id)) is not None
    def already_imported(self,file_id,version):
        return self._one("SELECT 1 AS found FROM drive_import_files WHERE file_id=%s AND outcome='imported' AND version IS NOT DISTINCT FROM %s LIMIT 1",(file_id,version)) is not None
    def record_file(self,job_id,file):
        with self.db.cursor() as c:
            c.execute("""INSERT INTO drive_import_files(job_id,file_id,version,name,path,outcome,added,matched,rejected,error)
            VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING""",
            (job_id,file["file_id"],file["version"],file["name"],file["path"],file["outcome"],file["added"],file["matched"],file["rejected"],file["error"]))
    def add_new_transactions(self,rows,own_ids):
        """Add a statement's rows together, leaving out what Fiora has from elsewhere; return (added, matched)."""
        added=matched=0
        with self.db.cursor() as c:
            for row in rows:
                c.execute("""SELECT 1 FROM transactions WHERE occurred_at::date=%s::date AND amount=%s AND kind=%s
                AND (external_id IS NULL OR external_id NOT LIKE %s) LIMIT 1""",(row["occurred_at"],row["amount"],row["kind"],own_ids))
                if c.fetchone(): matched+=1; continue
                keys=list(row)
                c.execute(f"INSERT INTO transactions ({','.join(keys)}) VALUES ({','.join(['%s']*len(keys))}) ON CONFLICT(external_id) DO NOTHING RETURNING id",[row[k] for k in keys])
                if c.fetchone(): added+=1
        return added,matched
