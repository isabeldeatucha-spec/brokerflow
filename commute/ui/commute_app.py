import os
import sys
import time
from datetime import datetime

import streamlit as st

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from commute.agent.graph import plan_commute
from commute.data import mbta, bluebike, passio, google_maps, apple_maps, outlook
from commute.config import MIT_SLOAN_ADDRESS

st.set_page_config(
    page_title="MIT Sloan Commute Planner",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
  html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
  .main { background: #f8f9fa; }

  .mit-header {
    background: linear-gradient(135deg, #A31F34 0%, #8B1A2C 100%);
    color: white;
    padding: 1.5rem 2rem;
    border-radius: 12px;
    margin-bottom: 1.5rem;
  }
  .mit-header h1 { margin: 0; font-size: 1.8rem; font-weight: 700; }
  .mit-header p { margin: 0.25rem 0 0; opacity: 0.85; font-size: 0.95rem; }

  .option-card {
    background: white;
    border: 1px solid #e0e0e0;
    border-radius: 10px;
    padding: 1rem 1.25rem;
    margin-bottom: 0.75rem;
    border-left: 4px solid #A31F34;
  }
  .option-card.best {
    border-left: 4px solid #28a745;
    background: #f0fff4;
  }
  .option-card h4 { margin: 0 0 0.5rem; font-size: 1rem; font-weight: 600; }
  .option-card .time-badge {
    background: #A31F34;
    color: white;
    padding: 2px 10px;
    border-radius: 20px;
    font-size: 0.8rem;
    font-weight: 600;
  }

  .event-card {
    background: #002244;
    color: white;
    border-radius: 10px;
    padding: 1rem 1.25rem;
    margin-bottom: 1rem;
  }
  .event-card h4 { margin: 0; font-size: 1rem; color: #cce5ff; }
  .event-card p { margin: 0.25rem 0 0; font-size: 1.1rem; font-weight: 600; }

  .recommendation-box {
    background: white;
    border: 2px solid #28a745;
    border-radius: 12px;
    padding: 1.25rem 1.5rem;
    margin-top: 1rem;
  }
  .recommendation-box h3 { color: #28a745; margin-top: 0; }

  .status-pill {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 12px;
    font-size: 0.75rem;
    font-weight: 600;
    margin-left: 6px;
  }
  .pill-live { background: #d4edda; color: #155724; }
  .pill-unavail { background: #f8d7da; color: #721c24; }

  .sidebar-section { margin-bottom: 1.5rem; }
  div[data-testid="stSidebar"] { background: #1a1a2e; }
  div[data-testid="stSidebar"] label { color: #e0e0e0 !important; }
  div[data-testid="stSidebar"] .stMarkdown p { color: #aaa; font-size: 0.85rem; }
</style>
""", unsafe_allow_html=True)


def render_header():
    st.markdown("""
    <div class="mit-header">
      <h1>🎓 MIT Sloan Commute Planner</h1>
      <p>Real-time routing to 50 Memorial Drive, Cambridge MA — powered by MBTA, Bluebikes, MIT Shuttle, Google Maps & Apple Maps</p>
    </div>
    """, unsafe_allow_html=True)


def render_sidebar() -> tuple[str, int, str, bool]:
    with st.sidebar:
        st.markdown("## 🏠 Your Commute")

        home_address = st.text_input(
            "Home Address",
            value=st.session_state.get("home_address", ""),
            placeholder="e.g. 123 Main St, Boston MA",
            help="Your starting address. Geocoded automatically.",
        )

        buffer = st.slider(
            "Buffer time (minutes)",
            min_value=5,
            max_value=45,
            value=st.session_state.get("buffer_minutes", 15),
            step=5,
            help="How many minutes early do you want to arrive?",
        )

        st.markdown("---")
        st.markdown("## 📅 Outlook Calendar")
        user_email = st.text_input(
            "Work email (for Outlook)",
            value=st.session_state.get("user_email", ""),
            placeholder="you@mit.edu",
            help="Pulls your next MIT Sloan commitment.",
        )

        st.markdown("---")
        st.markdown("## ⚙️ API Status")
        _render_api_status()

        st.markdown("---")
        plan_clicked = st.button("🚀 Plan My Commute", type="primary", use_container_width=True)

        if home_address:
            st.session_state["home_address"] = home_address
        st.session_state["buffer_minutes"] = buffer
        st.session_state["user_email"] = user_email

    return home_address, buffer, user_email, plan_clicked


def _render_api_status():
    checks = {
        "MBTA": True,
        "Bluebikes": True,
        "Google Maps": bool(os.getenv("GOOGLE_MAPS_API_KEY") or os.getenv("OUTSCRAPER_API_KEY")),
        "Apple Maps": bool(os.getenv("APPLE_MAPS_KEY_ID")),
        "MIT Shuttle": True,
        "Outlook": bool(os.getenv("AZURE_CLIENT_ID")),
    }
    for name, available in checks.items():
        tag = f'<span class="status-pill pill-live">✓ Live</span>' if available else \
              f'<span class="status-pill pill-unavail">! Config needed</span>'
        st.markdown(f"**{name}** {tag}", unsafe_allow_html=True)


def render_outlook_event(next_event: dict | None, buffer: int):
    if not next_event:
        st.info("No Outlook events found today. Set AZURE credentials or check your email setting.")
        return

    arrival_str = next_event.get("arrival_needed_str", next_event.get("start_str", ""))
    st.markdown(f"""
    <div class="event-card">
      <h4>📅 Next commitment</h4>
      <p>{next_event['subject']}</p>
      <small style="color:#aecbfa">Starts {next_event['start_str']}
      {"@ " + next_event['location'] if next_event.get('location') else ""}
      &nbsp;·&nbsp; Arrive by <strong>{arrival_str}</strong> ({buffer}min buffer)</small>
    </div>
    """, unsafe_allow_html=True)


def render_live_transit(lat: float, lon: float):
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("#### 🚇 MBTA")
        with st.spinner("Fetching MBTA..."):
            try:
                options = mbta.get_transit_options(lat, lon)
                _render_mbta_options(options)
            except Exception as e:
                st.error(f"MBTA error: {e}")

    with col2:
        st.markdown("#### 🚲 Bluebikes")
        with st.spinner("Fetching Bluebikes..."):
            try:
                bike_opts = bluebike.get_bike_options(lat, lon)
                for opt in bike_opts[:2]:
                    if "error" in opt:
                        st.warning(opt["error"])
                        continue
                    st.markdown(f"""
                    <div class="option-card">
                      <h4>🚲 {opt['origin_station'][:30]}</h4>
                      Walk: {opt['walk_to_station_min']}min · Bikes: {opt['available_bikes']} available<br>
                      Ride: {opt['ride_min']}min · <strong>Total: ~{int(opt['total_min'])}min</strong>
                    </div>
                    """, unsafe_allow_html=True)
            except Exception as e:
                st.error(f"Bluebike error: {e}")

    with col3:
        st.markdown("#### 🚐 MIT Shuttle")
        with st.spinner("Fetching MIT Shuttle..."):
            try:
                shuttle_opts = passio.get_shuttle_options(lat, lon)
                for opt in shuttle_opts[:3]:
                    if "error" in opt:
                        st.warning(opt["error"])
                        continue
                    st.markdown(f"""
                    <div class="option-card">
                      <h4>🚐 {opt['route']}</h4>
                      From: {opt['origin_stop'][:25]}<br>
                      Walk: {opt['walk_to_stop_min']}min · Shuttle in: {opt['shuttle_in_min']}min<br>
                      <strong>Total: ~{int(opt['total_est_min'])}min</strong>
                    </div>
                    """, unsafe_allow_html=True)
            except Exception as e:
                st.error(f"MIT Shuttle error: {e}")


def _render_mbta_options(options: dict):
    shown = 0
    for stop_data in options.get("subway", [])[:1]:
        stop = stop_data["stop"]
        preds = stop_data["predictions"]
        for p in preds[:2]:
            st.markdown(f"""
            <div class="option-card">
              <h4>🚇 {p['route_name']}</h4>
              From: {stop['name']}<br>
              Walk: {stop['walk_minutes']}min · Departs in: {p['minutes_away']}min<br>
              <small>{p['departure_time']}</small>
            </div>
            """, unsafe_allow_html=True)
            shown += 1

    for stop_data in options.get("bus", [])[:1]:
        stop = stop_data["stop"]
        preds = stop_data["predictions"]
        for p in preds[:1]:
            st.markdown(f"""
            <div class="option-card">
              <h4>🚌 {p['route_name'] or 'Route ' + p['route_id']}</h4>
              From: {stop['name']}<br>
              Walk: {stop['walk_minutes']}min · In: {p['minutes_away']}min
            </div>
            """, unsafe_allow_html=True)
            shown += 1

    for stop_data in options.get("commuter_rail", [])[:1]:
        stop = stop_data["stop"]
        preds = stop_data["predictions"]
        for p in preds[:1]:
            st.markdown(f"""
            <div class="option-card">
              <h4>🚂 {p['route_name']}</h4>
              From: {stop['name']}<br>
              Walk: {stop['walk_minutes']}min · Departs: {p['departure_time']}
            </div>
            """, unsafe_allow_html=True)
            shown += 1

    if shown == 0:
        st.info("No MBTA departures found near this address.")


def render_maps_routes(address: str, lat: float, lon: float):
    st.markdown("#### 🗺️ Route Times")
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Google Maps**")
        with st.spinner("Google Maps..."):
            try:
                gm_results = google_maps.get_all_routes(address)
                mode_icons = {"transit": "🚇", "walking": "🚶", "bicycling": "🚲"}
                for mode, data in gm_results.items():
                    icon = mode_icons.get(mode, "🗺️")
                    if "error" in data:
                        st.caption(f"{icon} {mode}: unavailable")
                    else:
                        dep = f" · departs {data['departure_time']}" if data.get("departure_time") else ""
                        st.metric(f"{icon} {mode.title()}", f"{data['duration_min']} min", data.get("distance", ""))
            except Exception as e:
                st.error(f"Google Maps error: {e}")

    with col2:
        st.markdown("**Apple Maps**")
        with st.spinner("Apple Maps..."):
            try:
                am_results = apple_maps.get_all_routes(lat, lon)
                mode_icons = {"Transit": "🚇", "Walking": "🚶", "Automobile": "🚗"}
                for mode, data in am_results.items():
                    icon = mode_icons.get(mode, "🗺️")
                    if "error" in data:
                        st.caption(f"{icon} {mode}: unavailable")
                    else:
                        st.metric(f"{icon} {mode}", f"{data['duration_min']} min", f"{data['distance_miles']}mi")
            except Exception as e:
                st.error(f"Apple Maps error: {e}")


def render_ai_recommendation(result: dict):
    rec = result.get("recommendation", "")
    if not rec:
        rec = "No recommendation generated."

    st.markdown("""
    <div class="recommendation-box">
      <h3>🤖 AI Recommendation</h3>
    """, unsafe_allow_html=True)
    st.markdown(rec)
    st.markdown("</div>", unsafe_allow_html=True)


def main():
    render_header()
    home_address, buffer, user_email, plan_clicked = render_sidebar()

    if not plan_clicked and "last_result" not in st.session_state:
        st.markdown("""
        ### Welcome to your MIT Sloan Commute Planner

        Enter your **home address** and **buffer time** in the sidebar, then click **Plan My Commute**.

        The app will check:
        - 🚇 **MBTA** — Red Line, buses, commuter rail (live predictions)
        - 🚲 **Bluebikes** — nearest station availability + ride time
        - 🚐 **MIT Shuttle** — live ETAs from Passio GO
        - 🗺️ **Google Maps** — real-time transit, walking, cycling routes
        - 🍎 **Apple Maps** — transit, walking, driving times
        - 📅 **Outlook** — next MIT Sloan commitment so you know your deadline

        Then an AI agent synthesizes everything into a single recommendation.

        ---
        **Setup**: add API keys to your `.env` file. See the README for required keys.
        """)
        return

    if not home_address:
        st.warning("Please enter your home address in the sidebar.")
        return

    st.markdown(f"### Commute from: `{home_address}`")

    if plan_clicked:
        with st.spinner("🔍 Gathering real-time commute data and analyzing options..."):
            start = time.time()
            result = plan_commute(
                home_address=home_address,
                buffer_minutes=buffer,
                user_email=user_email,
            )
            elapsed = time.time() - start
        st.session_state["last_result"] = result
        st.session_state["last_address"] = home_address
        st.session_state["last_lat"] = result.get("origin_lat", 0.0)
        st.session_state["last_lon"] = result.get("origin_lon", 0.0)
        st.caption(f"Analysis completed in {elapsed:.1f}s")
    else:
        result = st.session_state.get("last_result", {})

    lat = st.session_state.get("last_lat", 0.0)
    lon = st.session_state.get("last_lon", 0.0)
    next_event = result.get("next_event")

    if next_event:
        render_outlook_event(next_event, buffer)

    st.markdown("---")
    st.markdown("### 🕐 Live Transit Options")
    if lat and lon:
        render_live_transit(lat, lon)

    st.markdown("---")
    if lat and lon:
        render_maps_routes(home_address, lat, lon)

    st.markdown("---")
    render_ai_recommendation(result)

    st.markdown("---")
    st.caption(f"Destination: {MIT_SLOAN_ADDRESS} · Refreshed at {datetime.now().strftime('%I:%M:%S %p')}")

    if st.button("🔄 Refresh"):
        st.rerun()


if __name__ == "__main__":
    main()
