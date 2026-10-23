from datetime import datetime
import pandas as pd
import streamlit as st
def render(api,d):
    with st.form("transaction_form",border=True):
        st.subheader("Add transaction")
        c1,c2,c3=st.columns(3); kind=c1.selectbox("Type",["expense","income"]); amount=c2.number_input("Amount",min_value=0.01); when=c3.date_input("Date")
        merchant=st.text_input("Merchant or source"); category=st.text_input("Category",value="Uncategorized"); account=st.text_input("Account")
        if st.form_submit_button("Add transaction",icon=":material/add:",use_container_width=True):
            api.create("transactions",{"occurred_at":datetime.combine(when,datetime.min.time()).isoformat(),"kind":kind,"amount":amount,"merchant":merchant,"category":category,"account":account or None}); st.rerun()
    st.subheader("Transactions")
    if d.transactions: st.dataframe(pd.DataFrame(d.transactions),use_container_width=True,hide_index=True)
    else: st.info("No transactions in this date range.")