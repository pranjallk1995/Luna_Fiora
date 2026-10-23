from datetime import date
from pathlib import Path
import httpx
import streamlit as st
from auth import OIDCAuthentication
from config import UIConfig
from domain.dashboard import Dashboard
from services.api import FioraAPI
from styles import LunaStyle
from views import overview, transactions, plans, goals

class LunaFioraApp:
    NAV = {
        "Overview": (":material/finance_mode:", overview.render),
        "Transactions": (":material/receipt_long:", transactions.render),
        "EMIs & SIPs": (":material/account_balance:", plans.render),
        "Goals & reminders": (":material/flag:", goals.render),
    }
    def __init__(self):
        self.config = UIConfig.from_env()
        self.api = FioraAPI(self.config)
    def header(self):
        brand, actions = st.columns([5, 4], vertical_alignment="center", gap="medium")
        with brand:
            st.markdown('<div class="lv-header"><div class="lv-placeholder">◌</div><div><h1 class="lv-title">Luna Fiora</h1><p class="lv-subtitle">Private AI-managed personal finance</p></div></div>', unsafe_allow_html=True)
        with actions:
            dates, logout = st.columns([5, 1], vertical_alignment="center")
            with dates:
                selected = st.date_input("Date range", value=(st.session_state.start, st.session_state.end), label_visibility="collapsed", key="header_date_range")
                if isinstance(selected, (tuple, list)) and len(selected) == 2:
                    st.session_state.start, st.session_state.end = selected
            with logout:
                st.button("Sign out", icon=":material/logout:", key="header_sign_out", on_click=st.logout, use_container_width=True)
    def render(self):
        LunaStyle.apply()
        OIDCAuthentication(self.config.allowed_emails).require_login()
        today = date.today()
        if "start" not in st.session_state:
            st.session_state.start = today.replace(day=1)
        if "end" not in st.session_state:
            st.session_state.end = today
        self.header()
        labels = list(self.NAV)
        nav = st.segmented_control("Navigation", labels, default=labels[0], format_func=lambda x: f"{self.NAV[x][0]} {x}", label_visibility="collapsed", key="fiora_navigation")
        try:
            dashboard = Dashboard.from_payload(self.api.dashboard(st.session_state.start, st.session_state.end))
        except httpx.HTTPError as error:
            st.error(f"Luna Fiora service is unavailable: {error}")
            st.stop()
        self.NAV[nav or labels[0]][1](self.api, dashboard)
    @classmethod
    def run(cls):
        st.set_page_config(page_title="Luna Fiora", page_icon=str(Path(__file__).parent / "assets" / "lunafiora_logo.png"), layout="wide", initial_sidebar_state="collapsed")
        cls().render()

if __name__ == "__main__":
    LunaFioraApp.run()
