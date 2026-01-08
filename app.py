import streamlit as st
import pandas as pd
import folium
import json
from geopy.distance import geodesic
from streamlit_folium import st_folium

# =========================================================
# PAGE CONFIG
# =========================================================
st.set_page_config(
    page_title="Nigeria Network Coverage & Planning",
    layout="wide"
)

st.title("📡 Nigeria Network Coverage & Planning Dashboard")
st.caption("All results remain visible until new coordinates are analyzed")

# =========================================================
# SESSION STATE
# =========================================================
if "run" not in st.session_state:
    st.session_state.run = False

# =========================================================
# LOAD DATA
# =========================================================
@st.cache_data
def load_network_data():
    return pd.read_csv("Nigeria_2G_3G_4G_All_Operators_ArcGIS.csv")

@st.cache_data
def load_geojson(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

try:
    df = load_network_data()
except:
    st.error("❌ Nigeria_2G_3G_4G_All_Operators_ArcGIS.csv not found")
    st.stop()

try:
    nigeria_geo = load_geojson("gadm41_NGA_0.geojson")
    states_geo = load_geojson("gadm41_NGA_1.geojson")
except:
    st.error("❌ Nigeria GeoJSON files not found")
    st.stop()

# =========================================================
# COLUMN NAMES (EXACT)
# =========================================================
LAT = "Latitude"
LON = "Longitude"
OP = "Network_Operator"
GEN = "Network_Generation"

# =========================================================
# COLOR CODING
# =========================================================
OP_COLORS = {
    "MTN": "yellow",
    "Airtel": "red",
    "Glo": "green",
    "9mobile": "darkgreen"
}

GEN_COLORS = {
    "2G": "gray",
    "3G": "orange",
    "4G": "blue"
}

# =========================================================
# CONFIDENCE LOGIC
# =========================================================
def confidence_level(d):
    if d <= 5:
        return "High"
    elif d <= 15:
        return "Medium"
    else:
        return "Low"

# =========================================================
# SIDEBAR INPUT
# =========================================================
st.sidebar.header("📍 Location Input")

lat = st.sidebar.number_input("Latitude", value=6.5244, format="%.6f")
lon = st.sidebar.number_input("Longitude", value=3.3792, format="%.6f")
radius = st.sidebar.slider("Analysis Radius (km)", 5, 300, 20)
no_limit = st.sidebar.checkbox("No distance limit")

if st.sidebar.button("🔍 Analyze"):
    st.session_state.run = True
    st.session_state.lat = lat
    st.session_state.lon = lon
    st.session_state.radius = radius
    st.session_state.no_limit = no_limit

# =========================================================
# MAIN ANALYSIS
# =========================================================
if st.session_state.run:

    lat0 = st.session_state.lat
    lon0 = st.session_state.lon

    df["distance_km"] = df.apply(
        lambda r: geodesic((lat0, lon0), (r[LAT], r[LON])).km,
        axis=1
    )

    if st.session_state.no_limit:
        nearby = df.copy()
    else:
        nearby = df[df["distance_km"] <= st.session_state.radius].copy()

    nearby["Confidence"] = nearby["distance_km"].apply(confidence_level)

    # =====================================================
    st.header("🗺 Coverage Map")

    m = folium.Map(
        location=[lat0, lon0],
        zoom_start=10,
        tiles="cartodbpositron"
    )

    folium.GeoJson(
        nigeria_geo,
        name="Nigeria Boundary",
        style_function=lambda x: {"fillColor": "none", "color": "black", "weight": 2}
    ).add_to(m)

    folium.GeoJson(
        states_geo,
        name="State Boundaries",
        style_function=lambda x: {"fillColor": "none", "color": "#666", "weight": 1}
    ).add_to(m)

    folium.Marker(
        [lat0, lon0],
        popup="Input Location",
        icon=folium.Icon(color="red")
    ).add_to(m)

    folium.Circle(
        [lat0, lon0],
        radius=radius * 1000,
        color="blue",
        fill=True,
        fill_opacity=0.1
    ).add_to(m)

    for _, r in nearby.iterrows():
        color = OP_COLORS.get(r[OP], "blue")
        folium.CircleMarker(
            [r[LAT], r[LON]],
            radius=4,
            color=color,
            fill=True,
            popup=f"""
            Operator: {r[OP]}<br>
            Generation: {r[GEN]}<br>
            Distance: {r['distance_km']:.2f} km<br>
            Confidence: {r['Confidence']}
            """
        ).add_to(m)

    folium.LayerControl().add_to(m)
    st_folium(m, height=650, use_container_width=True)

    # =====================================================
    st.header("📡 Network Predictor")

    if nearby.empty:
        st.error("❌ No network detected at this location")
    else:
        predictor = nearby[[OP, GEN, "distance_km", "Confidence"]].sort_values("distance_km")
        st.dataframe(predictor, use_container_width=True)

        best = predictor.iloc[0]
        st.success(
            f"Best Network: {best[OP]} ({best[GEN]}) – {best['Confidence']} confidence"
        )

    # =====================================================
    st.header("⚠ Coverage Gap Analyzer")

    nearest_dist = df["distance_km"].min()
    gap_status = "No Coverage" if nearby.empty else "Partial Coverage"

    gap_df = pd.DataFrame([{
        "Latitude": lat0,
        "Longitude": lon0,
        "Coverage_Status": gap_status,
        "Nearest_Network_Distance_km": nearest_dist,
        "Detected_Sites": len(nearby)
    }])

    st.dataframe(gap_df, use_container_width=True)

    # =====================================================
    st.header("🏗 New Tower Recommendation")

    st.markdown(f"""
    *Recommended Latitude:* {lat0}  
    *Recommended Longitude:* {lon0}  
    *Reason:* { "No existing coverage" if nearby.empty else "Coverage improvement needed" }
    """)

    rec_df = pd.DataFrame([{
        "Recommended_Latitude": lat0,
        "Recommended_Longitude": lon0,
        "Reason": "No Coverage" if nearby.empty else "Weak Coverage"
    }])

    # =====================================================
    st.header("📊 Coverage Density per State")

    if "State" in df.columns:
        density = (
            df.groupby("State")
            .size()
            .reset_index(name="Network_Sites")
            .sort_values("Network_Sites", ascending=False)
        )
        st.dataframe(density, use_container_width=True)
        st.bar_chart(density.set_index("State"))
    else:
        st.info("State column not available in CSV")

    # =====================================================
    st.header("🏢 Operator Summary")
    st.bar_chart(df[OP].value_counts())

    # =====================================================
    st.header("📶 Technology Summary")
    st.bar_chart(df[GEN].value_counts())

    # =====================================================
    st.header("📤 Export Results")

    st.download_button(
        "⬇ Download Network Results",
        nearby.to_csv(index=False),
        "network_results.csv"
    )

    st.download_button(
        "⬇ Download Coverage Gap",
        gap_df.to_csv(index=False),
        "coverage_gap.csv"
    )

    st.download_button(
        "⬇ Download Recommended Tower",
        rec_df.to_csv(index=False),
        "recommended_tower.csv"
    )

    # =====================================================
    st.header("📖 User Guide")
    st.markdown("""
    *Steps*
    1. Enter Latitude & Longitude
    2. Choose radius or No distance limit
    3. Click Analyze
    4. Scroll to view all results
    5. Export any result as CSV
    """)

else:
    st.info("👈 Enter coordinates and click Analyze")
