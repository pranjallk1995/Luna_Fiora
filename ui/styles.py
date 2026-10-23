import streamlit as st
class LunaStyle:
 @staticmethod
 def apply():
  st.html("""<style>
  :root{--lv-bg:#111;--lv-surface:rgba(255,255,255,.055);--lv-control:rgba(255,255,255,.07);--lv-hover:rgba(255,255,255,.12);--lv-text:#f5f5f5;--lv-muted:#a3a3a3;--lv-border:rgba(255,255,255,.14);--lv-strong:rgba(255,255,255,.34)}
  .stApp{background:var(--lv-bg);color:var(--lv-text)} .block-container{max-width:1180px;padding-top:2.35rem;padding-bottom:3rem}
  header[data-testid="stHeader"]{background:transparent} #MainMenu,footer,div[data-testid="stDecoration"]{display:none}
  .lv-header{display:flex;align-items:center;gap:1rem;min-height:4.5rem;margin-bottom:1rem}.lv-placeholder{width:5.75rem;height:4.5rem;display:grid;place-items:center;border:1px solid var(--lv-border);border-radius:.9rem;font-size:2rem}
  .lv-title{margin:0;font-size:clamp(1.65rem,3vw,2.15rem);font-weight:720;letter-spacing:-.04em;line-height:1}.lv-subtitle{margin:.32rem 0 0;color:var(--lv-muted);font-size:.78rem}
  div[data-testid="stHorizontalBlock"]:has(.lv-header){align-items:center;margin-bottom:.55rem}
  .st-key-fiora_navigation div[data-testid="stButtonGroup"]{display:flex;gap:.2rem;margin:.2rem 0 1.15rem;padding:.4rem;border:1px solid var(--lv-border);border-radius:.9rem;background:var(--lv-surface)}
  .st-key-fiora_navigation button{flex:1;min-height:2.55rem;color:var(--lv-muted)!important;background:var(--lv-control)!important;border:1px solid transparent!important}
  .st-key-fiora_navigation button[aria-pressed="true"]{background:var(--lv-hover)!important;border-color:var(--lv-strong)!important}
  div[data-testid="stMetric"],div[data-testid="stForm"]{background:var(--lv-surface);border:1px solid var(--lv-border);border-radius:.9rem;padding:1rem}
  @media(max-width:700px){.block-container{padding:.85rem .8rem 2rem}.lv-subtitle{display:none}.lv-placeholder{width:4.25rem;height:3.5rem}.st-key-header_sign_out button p,.st-key-fiora_navigation button p{font-size:0}.st-key-header_sign_out button{width:2.625rem!important;padding:0!important}}
  </style>""")