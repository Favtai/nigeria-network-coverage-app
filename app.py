import streamlit as st
import pandas as pd
import folium
from geopy.distance import geodesic

# ---------------- PAGE CONFIG ----------------
st.set_page_config(
    page_title="Nigeria Network Coverage & Gap Analysis",
    layout="wide"
)

st.title("📡 Nigeria Network Coverage & Gap Analysis Dashboard")

# ---------------- SESSION STATE ----------------
if "analysis_done" not in st.session_state:
    st.session_state.analysis_done = False

# ---------------- LOAD DATA ----------------
@st.cache_data
def load_data():
    return pd.read_csv("Nigeria_2G_3G_4G_All_Operators_ArcGIS.csv")

try:
    df = load_data()
except Exception as e:
    st.error("❌ CSV file not found or failed to load.")
    st.stop()

df.columns = df.columns.str.lower()

# Detect columns safely
lat_col = next(c for c in df.columns if "lat" in c)
lon_col = next(c for c in df.columns if "lon" in c)
operator_col = next(c for c in df.columns if "operator" in c)
tech_col = next(c for c in df.columns if "2g" in c or "3g" in c or "4g" in c or "tech" in c)

state_col = None
for c in df.columns:
    if c in ["state", "admin1", "region"]:
        state_col = c
        break

# ---------------- SIDEBAR ----------------
st.sidebar.header("📍 Input Coordinates")

lat = st.sidebar.number_input("Latitude", value=6.5244, format="%.6f")
lon = st.sidebar.number_input("Longitude", value=3.3792, format="%.6f")

no_limit = st.sidebar.checkbox("No Distance Limit", value=True)
radius_km = st.sidebar.slider("Analysis Radius (km)", 5, 100, 20)

if st.sidebar.button("🔍 Run Analysis"):
    st.session_state.analysis_done = True
    st.session_state.lat = lat
    st.session_state.lon = lon
    st.session_state.radius = radius_km
    st.session_state.no_limit = no_limit

# ---------------- TABS ----------------
tabs = st.tabs([
    "🗺 Coverage Map",
    "📊 Results Table",
    "📥 Export Network",
    "🚫 Coverage Gaps",
    "📤 Export Gaps",
    "🏗 New Tower Recommendation",
    "📤 Export Towers",
    "🏙 State Coverage Density",
    "📘 How It Works"
])

# ---------------- ANALYSIS ----------------
if st.session_state.analysis_done:
    lat0 = st.session_state.lat
    lon0 = st.session_state.lon
    radius = st.session_state.radius
    no_limit = st.session_state.no_limit

    df["distance_km"] = df.apply(
        lambda r: geodesic((lat0, lon0), (r[lat_col], r[lon_col])).km,
        axis=1
    )

    if no_limit:
        nearby = df.copy()
    else:
        nearby = df[df["distance_km"] <= radius].copy()

    nearby["confidence"] = nearby["distance_km"].apply(
        lambda d: "High" if d <= 5 else "Medium" if d <= 15 else "Low"
    )

    # Operator colors
    operator_colors = {
        "mtn": "yellow",
        "airtel": "red",
        "glo": "green",
        "9mobile": "blue"
    }

    # ---------------- TAB 1: MAP ----------------
    with tabs[0]:
        m = folium.Map(location=[lat0, lon0], zoom_start=10)

        folium.Marker(
            [lat0, lon0],
            tooltip="Input Location",
            icon=folium.Icon(color="black")
        ).add_to(m)

        if not no_limit:
            folium.Circle(
                [lat0, lon0],
                radius=radius * 1000,
                color="blue",
                fill=True,
                fill_opacity=0.08
            ).add_to(m)

        for _, r in nearby.iterrows():
            op = str(r[operator_col]).lower()
            color = operator_colors.get(op, "gray")

            folium.CircleMarker(
                [r[lat_col], r[lon_col]],
                radius=4,
                color=color,
                fill=True,
                fill_opacity=0.8,
                tooltip=f"""
                Operator: {r[operator_col]}<br>
                Tech: {r[tech_col]}<br>
                Distance: {r['distance_km']:.2f} km<br>
                Confidence: {r['confidence']}
                """
            ).add_to(m)

        st.components.v1.html(m.repr_html(), height=600)

    # ---------------- TAB 2: TABLE ----------------
    with tabs[1]:
        st.dataframe(
            nearby[[operator_col, tech_col, "distance_km", "confidence"]]
            .sort_values("distance_km")
        )

    # ---------------- TAB 3: EXPORT NETWORK ----------------
    with tabs[2]:
        st.download_button(
            "⬇ Download Network Results",
            nearby.to_csv(index=False),
            "network_results.csv",
            "text/csv"
        )

    # ---------------- TAB 4: COVERAGE GAPS ----------------
    with tabs[3]:
        if nearby.empty:
            gap_status = "No Coverage"
            recommendation = "Build new tower"
        else:
            gap_status = "Partial Coverage"
            recommendation = "Coverage improvement needed"

        gap_df = pd.DataFrame([{
            "latitude": lat0,
            "longitude": lon0,
            "coverage_status": gap_status,
            "network_count": len(nearby),
            "nearest_distance_km": nearby["distance_km"].min() if not nearby.empty else None,
            "recommendation": recommendation
        }])

        st.dataframe(gap_df)

    # ---------------- TAB 5: EXPORT GAPS ----------------
    with tabs[4]:
        st.download_button(
            "⬇ Download Coverage Gaps",
            gap_df.to_csv(index=False),
            "coverage_gaps.csv",
            "text/csv"
        )

    # ---------------- TAB 6: NEW TOWER ----------------
    with tabs[5]:
        tower_df = pd.DataFrame([{
            "recommended_latitude": lat0 + 0.02,
            "recommended_longitude": lon0 + 0.02,
            "reason": "Coverage gap / weak signal",
            "based_on_networks": len(nearby)
        }])

        st.dataframe(tower_df)

    # ---------------- TAB 7: EXPORT TOWER ----------------
    with tabs[6]:
        st.download_button(
            "⬇ Download Recommended Tower",
            tower_df.to_csv(index=False),
            "recommended_tower.csv",
            "text/csv"
        )

    # ---------------- TAB 8: STATE DENSITY ----------------
    with tabs[7]:
        if state_col:
            density = df.groupby(state_col).size().reset_index(name="site_count")
            st.dataframe(density.sort_values("site_count", ascending=False))
        else:
            st.warning("State column not found in dataset")

    # ---------------- TAB 9: GUIDE ----------------
    with tabs[8]:
        st.markdown("""
        ### 📘 How This Dashboard Works
        - Enter coordinates
        - Choose radius or no limit
        - View nearby network coverage
        - Identify gaps
        - Get new tower recommendations
        - Export all results as CSV

        *Data Source:* Nigeria 2G/3G/4G Network Dataset  
        *No 5G. No GeoJSON. Stable Deployment.*
        """)

else:
    st.info("👈 Enter coordinates and click *Run Analysis*")
