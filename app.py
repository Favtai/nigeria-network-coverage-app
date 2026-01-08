import os
import json
import math
import streamlit as st
import pandas as pd
import folium
from geopy.distance import geodesic
from streamlit_folium import st_folium

# -------------------------------------------------
# PAGE CONFIG
# -------------------------------------------------
st.set_page_config(
    page_title="Nigeria Network Coverage Dashboard",
    layout="wide"
)

st.title("📡 Nigeria Network Coverage, Gaps & Planning Dashboard")

# -------------------------------------------------
# SESSION STATE
# -------------------------------------------------
if "analyzed" not in st.session_state:
    st.session_state.analyzed = False

# -------------------------------------------------
# FILE FINDER (VERY IMPORTANT FOR STREAMLIT CLOUD)
# -------------------------------------------------
def find_file(filename):
    for root, dirs, files in os.walk("."):
        if filename in files:
            return os.path.join(root, filename)
    return None

# -------------------------------------------------
# LOAD DATA
# -------------------------------------------------
@st.cache_data
def load_network_data():
    path = find_file("Nigeria_2G_3G_4G_All_Operators_ArcGIS.csv")
    if not path:
        st.error("❌ Network CSV not found")
        st.stop()
    return pd.read_csv(path)

@st.cache_data
def load_geojson(name):
    path = find_file(name)
    if not path:
        st.error(f"❌ {name} not found")
        st.stop()
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

df = load_network_data()

nigeria_geo = load_geojson("gadm41_NGA_0.geojson")
states_geo = load_geojson("gadm41_NGA_1.geojson")

# -------------------------------------------------
# REQUIRED CSV COLUMNS (LOCKED)
# -------------------------------------------------
LAT = "Latitude"
LON = "Longitude"
OPERATOR = "Network_Operator"
GEN = "Network_Generation"

# -------------------------------------------------
# SIDEBAR INPUT
# -------------------------------------------------
st.sidebar.header("📍 Location Input")

lat = st.sidebar.number_input("Latitude", value=6.5244, format="%.6f")
lon = st.sidebar.number_input("Longitude", value=3.3792, format="%.6f")

radius_km = st.sidebar.slider("Buffer Radius (km)", 5, 200, 30)

no_limit = st.sidebar.checkbox("No distance limit (show all networks)", False)

if st.sidebar.button("🔍 Analyze Location"):
    st.session_state.analyzed = True
    st.session_state.lat = lat
    st.session_state.lon = lon
    st.session_state.radius = radius_km
    st.session_state.no_limit = no_limit

# -------------------------------------------------
# TABS (ALL REQUIRED)
# -------------------------------------------------
tabs = st.tabs([
    "🗺 Coverage Map",
    "🚫 No Coverage Map",
    "📊 Network Results",
    "🔮 Network Predictor",
    "⚠ Coverage Gaps Analyzer",
    "🏗 New Tower Recommendation",
    "📈 Coverage Density (State)",
    "🏢 Operator Summary",
    "📡 Technology Summary",
    "⭕ Buffer View",
    "📥 Export Results",
    "📘 User Guide"
])

