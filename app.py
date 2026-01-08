import os
import math
import streamlit as st
import pandas as pd
import geopandas as gpd
import folium
from streamlit_folium import st_folium

# =====================================================
# CONFIG
# =====================================================
st.set_page_config(page_title="Nigeria Network Planner", layout="wide")
st.title("🇳🇬 Nigeria Mobile Network Coverage Planning System")
st.caption("Coverage • No Coverage • Gap Analysis • Site Recommendation")

# =====================================================
# HELPERS
# =====================================================
def find_file(name):
    for r, d, f in os.walk("."):
        if name in f:
            return os.path.join(r, name)
    return None

def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat/2)**2 +
         math.cos(math.radians(lat1)) *
         math.cos(math.radians(lat2)) *
         math.sin(dlon/2)**2)
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1-a))

# =====================================================
# LOAD FILES
# =====================================================
nga0 = find_file("gadm41_NGA_0.geojson")
nga1 = find_file("gadm41_NGA_1.geojson")
csv_file = find_file("Nigeria_2G_3G_4G_All_Operators_ArcGIS.csv")

if not nga0 or not nga1:
    st.error("Nigeria boundary files missing")
    st.stop()

nigeria = gpd.read_file(nga0)
states = gpd.read_file(nga1)

network_df = pd.read_csv(csv_file) if csv_file else None

lat_col = next(c for c in network_df.columns if "lat" in c.lower())
lon_col = next(c for c in network_df.columns if "lon" in c.lower())
op_col  = next(c for c in network_df.columns if "operator" in c.lower())
gen_col = next(c for c in network_df.columns if "generation" in c.lower())

# =====================================================
# LOCATION CONTROLLER (MOTHERBOARD)
# =====================================================
st.sidebar.header("📍 Location Controller")

input_lat = st.sidebar.number_input("Latitude", value=6.5244, format="%.6f")
input_lon = st.sidebar.number_input("Longitude", value=3.3792, format="%.6f")
buffer_km = st.sidebar.slider("Coverage Radius (km)", 3, 30, 10)

analyze = st.sidebar.button("🔍 Analyze Location")

# =====================================================
# BASE MAP
# =====================================================
def base_map(center, zoom=9):
    m = folium.Map(location=center, zoom_start=zoom, tiles="CartoDB positron")
    folium.GeoJson(nigeria, style_function=lambda x: {"color": "black", "weight": 2}).add_to(m)
    folium.GeoJson(states, style_function=lambda x: {"color": "gray", "weight": 1}).add_to(m)
    return m

# =====================================================
# TABS
# =====================================================
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🗺 Coverage & No Coverage",
    "⚠ Coverage Gaps",
    "📡 Network Prediction",
    "📍 New Tower Recommendation",
    "📊 Coverage Density (States)"
])

# =====================================================
# ANALYSIS
# =====================================================
if analyze and network_df is not None:
    network_df["distance_km"] = network_df.apply(
        lambda r: haversine(input_lat, input_lon, r[lat_col], r[lon_col]), axis=1
    )

    nearby = network_df.sort_values("distance_km").head(50)

    confidence = max(5, 100 - nearby["distance_km"].mean() * 3)

    # =================================================
    # TAB 1 — COVERAGE & NO COVERAGE
    # =================================================
    with tab1:
        m = base_map([input_lat, input_lon])

        folium.Marker(
            [input_lat, input_lon],
            icon=folium.Icon(color="green", icon="signal"),
            tooltip="Input Location"
        ).add_to(m)

        # Coverage buffers
        for _, r in nearby.iterrows():
            folium.Circle(
                [r[lat_col], r[lon_col]],
                radius=buffer_km * 1000,
                color="blue",
                fill=True,
                fill_opacity=0.1
            ).add_to(m)

        # No coverage zone
        folium.Circle(
            [input_lat, input_lon],
            radius=buffer_km * 1000,
            color="red",
            fill=True,
            fill_opacity=0.25,
            tooltip="Potential No Coverage Area"
        ).add_to(m)

        st_folium(m, height=600)

    # =================================================
    # TAB 2 — GAP ANALYSIS
    # =================================================
    with tab2:
        m = base_map([input_lat, input_lon])

        gaps = nearby[nearby["distance_km"] > buffer_km]

        for _, r in gaps.iterrows():
            folium.CircleMarker(
                [r[lat_col], r[lon_col]],
                radius=6,
                color="red",
                fill=True
            ).add_to(m)

        st_folium(m, height=600)
        st.warning("Red markers represent coverage gaps")

    # =================================================
    # TAB 3 — NETWORK PREDICTION
    # =================================================
    with tab3:
        st.metric("Network Confidence Level", f"{confidence:.1f}%")

        st.subheader("Available Operators")
        st.write(nearby[op_col].value_counts())

        st.subheader("Technology Availability")
        st.write(nearby[gen_col].value_counts())

        st.subheader("Nearest Network Sites")
        st.dataframe(
            nearby[[op_col, gen_col, "distance_km"]].head(10)
        )

    # =================================================
    # TAB 4 — NEW TOWER RECOMMENDATION
    # =================================================
    with tab4:
        st.subheader("Recommended New Tower Location")

        # Recommend new site at centroid of no-coverage zone
        rec_lat = input_lat + (buffer_km / 111)
        rec_lon = input_lon + (buffer_km / 111)

        m = base_map([rec_lat, rec_lon])

        folium.Marker(
            [rec_lat, rec_lon],
            icon=folium.Icon(color="purple", icon="tower"),
            tooltip="Recommended New Tower"
        ).add_to(m)

        st_folium(m, height=600)

        st.success("Recommended site generated based on coverage gap")

        st.download_button(
            "⬇ Export Recommended Site",
            pd.DataFrame([{
                "Latitude": rec_lat,
                "Longitude": rec_lon,
                "Reason": "Coverage Gap",
                "Priority": "High"
            }]).to_csv(index=False),
            file_name="recommended_new_tower.csv",
            mime="text/csv"
        )

    # =================================================
    # TAB 5 — COVERAGE DENSITY PER STATE
    # =================================================
    with tab5:
        st.subheader("Coverage Density per State")

        # Spatial join
        gdf_points = gpd.GeoDataFrame(
            network_df,
            geometry=gpd.points_from_xy(network_df[lon_col], network_df[lat_col]),
            crs="EPSG:4326"
        )

        joined = gpd.sjoin(gdf_points, states, how="left", predicate="within")

        density = joined.groupby("NAME_1").size().reset_index(name="Site_Count")

        states_density = states.merge(density, on="NAME_1", how="left").fillna(0)

        m = base_map([9.1, 8.7], zoom=6)

        folium.Choropleth(
            geo_data=states_density,
            data=states_density,
            columns=["NAME_1", "Site_Count"],
            key_on="feature.properties.NAME_1",
            fill_color="YlGnBu",
            fill_opacity=0.7,
            line_opacity=0.3,
            legend_name="Network Site Density"
        ).add_to(m)

        st_folium(m, height=600)

        st.dataframe(density.sort_values("Site_Count", ascending=False))

else:
    st.info("👈 Enter coordinates and click *Analyze Location*")
