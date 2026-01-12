import streamlit as st
import geopandas as gpd
import folium
from streamlit_folium import folium_static
from shapely.geometry import Point

# ==========================================
# 1. PAGE CONFIG & STYLING
# ==========================================
st.set_page_config(
    layout="wide", 
    page_title="Spectrum: National Coverage Verifier",
    page_icon="📡"
)

# Custom CSS for professional metric styling
st.markdown("""
    <style>
    div[data-testid="stMetricValue"] {
        font-size: 24px;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("📡 Spectrum | National Coverage Verification")
st.markdown("### Network Coverage Verification Engine")
st.markdown("Verifies 2G/3G/4G coverage availability across all 36 States + FCT")
st.markdown("---")

# ==========================================
# 2. DATA LOADING
# ==========================================
COVERAGE_FILE = "buffered_towers.gpkg"
STATES_FILE = "gadm41_NGA_1.geojson"

@st.cache_data
def load_data():
    try:
        # Load Coverage & Force Lat/Lon (EPSG:4326)
        gdf_cov = gpd.read_file(COVERAGE_FILE, layer="buffered_towers")
        if gdf_cov.crs != "EPSG:4326":
            gdf_cov = gdf_cov.to_crs("EPSG:4326")
            
        # Load States & Force Lat/Lon
        gdf_states = gpd.read_file(STATES_FILE)
        if gdf_states.crs != "EPSG:4326":
            gdf_states = gdf_states.to_crs("EPSG:4326")
            
        return gdf_cov, gdf_states
    except Exception as e:
        st.error(f"Critical Data Error: {e}")
        return gpd.GeoDataFrame(), gpd.GeoDataFrame()

with st.spinner("Initializing National Geospatial Database..."):
    gdf_coverage, gdf_states = load_data()

# ==========================================
# 3. SIDEBAR CONTROLS
# ==========================================
if "run_analysis" not in st.session_state:
    st.session_state.run_analysis = False

with st.sidebar:
    st.header("📍 Search Parameters")
    
    with st.form("search_form"):
        # Default Coordinates: Wuse 2, Abuja
        lat = st.number_input("Latitude", value=9.05785, format="%.6f")
        lon = st.number_input("Longitude", value=7.49508, format="%.6f")
        
        submitted = st.form_submit_button("🔍 Verify Coverage", type="primary")
        
    if submitted:
        st.session_state.run_analysis = True
        
    st.markdown("---")
    st.caption("v1.0.0 | Competition Build")

# ==========================================
# 4. MAIN ANALYSIS ENGINE
# ==========================================
if st.session_state.run_analysis:
    
    # 1. Create the User Point
    raw_point = Point(lon, lat)
    
    # 2. Add Tolerance (Buffer 5m)
    user_geometry = raw_point.buffer(0.00005)
    
    # 3. State Check
    state_match = gdf_states[gdf_states.intersects(user_geometry)]
    state_name = state_match.iloc[0]['NAME_1'] if not state_match.empty else "Unknown Region"
    
    # 4. Coverage Check
    # Step A: Fast Filter
    possible_matches = list(gdf_coverage.sindex.query(user_geometry, predicate='intersects'))
    matches = gdf_coverage.iloc[possible_matches]
    
    # Step B: Precision Check
    exact_matches = matches[matches.intersects(user_geometry)]
    
    # ==========================================
    # 5. RESULTS DASHBOARD
    # ==========================================
    col1, col2 = st.columns([2, 1])
    
    # --- LEFT: MAP VISUALIZATION ---
    with col1:
        st.subheader(f"🗺️ Geospatial View: {state_name}")
        
        m = folium.Map(location=[lat, lon], zoom_start=14, tiles="CartoDB positron")
        
        # User Pin
        folium.Marker(
            [lat, lon], popup="Query Location", 
            icon=folium.Icon(color="red", icon="crosshairs", prefix="fa")
        ).add_to(m)
        
        # Highlight State Boundary (Blue border, transparent fill)
        # This gives context without cluttering the map with green blobs
        if not state_match.empty:
            folium.GeoJson(
                state_match,
                name="State Boundary",
                style_function=lambda x: {
                    'fillColor': '#3498db', 
                    'color': '#2980b9', 
                    'weight': 3, 
                    'fillOpacity': 0.1
                }
            ).add_to(m)
            
        # Render Static Map
        folium_static(m, width=950, height=500)

    # --- RIGHT: INTELLIGENCE REPORT ---
    with col2:
        st.subheader("📊 Signal Intelligence")
        
        if exact_matches.empty:
            st.error("❌ No Active Service")
            st.metric("Coverage Status", "Disconnected")
            st.warning(f"No signal found within 5m of these coordinates in **{state_name}**.")
        else:
            st.success("✅ Active Service Confirmed")
            
            # --- INTELLIGENT METRICS ---
            # 1. Total Operators (Who is here?)
            num_ops = exact_matches['Network_Operator'].nunique()
            
            # 2. Best Tech (Instead of raw count)
            # We check what generations are present and pick the 'Winner'
            all_gens = exact_matches['Network_Generation'].unique()
            if "4G" in all_gens or "LTE" in all_gens:
                best_tech = "4G LTE"
                delta_color = "normal" 
            elif "3G" in all_gens:
                best_tech = "3G (Broadband)"
                delta_color = "off"
            else:
                best_tech = "2G (Voice Only)"
                delta_color = "off"

            m1, m2 = st.columns(2)
            m1.metric("Operators Available", num_ops)
            m2.metric("Max Network Speed", best_tech, delta_color=delta_color)
            
            st.divider()
            
            # Operator Breakdown
            st.markdown("### Network Details")
            unique_ops = exact_matches['Network_Operator'].unique()
            
            for op in unique_ops:
                op_data = exact_matches[exact_matches['Network_Operator'] == op]
                gens = sorted(op_data['Network_Generation'].unique())
                
                badges = ""
                for g in gens:
                    color = "blue" if "4G" in g else "orange" if "3G" in g else "grey"
                    badges += f":{color}[**{g}**] "
                
                st.markdown(f"**{op}** — {badges}")

            # Raw Data Expander
            with st.expander("📂 View Technical Data"):
                cols = [c for c in ['Network_Operator', 'Network_Generation', 'Radio_Technology'] if c in exact_matches.columns]
                st.dataframe(exact_matches[cols].drop_duplicates(), hide_index=True)

# Footer
st.info("Feel free to use our [3D MAST PLANNER](https://mast3dplanner.streamlit.app/) to plan " \
        "your network deployments effectively.")

st.markdown("<hr>", unsafe_allow_html=True)
st.markdown("Made with ❤️ by [Group B](https://www.linkedin.com/in/favour-taiwo-57232023a/) for GIC competition " \
                "with special thanks to [opencellid](https://www.opencellid.org/) for for the dataset.")
