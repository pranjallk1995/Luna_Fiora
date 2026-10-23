import pandas as pd
import plotly.express as px
import streamlit as st
def render(api,d):
    a=d.analytics; cols=st.columns(3)
    cols[0].metric("Income",f"₹{a['income']:,.2f}"); cols[1].metric("Expenditure",f"₹{a['expense']:,.2f}"); cols[2].metric("Net savings",f"₹{a['net']:,.2f}")
    left,right=st.columns([3,2])
    with left:
        st.subheader("Cash flow")
        trend=pd.DataFrame(a["trend"])
        if trend.empty: st.info("No transactions in this date range.")
        else: st.plotly_chart(px.line(trend,x="day",y=["income","expense"],markers=True),use_container_width=True)
    with right:
        st.subheader("Expense categories")
        categories=pd.DataFrame(a["categories"])
        if categories.empty: st.info("No expenses in this date range.")
        else: st.plotly_chart(px.pie(categories,names="category",values="total",hole=.58),use_container_width=True)
    st.subheader("Gmail transaction import")
    c1,c2=st.columns([3,1])
    try:c1.link_button("Connect Gmail",api.gmail_url(),icon=":material/mail:",use_container_width=True)
    except Exception:c1.info("Add Gmail OAuth settings to connect an inbox.")
    if c2.button("Sync now",icon=":material/sync:",use_container_width=True): api.sync_gmail(); st.rerun()