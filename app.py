# app.py
# FINAL – Nigeria Mobile Network Coverage, Density & Site Selection Web App
# Error-safe version with automatic column normalization

import streamlit as st
import pandas as pd
import numpy as np
from sklearn.neighbors import BallTree
import folium
from streamlit_folium import st_folium

# ---------------- PAGE CONFIG ----------------
st.set_page_config(
    page_title="Nigeria Network Coverage & Planning App",
    page_icon="📡",
    layout="wide"
)

# ---------------- LOAD DATA ----------------
@st.cache_data
def load_data():
    df = pd.read_csv("Nigeria_2G_3G_4G_All_Operators_ArcGIS.csv")

    # Normalize column names (VERY IMPORTANT)
    df.columns = df.columns.str.strip().str.replace(" ", "_").str.lower()
    return df

df = load_data()

# ---------------- REQUIRED COLUMNS CHECK ----------------
required_cols = ["latitude", "longitude", "network_provider", "technology"]
for col in required_cols:
    if col not in df.columns:
        st.error(f"Missing required column: {col}")
        st.stop()

# ---------------- SPATIAL INDEX ----------------
coords_rad = np.radians(df[["latitude", "longitude"]])
tree = BallTree(coords_rad, metric="haversine")

# ---------------- SIDEBAR CONTROLS ----------------
st.sidebar.title("📍 Analysis Controls")

lat = st.sidebar.number_input("Latitude", value=6.5244, format="%.6f")
lon = st.sidebar.number_input("Longitude", value=3.3792, format="%.6f")

k = st.sidebar.slider("Nearby sites to analyze", 1, 25, 5)
buffer_km = st.sidebar.slider("Coverage buffer (km)", 1, 20, 5)

show_density_grid = st.sidebar.checkbox("Show coverage grid", True)
show_site_selection = st.sidebar.checkbox("Show site selection insight", True)
show_state_density = st.sidebar.checkbox("Show coverage density per state")

predict_btn = st.sidebar.button("📡 Predict Network Coverage")

# ---------------- USER GUIDE ----------------
with st.expander("📘 User Guide"):
    st.markdown(
        """
        *How to use this app*
        1. Enter coordinates OR click on the map
        2. Adjust number of nearby sites
        3. Adjust coverage buffer
        4. Click Predict Network Coverage
        5. Green = covered | Red = no coverage
        """
    )

# ---------------- MAIN TITLE ----------------
st.title("📡 Nigeria Mobile Network Coverage & Planning System")

# ---------------- MAP INITIALIZATION ----------------
base_map = folium.Map(location=[lat, lon], zoom_start=6, tiles="CartoDB positron")

click_data = st_folium(base_map, height=350, width=1100)

if click_data and click_data.get("last_clicked"):
    lat = click_data["last_clicked"]["lat"]
    lon = click_data["last_clicked"]["lng"]

# ---------------- ANALYSIS ----------------
if predict_btn:

    # Nearest sites
    point = np.radians([[lat, lon]])
    dist, idx = tree.query(point, k=k)
    nearby = df.iloc[idx[0]].copy()

    # User marker
    folium.Marker(
        [lat, lon],
        popup="Analysis Location",
        icon=folium.Icon(color="blue", icon="signal")
    ).add_to(base_map)

    # Operator colors
    operator_colors = {
        "mtn": "orange",
        "airtel": "red",
        "glo": "green",
        "9mobile": "darkgreen"
    }

    # ---------------- BUFFERS & SITES ----------------
    for _, row in nearby.iterrows():
        provider = str(row["network_provider"]).lower()
        color = operator_colors.get(provider, "gray")

        folium.Marker(
            [row["latitude"], row["longitude"]],
            popup=f"{row['network_provider']} | {row['technology']}",
            icon=folium.Icon(color=color)
        ).add_to(base_map)

        folium.Circle(
            [row["latitude"], row["longitude"]],
            radius=buffer_km * 1000,
            color=color,
            fill=True,
            fill_opacity=0.25
        ).add_to(base_map)

    # ---------------- GRID-BASED …