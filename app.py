import streamlit as st
import pandas as pd
import numpy as np
import folium
from geopy.distance import geodesic

# ---------------- PAGE CONFIG ----------------
st.set_page_config(
    page_title="Nigeria Network Coverage & Planning",
    layout="wide"
)

st.title("📡 Nigeria Network Coverage & Planning Dashboard")

# ---------------- SESSION STATE ----------------
if "run" not in st.session_state:
    st.session_state.run = False

# ---------------- LOAD DATA ----------------
@st.cache_data
def load_data():
    return pd.read_csv("Nigeria_2G_3G_4G_All_Operators_ArcGIS.csv")

try:
    df = load_data()
except Exception as e:
    st.error("❌ Network CSV not found or failed to load.")
    st.stop()

# Normalize column names
df.columns = df.columns.str.lower()

# Auto-detect columns
lat_col = [c for c in df.columns if "lat" in c][0]
lon_col = [c for c in df.columns if "lon" in c][0]
operator_col = [c for c in df.columns if "operator" in c][0]
tech_col = [c for c in df.columns if "gen" in c or "tech" in c][0]

# Optional state column
state_col = None
for c in df.columns:
    if c in ["state", "admin1", "region"]:
        state_col = c
        break

# ---------------- SIDEBAR INPUT ----------------
st.sidebar.header("📍 Location Input")

lat = st.sidebar.number_input("Latitude", value=6.5244, format="%.6f")
lon = st.sidebar.number_input("Longitude", value=3.3792, format="%.6f")

radius_mode = st.sidebar.radio(
    "Distance Mode",
    ["No Distance Limit", "Limit by Radius"]
)

radius_km = None
if radius_mode == "Limit by Radius":
    radius_km = st.sidebar.slider("Analysis Radius (km)", 5, 200, 30)

if st.sidebar.button("🔍 Run Analysis"):
    st.session_state.run = True
    st.session_state.lat = lat
    st.session_state.lon = lon
    st.session_state.radius = radius_km
    st.session_state.mode = radius_mode

# ---------------- TABS (9 TOTAL) ----------------
tabs = st.tabs([
    "🗺 Coverage Map",
    "📊 Network Results",
    "📡 Operator Summary",
    "🎯 Buffer Visualization",
    "🚫 Coverage Gaps",
    "🏗 New Tower Recommendation",
    "🏙 State Coverage Density",
    "📥 Export Results",
    "📘 User Guide"
])

# ---------------- ANALYSIS ----------------
if st.session_state.run:

    lat0 = st.session_state.lat
    lon0 = st.session_state.lon
    radius_km = st.session_state.radius
    mode = st.session_state.mode

    df["distance_km"] = df.apply(
        lambda r: geodesic((lat0, lon0), (r[lat_col], r[lon_col])).km,
        axis=1
    )

    if mode == "Limit by Radius":
        nearby = df[df["distance_km"] <= radius_km].copy()
    else:
        nearby = df.copy()

    nearby["confidence"] = nearby["distance_km"].apply(
        lambda d: "High" if d <= 5 else "Medium" if d <= 20 else "Low"
    )

    # ---------------- TAB 1: COVERAGE MAP ----------------
    with tabs[0]:
        m = folium.Map(location=[lat0, lon0], zoom_start=9)

        folium.Marker(
            [lat0, lon0],
            popup="Input Location",
            icon=folium.Icon(color="red", icon="info-sign")
        ).add_to(m)

        if radius_km:
            folium.Circle(
                [lat0, lon0],
                radius=radius_km * 1000,
                color="blue",
                fill=True,
                fill_opacity=0.1
            ).add_to(m)

        color_map = {
            "mtn": "yellow",
            "airtel": "red",
            "glo": "green",
            "9mobile": "blue"
        }

        for _, r in nearby.iterrows():
            op = str(r[operator_col]).lower()
            color = color_map.get(op, "gray")

            folium.CircleMarker(
                [r[lat_col], r[lon_col]],
                radius=4,
                color=color,
                fill=True,
                fill_opacity=0.7,
                popup=f"""
                Operator: {r[operator_col]}<br>
                Technology: {r[tech_col]}<br>
                Distance: {r['distance_km']:.2f} km<br>
                Confidence: {r['confidence']}
                """
            ).add_to(m)

        st.components.v1.html(m.repr_html(), height=600)

    # ---------------- TAB 2: NETWORK RESULTS ----------------
    with tabs[1]:
        st.dataframe(
            nearby[[operator_col, tech_col, "distance_km", "confidence"]]
            .sort_values("distance_km")
        )

    # ---------------- TAB 3: OPERATOR SUMMARY ----------------
    with tabs[2]:
        summary = nearby.groupby(operator_col).size().reset_index(name="site_count")
        st.dataframe(summary)
        st.bar_chart(summary.set_index(operator_col))

    # ---------------- TAB 4: BUFFER VISUALIZATION ----------------
    with tabs[3]:
        st.markdown("### 📡 Network Buffer Around Location")
        st.write(f"Total sites found: *{len(nearby)}*")
        st.dataframe(
            nearby[[operator_col, tech_col, "distance_km"]]
            .sort_values("distance_km")
            .head(20)
        )

    # ---------------- TAB 5: COVERAGE GAPS ----------------
    with tabs[4]:
        if nearby.empty:
            gap_status = "No Coverage"
            recommendation = "Deploy new site"
        else:
            gap_status = "Partial Coverage"
            recommendation = "Coverage improvement needed"

        gap_df = pd.DataFrame([{
            "latitude": lat0,
            "longitude": lon0,
            "coverage_status": gap_status,
            "network_sites_found": len(nearby),
            "recommendation": recommendation
        }])

        st.dataframe(gap_df)

    # ---------------- TAB 6: NEW TOWER RECOMMENDATION ----------------
    with tabs[5]:
        rec_lat = lat0 + 0.02
        rec_lon = lon0 + 0.02

        rec_df = pd.DataFrame([{
            "recommended_latitude": rec_lat,
            "recommended_longitude": rec_lon,
            "reason": "Coverage gap / weak density"
        }])

        st.dataframe(rec_df)

    # ---------------- TAB 7: STATE COVERAGE DENSITY ----------------
    with tabs[6]:
        if state_col:
            density = df.groupby(state_col).size().reset_index(name="site_count")
            st.dataframe(density.sort_values("site_count", ascending=False))
            st.bar_chart(density.set_index(state_col))
        else:
            st.warning("State column not available in dataset.")

    # ---------------- TAB 8: EXPORT ----------------
    with tabs[7]:
        st.download_button(
            "⬇ Export Network Results",
            nearby.to_csv(index=False),
            "network_results.csv",
            "text/csv"
        )

        st.download_button(
            "⬇ Export Coverage Gap",
            gap_df.to_csv(index=False),
            "coverage_gap.csv",
            "text/csv"
        )

    # ---------------- TAB 9: USER GUIDE ----------------
    with tabs[8]:
        st.markdown("""
        ### 📘 How to Use This App
        1. Enter latitude & longitude
        2. Choose distance mode
        3. Click *Run Analysis*
        4. View maps, gaps & recommendations
        5. Export results as CSV
        """)

else:
    st.info("👈 Enter coordinates and click *Run Analysis* to begin.")
