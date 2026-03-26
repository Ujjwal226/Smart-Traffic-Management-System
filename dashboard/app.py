"""
TrafficFlow AI – GreenWave Dashboard
=====================================
Streamlit-based real-time monitoring & analytics dashboard.
Launch:  streamlit run dashboard/app.py
"""
import sys, os, json, time, math
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime

# ── Project imports ──────────────────────────────────────
# Graceful import: config may fail on Streamlit Cloud (no SUMO installed)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
try:
    from config import RESULTS_FILE, VISION_API_PORT, PROJECT_ROOT
except SystemExit:
    # Fallback for Streamlit Cloud deployment (SUMO not available)
    PROJECT_ROOT = os.path.join(os.path.dirname(__file__), "..")
    RESULTS_FILE = os.path.join(PROJECT_ROOT, "results.json")
    VISION_API_PORT = 8000

# ── Page config ──────────────────────────────────────────
st.set_page_config(
    page_title="TrafficFlow AI – GreenWave",
    page_icon="🚦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ───────────────────────────────────────────
st.markdown("""
<style>
    /* Dark theme cards */
    .metric-card {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        border: 1px solid #0f3460;
        border-radius: 16px;
        padding: 20px 24px;
        text-align: center;
        box-shadow: 0 4px 24px rgba(0,0,0,0.3);
    }
    .metric-card h3 {
        color: #a8b2d1;
        font-size: 0.85rem;
        margin-bottom: 4px;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    .metric-card .value {
        color: #ccd6f6;
        font-size: 2.2rem;
        font-weight: 700;
        line-height: 1.2;
    }
    .metric-card .delta {
        font-size: 0.9rem;
        margin-top: 4px;
    }
    .delta-good { color: #64ffda; }
    .delta-bad  { color: #ff6b6b; }
    .stApp { background-color: #0a0a23; }
    header[data-testid="stHeader"] { background-color: #0a0a23; }
    .block-container { padding-top: 1rem; }
    h1, h2, h3 { color: #ccd6f6 !important; }
    .sidebar .sidebar-content { background-color: #112240; }
</style>
""", unsafe_allow_html=True)


# ── Helper: load results ────────────────────────────────
@st.cache_data(ttl=5)   # auto-refresh every 5 s
def load_results():
    """Load simulation results from JSON."""
    if not os.path.exists(RESULTS_FILE):
        return None
    with open(RESULTS_FILE) as f:
        return json.load(f)


def metric_card(label, value, delta=None, delta_good=True):
    """Render a styled metric card."""
    delta_html = ""
    if delta is not None:
        cls = "delta-good" if delta_good else "delta-bad"
        delta_html = f'<div class="delta {cls}">{delta}</div>'
    st.markdown(f"""
    <div class="metric-card">
        <h3>{label}</h3>
        <div class="value">{value}</div>
        {delta_html}
    </div>
    """, unsafe_allow_html=True)


# ── Sidebar ──────────────────────────────────────────────
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/traffic-light.png", width=60)
    st.title("GreenWave AI")
    st.caption("Adaptive Traffic Signal Control")
    st.divider()

    mode = st.radio(
        "🎛️ Simulation Mode",
        ["adaptive", "static", "vision_linked"],
        index=0,
        help="Choose controller mode for next simulation run",
    )
    st.divider()

    auto_refresh = st.toggle("🔄 Auto-Refresh (5s)", value=False)
    if auto_refresh:
        time.sleep(5)
        st.rerun()

    st.divider()
    st.markdown(f"**Results file:** `results.json`")
    st.markdown(f"**Vision API:** `http://localhost:{VISION_API_PORT}`")
    st.markdown(f"---\n*Built with ❤️ by Team GreenWave*")


# ── Load Data ────────────────────────────────────────────
data = load_results()

if data is None:
    st.warning("⚠️ No results.json found. Run the simulation first:")
    st.code("python3 simulation_module/sim_engine.py", language="bash")
    st.stop()

# ── Header ───────────────────────────────────────────────
st.markdown("# 🚦 TrafficFlow AI – GreenWave Dashboard")
st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  •  Mode: **{data.get('mode', 'N/A').upper()}**")

# ── KPI Cards Row ────────────────────────────────────────
k1, k2, k3, k4 = st.columns(4)

with k1:
    metric_card(
        "Total Vehicles",
        f"{data['total_vehicles']:,}",
        f"{data['simulation_steps']:,} steps",
    )

with k2:
    metric_card(
        "CO₂ Saved",
        f"{data['saved_co2_kg']:.1f} kg",
        f"↓ {data['saved_co2_kg']/data.get('baseline_idle_time',1)*100:.1f}% vs baseline",
        delta_good=True,
    )

with k3:
    avg_delay = data.get("avg_delay_per_vehicle", 0)
    metric_card(
        "Avg Delay / Vehicle",
        f"{avg_delay:.0f}s",
        "Lower is better",
        delta_good=avg_delay < 2000,
    )

with k4:
    perf = data.get("wall_clock_seconds", 0)
    metric_card(
        "Sim Runtime",
        f"{perf:.1f}s",
        f"{data['simulation_steps']/max(perf,1):.0f} steps/sec",
    )

st.divider()

# ── Charts Row ───────────────────────────────────────────
step_data = data.get("step_data", [])
if step_data:
    df = pd.DataFrame(step_data)

    c1, c2 = st.columns(2)

    # --- Active vs Idle Vehicles Over Time ---
    with c1:
        st.subheader("📊 Active vs Idle Vehicles")
        fig1 = go.Figure()
        fig1.add_trace(go.Scatter(
            x=df["step"], y=df["active_vehicles"],
            mode="lines", name="Active",
            line=dict(color="#64ffda", width=2),
            fill="tozeroy", fillcolor="rgba(100,255,218,0.1)",
        ))
        fig1.add_trace(go.Scatter(
            x=df["step"], y=df["idle_vehicles"],
            mode="lines", name="Idle (waiting)",
            line=dict(color="#ff6b6b", width=2),
            fill="tozeroy", fillcolor="rgba(255,107,107,0.1)",
        ))
        fig1.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            xaxis_title="Simulation Step",
            yaxis_title="Vehicles",
            height=380,
            margin=dict(l=40, r=20, t=30, b=40),
            legend=dict(orientation="h", y=1.12),
        )
        st.plotly_chart(fig1, use_container_width=True)

    # --- Cumulative Delay ---
    with c2:
        st.subheader("⏱️ Cumulative Delay")
        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(
            x=df["step"], y=df["total_delay"],
            mode="lines", name="Total Delay (s)",
            line=dict(color="#bd93f9", width=2.5),
            fill="tozeroy", fillcolor="rgba(189,147,249,0.1)",
        ))
        fig2.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            xaxis_title="Simulation Step",
            yaxis_title="Cumulative Delay (s)",
            height=380,
            margin=dict(l=40, r=20, t=30, b=40),
        )
        st.plotly_chart(fig2, use_container_width=True)

