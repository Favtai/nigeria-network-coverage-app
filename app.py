import streamlit as st
import pandas as pd
import numpy as np
import pydeck as pdk
from math import radians, cos, sin

# ===============================
# CONFIG
# ===============================
st.set_page_config(
    page_title="Nigeria Network Coverage & Planning",
    layout="wide"
)

st.title("📡 Nigeria Network Coverage, Gap Analysis & 5G Planning Dashboard")

# ===============================
# LOAD DATA (SAFE)
# ===============================
@st.cache_data
def load_data():
    df = pd.read_csv("Nigeria_2G_3G_4G_All_Operators_ArcGIS.csv")
    df.columns = [c.lower() for c in df.columns]

    # Normalize columns
    df["latitude"] = df.get("latitude", df.get("lat"))
    df["longitude"] = df.get("longitude", df.get("lon", df.get("lng")))
    df["operator"] = df.get("operator", df.get("network", "Unknown"))
    df["technology"] = df.get("technology", df.get("tech", "Unknown"))

    df = df.dropna(subset=["latitude", "longitude"])
    return df

df = load_data()

# ===============================
# SESSION STATE (persist results)
# ===============================
if "analysis_done" not in st.session_state:
    st.session_state.analysis_done = False

# ===============================
# SIDEBAR INPUT
# ===============================
st.sidebar.header("📍 Location Input")

lat = st.sidebar.number_input("Latitude", value=9.0765, format="%.6f")
lon = st.sidebar.number_input("Longitude", value=7.3986, format="%.6f")

radius_km = st.sidebar.slider("Analysis Radius (km)", 1, 100, 10)
no_limit = st.sidebar.checkbox("No Distance Limit")

run = st.sidebar.button("▶ Run Analysis")

if run:
    st.session_state.analysis_done = True
    st.session_state.lat = lat
    st.session_state.lon = lon
    st.session_state.radius = radius_km
    st.session_state.no_limit = no_limit

# ===============================
# DISTANCE FUNCTION (FAST)
# ===============================
def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat/2)*2 + cos(radians(lat1))*cos(radians(lat2))*sin(dlon/2)*2
    return 2 * R * np.arcsin(np.sqrt(a))

# ===============================
# ANALYSIS
# ===============================
if st.session_state.analysis_done:

    lat = st.session_state.lat
    lon = st.session_state.lon

    df["distance_km"] = haversine(
        lat, lon,
        df["latitude"].values,
        df["longitude"].values
    )

    if st.session_state.no_limit:
        nearby = df.copy()
    else:
        nearby = df[df["distance_km"] <= st.session_state.radius]

    # Detect 5G safely
    nearby["is_5g"] = nearby["technology"].astype(str).str.contains("5g", case=False)

    # Operator colors
    operator_colors = {
        "mtn": [255, 204, 0],
        "airtel": [255, 0, 0],
        "glo": [0, 153, 0],
        "9mobile": [0, 204, 153]
    }

    def colorize(op):
        return operator_colors.get(str(op).lower(), [100, 100, 100])

    nearby["color"] = nearby["operator"].apply(colorize)

    # ===============================
    # TABS (11)
    # ===============================
    tabs = st.tabs([
        "📍 Coverage Map",
        "📊 Results Table",
        "📡 Operator Coverage",
        "🕳 Coverage Gaps",
        "🗼 New Tower Recommendation",
        "📐 Buffer Visualization",
        "📶 Technology Mix",
        "🗺 State Coverage Density",
        "📈 Sector Analysis",
        "🚀 5G Planning",
        "⬇ Export Results"
    ])

    # ===============================
    # TAB 1 – MAP
    # ===============================
    with tabs[0]:
        st.subheader("Coverage Map")

        layer = pdk.Layer(
            "ScatterplotLayer",
            nearby,
            get_position=["longitude", "latitude"],
            get_fill_color="color",
            get_radius=600,
            pickable=True
        )

        user_layer = pdk.Layer(
            "ScatterplotLayer",
            data=pd.DataFrame([{"lat": lat, "lon": lon}]),
            get_position=["lon", "lat"],
            get_fill_color=[0, 0, 255],
            get_radius=1000
        )

        st.pydeck_chart(pdk.Deck(
            initial_view_state=pdk.ViewState(
                latitude=lat,
                longitude=lon,
                zoom=9
            ),
            layers=[layer, user_layer]
        ))

    # ===============================
    # TAB 2 – TABLE
    # ===============================
    with tabs[1]:
        st.dataframe(nearby)

    # ===============================
    # TAB 3 – OPERATOR COVERAGE
    # ===============================
    with tabs[2]:
        st.bar_chart(nearby["operator"].value_counts())

    # ===============================
    # TAB 4 – COVERAGE GAPS
    # ===============================
    with tabs[3]:
        st.write("Areas beyond radius with no nearby towers")
        gaps = df[df["distance_km"] > st.session_state.radius]
        st.dataframe(gaps.head(200))

    # ===============================
    # TAB 5 – NEW TOWER
    # ===============================
    with tabs[4]:
        if not gaps.empty:
            rec_lat = gaps["latitude"].mean()
            rec_lon = gaps["longitude"].mean()
            st.success(f"Recommended Tower Location: {rec_lat:.5f}, {rec_lon:.5f}")

    # ===============================
    # TAB 6 – BUFFER
    # ===============================
    with tabs[5]:
        st.write(f"Buffer radius: {st.session_state.radius} km")

    # ===============================
    # TAB 7 – TECH MIX
    # ===============================
    with tabs[6]:
        st.pie_chart(nearby["technology"].value_counts())

    # ===============================
    # TAB 8 – STATE DENSITY
    # ===============================
    with tabs[7]:
        if "state" in nearby.columns:
            st.bar_chart(nearby["state"].value_counts())

    # ===============================
    # TAB 9 – SECTOR
    # ===============================
    with tabs[8]:
        st.write("Sector-based analysis placeholder (stable)")

    # ===============================
    # TAB 10 – 5G
    # ===============================
    with tabs[9]:
        st.write("Detected 5G sites")
        st.dataframe(nearby[nearby["is_5g"]])

    # ===============================
    # TAB 11 – EXPORT
    # ===============================
    with tabs[10]:
        st.download_button(
            "Download Nearby Coverage",
            nearby.to_csv(index=False),
            "nearby_coverage.csv"
        )
