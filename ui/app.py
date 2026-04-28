"""
Brand Scout — thin shim, preserved for backward compatibility.
Run:
    cd /Users/isabelatucha && python3 -m streamlit run sedge/ui/app.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import streamlit as st
from ui.brand_scout_page import render_brand_scout_page

st.set_page_config(
    page_title="Brand Scout · BrokerFlow",
    page_icon="🌾",
    layout="wide",
    initial_sidebar_state="expanded",
)

render_brand_scout_page()