st.divider()

# ── CO2 Gauge + Congestion Breakdown ─────────────────────
g1, g2 = st.columns([1, 1])

with g1:
    st.subheader("🌿 CO₂ Emissions Savings")
    baseline_co2 = data["baseline_idle_time"] * data["emission_factor"]
    ai_co2 = data["ai_idle_time"] * data["emission_factor"]
    saved = data["saved_co2_kg"]
    reduction_pct = (saved / max(baseline_co2, 0.01)) * 100

    fig_gauge = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=reduction_pct,
        number={"suffix": "%", "font": {"size": 48, "color": "#64ffda"}},
        delta={"reference": 0, "increasing": {"color": "#64ffda"}},
        title={"text": "CO₂ Reduction vs Baseline", "font": {"color": "#a8b2d1", "size": 16}},
        gauge={
            "axis": {"range": [0, 100], "tickcolor": "#a8b2d1"},
            "bar": {"color": "#64ffda"},
            "bgcolor": "#1a1a2e",
            "bordercolor": "#0f3460",
            "steps": [
                {"range": [0, 30], "color": "rgba(255,107,107,0.2)"},
                {"range": [30, 60], "color": "rgba(255,217,61,0.2)"},
                {"range": [60, 100], "color": "rgba(100,255,218,0.2)"},
            ],
        },
    ))
    fig_gauge.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        font={"color": "#ccd6f6"},
        height=320,
        margin=dict(l=30, r=30, t=50, b=20),
    )
    st.plotly_chart(fig_gauge, use_container_width=True)

    # CO2 breakdown table
    co2_data = pd.DataFrame({
        "Metric": ["Baseline CO₂", "AI-Optimised CO₂", "CO₂ Saved", "Idle Time Saved"],
        "Value": [
            f"{baseline_co2:.1f} kg",
            f"{ai_co2:.1f} kg",
            f"{saved:.1f} kg",
            f"{data['idle_time_saved']:,} seconds",
        ],
    })
    st.dataframe(co2_data, use_container_width=True, hide_index=True)

