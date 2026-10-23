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