from datetime import date
from app.core.models import TransactionInput, CommitmentInput, GoalInput, ReminderInput
from app.data.repositories import FinanceRepository

MODELS={"transactions":TransactionInput,"commitments":CommitmentInput,"goals":GoalInput,"reminders":ReminderInput}
class FioraService:
    def __init__(self,repo:FinanceRepository): self.repo=repo
    def list(self,resource,start=None,end=None): return self.repo.list(resource,start,end)
    def create(self,resource,payload):
        model=MODELS[resource].model_validate(payload)
        return self.repo.create(resource,model.model_dump())
    def update(self,resource,item_id,payload):
        model=MODELS[resource].model_validate(payload)
        return self.repo.update(resource,item_id,model.model_dump())
    def delete(self,resource,item_id): return {"deleted":self.repo.delete(resource,item_id),"id":item_id}
    def analytics(self,start:date,end:date): return self.repo.analytics(start,end)
    def dashboard(self,start:date,end:date):
        return {"analytics":self.analytics(start,end),"transactions":self.list("transactions",start,end),
                "commitments":self.list("commitments"),"goals":self.list("goals"),
                "reminders":self.list("reminders")}
    def goal_projection(self,goal_id:int):
        goals=[g for g in self.list("goals") if g["id"]==goal_id]
        if not goals: raise ValueError("Goal not found")
        g=goals[0]; today=date.today(); months=max(1,(g["target_date"].year-today.year)*12+g["target_date"].month-today.month)
        remaining=max(0,g["target_amount"]-g["current_amount"])
        return {**g,"remaining":remaining,"months_remaining":months,"monthly_saving_required":remaining/months}