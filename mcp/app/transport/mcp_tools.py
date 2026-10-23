from datetime import date
class FioraMCPTools:
    def __init__(self,server,service,imports):
        @server.tool()
        def list_transactions(start:str|None=None,end:str|None=None):
            return service.list("transactions",date.fromisoformat(start) if start else None,date.fromisoformat(end) if end else None)
        @server.tool()
        def add_transaction(occurred_at:str,kind:str,amount:float,merchant:str,category:str="Uncategorized",account:str|None=None,notes:str|None=None):
            return service.create("transactions",locals())
        @server.tool()
        def update_transaction(transaction_id:int,occurred_at:str,kind:str,amount:float,merchant:str,category:str="Uncategorized",account:str|None=None,notes:str|None=None):
            payload=locals(); payload.pop("transaction_id"); return service.update("transactions",transaction_id,payload)
        @server.tool()
        def delete_transaction(transaction_id:int): return service.delete("transactions",transaction_id)
        @server.tool()
        def list_commitments(): return service.list("commitments")
        @server.tool()
        def create_commitment(kind:str,name:str,amount:float,day_of_month:int,start_date:str,end_date:str|None=None,active:bool=True):
            return service.create("commitments",locals())
        @server.tool()
        def update_commitment(commitment_id:int,kind:str,name:str,amount:float,day_of_month:int,start_date:str,end_date:str|None=None,active:bool=True):
            payload=locals(); payload.pop("commitment_id"); return service.update("commitments",commitment_id,payload)
        @server.tool()
        def delete_commitment(commitment_id:int): return service.delete("commitments",commitment_id)
        @server.tool()
        def list_goals(): return service.list("goals")
        @server.tool()
        def create_goal(name:str,target_amount:float,target_date:str,current_amount:float=0,priority:str="medium",notes:str|None=None):
            return service.create("goals",locals())
        @server.tool()
        def update_goal(goal_id:int,name:str,target_amount:float,target_date:str,current_amount:float=0,priority:str="medium",notes:str|None=None):
            payload=locals(); payload.pop("goal_id"); return service.update("goals",goal_id,payload)
        @server.tool()
        def delete_goal(goal_id:int): return service.delete("goals",goal_id)
        @server.tool()
        def estimate_goal_savings(goal_id:int): return service.goal_projection(goal_id)
        @server.tool()
        def list_reminders(): return service.list("reminders")
        @server.tool()
        def create_reminder(title:str,due_at:str,recurrence:str="none",entity_type:str="general",entity_id:int|None=None,completed:bool=False):
            return service.create("reminders",locals())
        @server.tool()
        def update_reminder(reminder_id:int,title:str,due_at:str,recurrence:str="none",entity_type:str="general",entity_id:int|None=None,completed:bool=False):
            payload=locals(); payload.pop("reminder_id"); return service.update("reminders",reminder_id,payload)
        @server.tool()
        def delete_reminder(reminder_id:int): return service.delete("reminders",reminder_id)
        @server.tool()
        def financial_analytics(start:str,end:str): return service.analytics(date.fromisoformat(start),date.fromisoformat(end))
        @server.tool()
        def sync_gmail_transactions(): return imports.sync_all(service)