# -------------------------------------------------
# RUN ANALYSIS
# -------------------------------------------------
if st.session_state.analyzed:

    lat0 = st.session_state.lat
    lon0 = st.session_state.lon
    radius = st.session_state.radius

    df["distance_km"] = df.apply(
        lambda r: geodesic((lat0, lon0), (r[LAT], r[LON])).km,
        axis=1
    )

    if st.session_state.no_limit:
        nearby = df.copy()
    else:
        nearby = df[df["distance_km"] <= radius].copy()

    # Confidence
    nearby["Confidence"] = nearby["distance_km"].apply(
        lambda d: "High" if d <= 5 else "Medium" if d <= 20 else "Low"
    )

    # -------------------------------------------------
    # TAB 1: COVERAGE MAP
    # -------------------------------------------------
    with tabs[0]:
        m = folium.Map(location=[lat0, lon0], zoom_start=7)

        folium.GeoJson(nigeria_geo, name="Nigeria").add_to(m)
        folium.GeoJson(states_geo, name="States").add_to(m)

        folium.Marker(
            [lat0, lon0],
            icon=folium.Icon(color="red"),
            popup="Input Location"
        ).add_to(m)

        folium.Circle(
            [lat0, lon0],
            radius=radius * 1000,
            color="blue",
            fill=True,
            fill_opacity=0.1
        ).add_to(m)

        for _, r in nearby.iterrows():
            folium.CircleMarker(
                [r[LAT], r[LON]],
                radius=4,
                popup=f"""
                Operator: {r[OPERATOR]}<br>
                Generation: {r[GEN]}<br>
                Distance: {r['distance_km']:.2f} km<br>
                Confidence: {r['Confidence']}
                """
            ).add_to(m)

        st_folium(m, height=650, use_container_width=True)

    # -------------------------------------------------
    # TAB 2: NO COVERAGE MAP
    # -------------------------------------------------
    with tabs[1]:
        if nearby.empty:
            st.success("✅ This area has NO network coverage")
        else:
            st.warning("⚠ Some coverage exists near this location")

    # -------------------------------------------------
    # TAB 3: RESULTS TABLE
    # -------------------------------------------------
    with tabs[2]:
        st.dataframe(
            nearby[[OPERATOR, GEN, "distance_km", "Confidence"]]
            .sort_values("distance_km"),
            use_container_width=True
        )

    # -------------------------------------------------
    # TAB 4: NETWORK PREDICTOR
    # -------------------------------------------------
    with tabs[3]:
        if nearby.empty:
            st.error("❌ No network detected at this location")
        else:
            st.success(f"✅ {nearby[OPERATOR].nunique()} operators detected")

    # -------------------------------------------------
    # TAB 5: COVERAGE GAPS ANALYZER
    # -------------------------------------------------
    with tabs[4]:
        gap_status = "No Coverage" if nearby.empty else "Partial Coverage"
        st.metric("Coverage Status", gap_status)
        st.metric("Nearest Network (km)", None if nearby.empty else nearby["distance_km"].min())

    # -------------------------------------------------
    # TAB 6: NEW TOWER RECOMMENDATION
    # -------------------------------------------------
    with tabs[5]:
        if nearby.empty:
            st.success("📍 Strong candidate for NEW TOWER deployment")
            st.write(f"Recommended Location: {lat0}, {lon0}")
        else:
            st.info("📶 Improve capacity or densify existing sites")

    # -------------------------------------------------
    # TAB 7: COVERAGE DENSITY
    # -------------------------------------------------
    with tabs[6]:
        st.write("📍 State density requires state column in CSV")

    # -------------------------------------------------
    # TAB 8: OPERATOR SUMMARY
    # -------------------------------------------------
    with tabs[7]:
        st.bar_chart(nearby[OPERATOR].value_counts())

    # -------------------------------------------------
    # TAB 9: TECHNOLOGY SUMMARY
    # -------------------------------------------------
    with tabs[8]:
        st.bar_chart(nearby[GEN].value_counts())

    # -------------------------------------------------
    # TAB 10: BUFFER VIEW
    # -------------------------------------------------
    with tabs[9]:
        st.write(f"⭕ Buffer Radius: {radius} km")

    # -------------------------------------------------
    # TAB 11: EXPORT
    # -------------------------------------------------
    with tabs[10]:
        st.download_button(
            "⬇ Export Network Results",
            nearby.to_csv(index=False),
            "network_results.csv",
            "text/csv"
        )

    # -------------------------------------------------
    # TAB 12: USER GUIDE
    # -------------------------------------------------
    with tabs[11]:
        st.markdown("""
        *How to use this app*
        1. Enter Latitude & Longitude
        2. Choose buffer radius or no limit
        3. Click Analyze
        4. View results across all tabs
        """)

else:
    st.info("👈 Enter coordinates and click *Analyze Location*")