with g2:
    st.subheader("🚗 Traffic Congestion Analysis")

    if step_data:
        # Compute congestion ratio over time
        df["congestion_ratio"] = df["idle_vehicles"] / df["active_vehicles"].clip(lower=1)

        fig3 = go.Figure()
        fig3.add_trace(go.Scatter(
            x=df["step"], y=df["congestion_ratio"],
            mode="lines",
            line=dict(color="#f8961e", width=2),
            fill="tozeroy", fillcolor="rgba(248,150,30,0.1)",
            name="Congestion Ratio",
        ))
        # Threshold line
        fig3.add_hline(
            y=0.8, line_dash="dash", line_color="#ff6b6b",
            annotation_text="High Congestion Threshold",
            annotation_font_color="#ff6b6b",
        )
        fig3.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            xaxis_title="Simulation Step",
            yaxis_title="Congestion Ratio (idle/active)",
            height=350,
            margin=dict(l=40, r=20, t=30, b=40),
        )
        st.plotly_chart(fig3, use_container_width=True)

    # Congestion pie – high vs moderate vs clear
    if step_data:
        high = len(df[df["congestion_ratio"] >= 0.8])
        moderate = len(df[(df["congestion_ratio"] >= 0.4) & (df["congestion_ratio"] < 0.8)])
        clear = len(df[df["congestion_ratio"] < 0.4])
        fig_pie = px.pie(
            values=[high, moderate, clear],
            names=["High 🔴", "Moderate 🟡", "Clear 🟢"],
            color_discrete_sequence=["#ff6b6b", "#ffd93d", "#64ffda"],
            hole=0.45,
        )
        fig_pie.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            font={"color": "#ccd6f6"},
            height=250,
            margin=dict(l=0, r=0, t=10, b=10),
            legend=dict(orientation="h", y=-0.1),
        )
        st.plotly_chart(fig_pie, use_container_width=True)

st.divider()

# ── Interactive Map ──────────────────────────────────────
st.subheader("🗺️ Network Map – Traffic Light Locations")

try:
    import folium
    from streamlit_folium import st_folium
    import xml.etree.ElementTree as ET

    # Parse SUMO net.xml for junction coords
    net_file = os.path.join(PROJECT_ROOT, "simulation_module", "osm.net.xml")
    junctions = []
    if os.path.exists(net_file):
        tree = ET.parse(net_file)
        root = tree.getroot()

        # Get projection offset
        location = root.find("location")
        net_offset = [0.0, 0.0]
        orig_boundary = None
        conv_boundary = None
        if location is not None:
            offset_str = location.get("netOffset", "0.0,0.0")
            parts = offset_str.split(",")
            net_offset = [float(parts[0]), float(parts[1])]
            orig_boundary = location.get("origBoundary", "")
            conv_boundary = location.get("convBoundary", "")

        # Extract junction positions
        for junc in root.findall("junction"):
            jtype = junc.get("type", "")
            if jtype == "traffic_light":
                x = float(junc.get("x", 0))
                y = float(junc.get("y", 0))
                jid = junc.get("id", "unknown")
                junctions.append({"id": jid, "x": x, "y": y})

    if junctions and orig_boundary:
        # Parse original boundary for lat/lon reference
        b = list(map(float, orig_boundary.split(",")))
        lon_min, lat_min, lon_max, lat_max = b[0], b[1], b[2], b[3]
        cb = list(map(float, conv_boundary.split(",")))
        cx_min, cy_min, cx_max, cy_max = cb[0], cb[1], cb[2], cb[3]

        center_lat = (lat_min + lat_max) / 2
        center_lon = (lon_min + lon_max) / 2

        m = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=15,
            tiles="CartoDB dark_matter",
        )

        for j in junctions:
            # Convert SUMO coords to lat/lon using linear interpolation
            frac_x = (j["x"] - cx_min) / max(cx_max - cx_min, 1)
            frac_y = (j["y"] - cy_min) / max(cy_max - cy_min, 1)
            lat = lat_min + frac_y * (lat_max - lat_min)
            lon = lon_min + frac_x * (lon_max - lon_min)

            folium.CircleMarker(
                location=[lat, lon],
                radius=8,
                color="#64ffda",
                fill=True,
                fill_color="#64ffda",
                fill_opacity=0.7,
                popup=folium.Popup(
                    f"<b>🚦 {j['id']}</b><br>Type: Traffic Light<br>Controlled by AI",
                    max_width=200,
                ),
                tooltip=j["id"],
            ).add_to(m)

        st_folium(m, width=None, height=450, returned_objects=[])
    else:
        st.info("Map coordinates not available. Showing simulation network info.")
        st.metric("Traffic Lights", data.get("traffic_lights_count", "N/A"))

except ImportError:
    st.info("Install folium and streamlit-folium for map view: `pip3 install folium streamlit-folium`")
except Exception as e:
    st.warning(f"Map rendering error: {e}")
    st.metric("Traffic Lights", data.get("traffic_lights_count", "N/A"))

st.divider()

# ── Raw Data Explorer ────────────────────────────────────
with st.expander("📋 Raw Simulation Results"):
    st.json(
        {k: v for k, v in data.items() if k != "step_data"},
        expanded=True,
    )

with st.expander("📈 Step-by-Step Data Table"):
    if step_data:
        st.dataframe(
            pd.DataFrame(step_data),
            use_container_width=True,
            height=400,
        )

# ── Footer ───────────────────────────────────────────────
st.markdown("---")
st.markdown(
    '<div style="text-align:center; color:#a8b2d1; font-size:0.85rem;">'
    '🚦 TrafficFlow AI GreenWave  •  Smart Adaptive Traffic Signal Control  •  '
    'Powered by SUMO + YOLOv8 + Streamlit'
    '</div>',
    unsafe_allow_html=True,
)
