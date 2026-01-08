import os
import json
import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium

# ==========================================================
# STREAMLIT CONFIG
# ==========================================================
st.set_page_config(
    page_title="Nigeria Mobile Network Coverage Planning System",
    layout="wide"
)

st.title("📡 Nigeria Mobile Network Coverage Planning System")
st.caption("2G | 3G | 4G • Coverage • Gaps • Site Recommendation")

# ==========================================================
# SAFE WORKING DIRECTORY (NO _file_ USED)
# ==========================================================
BASE_DIR = os.getcwd()

# Debug info (VERY IMPORTANT – helps confirm deployment)
with st.expander("🔍 Debug Info"):
    st.write("Working directory:", BASE_DIR)
    st.write("Files in directory:", os.listdir(BASE_DIR))

# ==========================================================
# LOAD GEOJSON FILES SAFELY
# ==========================================================
nga0_path = os.path.join(BASE_DIR, "gadm41_NGA_0.geojson")
nga1_path = os.path.join(BASE_DIR, "gadm41_NGA_1.geojson")

if not os.path.exists(nga0_path):
    st.error("❌ gadm41_NGA_0.geojson not found in repo root")
    st.stop()

if not os.path.exists(nga1_path):
    st.error("❌ gadm41_NGA_1.geojson not found in repo root")
    st.stop()

with open(nga0_path, "r", encoding="utf-8") as f:
    nigeria_geo = json.load(f)

with open(nga1_path, "r", encoding="utf-8") as f:
    states_geo = json.load(f)

st.success("✅ Nigeria boundary & states loaded successfully")

# ==========================================================
# OPTIONAL NETWORK CSV (APP WILL NOT CRASH IF MISSING)
# ==========================================================
csv_file = "Nigeria_2G_3G_4G_All_Operators.csv"
network_df = None

if os.path.exists(csv_file):
    try:
        network_df = pd.read_csv(csv_file)
        st.success("✅ Network CSV loaded")
    except Exception as e:
        st.warning(f"⚠️ CSV found but failed to load: {e}")
else:
    st.warning("⚠️ Network CSV not found — map will still work")

# ==========================================================
# TABS
# ==========================================================
tab1, tab2, tab3 = st.tabs([
    "🗺️ National Coverage Map",
    "📍 Coverage Buffers",
    "📊 Coverage Density"
])

# ==========================================================
# TAB 1 – NATIONAL MAP
# ==========================================================
with tab1:
    st.subheader("Nigeria National Boundary & States")

    m = folium.Map(location=[9.1, 8.7], zoom_start=6, tiles="cartodbpositron")

    folium.GeoJson(
        nigeria_geo,
        name="Nigeria Boundary",
        style_function=lambda x: {
            "fillColor": "#ffffff",
            "color": "black",
            "weight": 2,
            "fillOpacity": 0.1
        }
    ).add_to(m)

    folium.GeoJson(
        states_geo,
        name="States",
        style_function=lambda x: {
            "fillColor": "#3186cc",
            "color": "gray",
            "weight": 1,
            "fillOpacity": 0.05
        }
    ).add_to(m)

    folium.LayerControl().add_to(m)

    st_folium(m, height=600, use_container_width=True)

# ==========================================================
# TAB 2 – COVERAGE BUFFER (SIMULATED)
# ==========================================================
with tab2:
    st.subheader("Coverage Buffer (Demo)")

    m2 = folium.Map(location=[9.1, 8.7], zoom_start=6, tiles="cartodbpositron")

    # Example site (Abuja)
    site_lat, site_lon = 9.0765, 7.3986

    folium.Circle(
        location=[site_lat, site_lon],
        radius=30000,  # 30km buffer
        color="blue",
        fill=True,
        fill_opacity=0.2,
        popup="Example Coverage Buffer (30km)"
    ).add_to(m2)

    folium.Marker(
        location=[site_lat, site_lon],
        popup="Sample BTS Site",
        icon=folium.Icon(color="red", icon="signal")
    ).add_to(m2)

    st_folium(m2, height=600, use_container_width=True)

# ==========================================================
# TAB 3 – COVERAGE DENSITY (SIMULATED)
# ==========================================================
with tab3:
    st.subheader("Coverage Density by State (Demo View)")
    st.info("This is a placeholder density view. Real density requires population & site data.")

    density_map = folium.Map(location=[9.1, 8.7], zoom_start=6, tiles="cartodbpositron")

    folium.GeoJson(
        states_geo,
        name="Density Layer",
        style_function=lambda x: {
            "fillColor": "#ff7800",
            "color": "black",
            "weight": 0.5,
            "fillOpacity": 0.3
        }
    ).add_to(density_map)

    st_folium(density_map, height=600, use_container_width=True)

# ==========================================================
# FOOTER
# ==========================================================
st.markdown("---")
st.caption("✅ App running safely without _file_ • Streamlit Cloud compatible")
