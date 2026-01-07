# app.py
# Nigeria Mobile Network Coverage & Planning App
# FIXED to match real CSV columns

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

    # Normalize column names
    df.columns = (
        df.columns
        .str.strip()
        .str.lower()
        .str.replace(" ", "_")
    )

    # Explicit mapping from YOUR CSV
    df.rename(columns={
        "network_operator": "network_provider",
        "radio_technology": "technology",
        "latitude": "latitude",
        "longitude": "longitude"
    }, inplace=True)

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

# ---------------- SIDEBAR ----------------
st.sidebar.title("📍 Analysis Controls")

lat = st.sidebar.number_input("Latitude", value=6.5244, format="%.6f")
lon = st.sidebar.number_input("Longitude", value=3.3792, format="%.6f")

k = st.sidebar.slider("Nearby sites to analyze", 1, 30, 5)
buffer_km = st.sidebar.slider("Coverage buffer (km)", 1, 30, 5)

predict_btn = st.sidebar.button("📡 Predict Network Coverage")

# ---------------- MAIN TITLE ----------------
st.title("📡 Nigeria Mobile Network Coverage & Site Planning System")

# ---------------- MAP INIT ----------------
base_map = folium.Map(location=[lat, lon], zoom_start=6, tiles="CartoDB positron")
map_data = st_folium(base_map, height=350, width=1100)

if map_data and map_data.get("last_clicked"):
    lat = map_data["last_clicked"]["lat"]
    lon = map_data["last_clicked"]["lng"]

# ---------------- ANALYSIS ----------------
if predict_btn:
    point = np.radians([[lat, lon]])
    dist, idx = tree.query(point, k=k)
    nearby = df.iloc[idx[0]].copy()

    # User location
    folium.Marker(
        [lat, lon],
        popup="Your Location",
        icon=folium.Icon(color="blue", icon="signal")
    ).add_to(base_map)

    operator_colors = {
        "mtn": "orange",
        "airtel": "red",
        "glo": "green",
        "9mobile": "darkgreen"
    }

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

# ---------------- FINAL MAP ----------------
st_folium(base_map, height=550, width=1100)