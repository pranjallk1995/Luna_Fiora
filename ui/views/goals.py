from datetime import date,datetime,timedelta
import pandas as pd
import streamlit as st
def render(api,d):
    goal_tab,reminder_tab=st.tabs(["Goals","Reminders"])
    with goal_tab:
      with st.form("goal_form",border=True):
        st.subheader("Create financial goal")
        name=st.text_input("Goal name"); c1,c2,c3=st.columns(3); target=c1.number_input("Target",min_value=0.01); saved=c2.number_input("Already saved",min_value=0.0); due=c3.date_input("Target date",value=date.today()+timedelta(days=365))
        if st.form_submit_button("Create goal",use_container_width=True): api.create("goals",{"name":name,"target_amount":target,"current_amount":saved,"target_date":due.isoformat(),"priority":"medium"}); st.rerun()
      if d.goals: st.dataframe(pd.DataFrame(d.goals),use_container_width=True,hide_index=True)
      else: st.info("No financial goals yet.")
    with reminder_tab:
      with st.form("reminder_form",border=True):
        title=st.text_input("Reminder"); due=st.date_input("Due date",value=date.today()+timedelta(days=1)); recurrence=st.selectbox("Repeat",["none","monthly","yearly"])
        if st.form_submit_button("Add reminder",use_container_width=True): api.create("reminders",{"title":title,"due_at":datetime.combine(due,datetime.min.time()).isoformat(),"recurrence":recurrence,"entity_type":"general"}); st.rerun()
      if d.reminders: st.dataframe(pd.DataFrame(d.reminders),use_container_width=True,hide_index=True)
      else: st.info("No reminders yet.")