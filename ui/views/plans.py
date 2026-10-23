from datetime import date
import pandas as pd
import streamlit as st
def render(api,d):
    with st.form("plan_form",border=True):
        st.subheader("Add EMI or SIP")
        c1,c2,c3=st.columns(3); kind=c1.selectbox("Type",["emi","sip"]); name=c2.text_input("Name"); amount=c3.number_input("Monthly amount",min_value=0.01)
        day=st.slider("Day of month",1,31,1)
        if st.form_submit_button("Add plan",icon=":material/add:",use_container_width=True):
            api.create("commitments",{"kind":kind,"name":name,"amount":amount,"day_of_month":day,"start_date":date.today().isoformat(),"active":True}); st.rerun()
    if d.commitments: st.dataframe(pd.DataFrame(d.commitments),use_container_width=True,hide_index=True)
    else: st.info("No EMIs or SIPs yet.")