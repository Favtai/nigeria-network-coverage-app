import streamlit as st
import pandas as pd
import numpy as np
import folium
import json
from streamlit_folium import st_folium
from math import sin, cos, radians

# ================= PAGE =================
st.set_page_config(page_title="Nigeria Network Coverage", layout="wide")
st.title("📡 Nigeria Network Coverage & Planning Dashboard")

# ================= SESSION =================
if "analyzed" not in st.session_state:
    st.session_state.analyzed = False

# ================= LOAD DATA =================
@st.cache_data
def load_network():
    df = pd.read_csv("Nigeria_2G_3G_4G_All_Operators_ArcGIS.csv")
    df.columns = df.columns.str.lower()
    return df

@st.cache_data
def load_geojson(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

df = load_network()
nga_boundary = load_geojson("gadm41_NGA_0.geojson")
nga_states = load_geojson("gadm41_NGA_1.geojson")

lat_col = "latitude"
lon_col = "longitude"
operator_col = "network_operator"
tech_col = "network_generation"
state_col = "state" if "state" in df.columns else None

# ================= DISTANCE =================
def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    lat1, lon1, lat2, lon2 = map(np.radians,[lat1,lon1,lat2,lon2])
    dlat = lat2-lat1
    dlon = lon2-lon1
    a = np.sin(dlat/2)*2 + np.cos(lat1)*np.cos(lat2)*np.sin(dlon/2)*2
    return 2*R*np.arcsin(np.sqrt(a))

# ================= SIDEBAR =================
st.sidebar.header("📍 Location Input")
lat0 = st.sidebar.number_input("Latitude", 6.5244, format="%.6f")
lon0 = st.sidebar.number_input("Longitude", 3.3792, format="%.6f")
radius = st.sidebar.slider("Analysis Radius (km)", 5, 200, 30)
no_limit = st.sidebar.checkbox("🔓 No Distance Limit")

if st.sidebar.button("🔍 Run Analysis"):
    st.session_state.analyzed = True
    st.session_state.lat0 = lat0
    st.session_state.lon0 = lon0
    st.session_state.radius = radius
    st.session_state.no_limit = no_limit

# ================= TABS =================
tabs = st.tabs([
    "🗺 Coverage Map",
    "🚫 No Coverage Map",
    "📊 Network Results",
    "🧠 Network Predictor",
    "🚨 Coverage Gaps",
    "🏗 New Tower Recommendation",
    "📥 Export Results",
    "📘 User Guide",
    "⭕ Buffer View",
    "📦 Operator Summary",
    "📡 Technology Summary",
    "🏙 Coverage Density per State"
])

# ================= ANALYSIS =================
if st.session_state.analyzed:
    lat0 = st.session_state.lat0
    lon0 = st.session_state.lon0

    df["distance_km"] = haversine(lat0, lon0, df[lat_col], df[lon_col])
    nearest_distance = df["distance_km"].min()

    if st.session_state.no_limit:
        nearby = df.copy()
    else:
        nearby = df[df["distance_km"] <= st.session_state.radius].copy()

    # ================= TAB 1: COVERAGE MAP =================
    with tabs[0]:
        m = folium.Map([lat0, lon0], zoom_start=6)

        folium.GeoJson(nga_boundary, name="Nigeria").add_to(m)
        folium.GeoJson(
            nga_states,
            style_function=lambda x: {
                "fillColor": "transparent",
                "color": "black",
                "weight": 0.7
            }
        ).add_to(m)

        folium.Marker([lat0, lon0], icon=folium.Icon(color="red")).add_to(m)
        folium.Circle([lat0, lon0], radius=radius*1000, fill=True, fill_opacity=0.1).add_to(m)

        for _, r in nearby.iterrows():
            folium.CircleMarker(
                [r[lat_col], r[lon_col]],
                radius=4,
                popup=f"{r[operator_col]} | {r[tech_col]} | {r.distance_km:.1f} km"
            ).add_to(m)

        st_folium(m, height=550)

    # ================= TAB 2: NO COVERAGE MAP =================
    with tabs[1]:
        m2 = folium.Map([lat0, lon0], zoom_start=6)
        folium.GeoJson(nga_boundary).add_to(m2)
        folium.GeoJson(nga_states).add_to(m2)

        folium.Marker([lat0, lon0], icon=folium.Icon(color="red")).add_to(m2)

        if nearby.empty:
            folium.Circle(
                [lat0, lon0],
                radius=radius*1000,
                color="red",
                fill=True,
                fill_opacity=0.3
            ).add_to(m2)
            st.error("❌ NO NETWORK COVERAGE")
            st.write(f"Nearest Network: *{nearest_distance:.2f} km*")

        st_folium(m2, height=550)

    # ================= TAB 12: STATE DENSITY =================
    with tabs[11]:
        if state_col:
            density = df.groupby(state_col).size()
            st.bar_chart(density)
        else:
            st.warning("State column not available")

else:
    st.info("👈 Enter coordinates and click Run Analysis")
