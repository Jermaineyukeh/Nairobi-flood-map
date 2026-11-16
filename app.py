import pandas as pd
import pydeck as pdk
import streamlit as st

st.set_page_config(page_title="Nairobi Flood Hotspot Finder", layout="wide")

band_colors = {
    "Low": [255, 213, 79, 70],
    "Medium": [251, 140, 0, 225],
    "High": [220, 38, 38, 240],
}
land_cover_names = {
    10: "Tree cover", 20: "Shrubland", 30: "Grassland", 40: "Cropland",
    50: "Built up", 60: "Sparse vegetation", 90: "Herbaceous wetland",
}


@st.cache_data
def load_grid():
    grid_scores = pd.read_csv("grid_scores.csv")
    grid_features = pd.read_csv("grid_features.csv").drop(columns=["lon", "lat"])
    grid = grid_scores.merge(grid_features, on="point_id", how="left")
    grid["score_text"] = grid["flood_score"].round(2).astype(str)
    grid["color"] = grid["risk_band"].map(band_colors)
    return grid.sort_values("flood_score").reset_index(drop=True)


def show_spot_details(spot, grid):
    st.markdown(f"**{spot['risk_band']} risk**")
    st.metric("Flood score", f"{spot['flood_score']:.2f}")
    st.caption(f"Latitude {spot['lat']:.4f}, longitude {spot['lon']:.4f}")

    common_land_cover = land_cover_names.get(int(grid["land_cover"].mode()[0]), "Other")
    spot_facts = pd.DataFrame({
        "Fact": [
            "Land cover",
            "Elevation",
            "Slope",
            "Height vs surroundings (500 m)",
            "Built up within 100 m",
            "Built up within 500 m",
            "Distance to nearest river",
        ],
        "This spot": [
            land_cover_names.get(int(spot["land_cover"]), "Other"),
            f"{spot['elevation']:,.0f} m",
            f"{spot['slope']:.1f} degrees",
            f"{spot['local_relief_500']:+.1f} m",
            f"{spot['builtup_100']:.0%}",
            f"{spot['builtup_500']:.0%}",
            f"{spot['dist_river']:,.0f} m",
        ],
        "Area average": [
            f"{common_land_cover} (most common)",
            f"{grid['elevation'].mean():,.0f} m",
            f"{grid['slope'].mean():.1f} degrees",
            f"{grid['local_relief_500'].mean():+.1f} m",
            f"{grid['builtup_100'].mean():.0%}",
            f"{grid['builtup_500'].mean():.0%}",
            f"{grid['dist_river'].mean():,.0f} m",
        ],
    })
    st.table(spot_facts.set_index("Fact"))
    st.caption(
        "These are the facts the model looked at for this spot. A high score means the spot "
        "looks like the places that flooded on 1 May 2024."
    )


grid = load_grid()

st.sidebar.title("Controls")
chosen_bands = st.sidebar.multiselect(
    "Risk bands to show",
    options=["High", "Medium", "Low"],
    default=["High", "Medium"],
)
minimum_score = st.sidebar.slider("Minimum flood score", 0.0, 1.0, 0.0, 0.05)
st.sidebar.markdown(
    "<span style='color:#DC2626'>&#9679;</span> High, above 0.66<br>"
    "<span style='color:#FB8C00'>&#9679;</span> Medium, 0.33 to 0.66<br>"
    "<span style='color:#FFD54F'>&#9679;</span> Low, below 0.33 (shown faint)",
    unsafe_allow_html=True,
)

visible_points = grid[
    grid["risk_band"].isin(chosen_bands) & (grid["flood_score"] >= minimum_score)
]

st.title("Nairobi Flood Hotspot Finder")
st.caption(
    "North and east Nairobi. Shows where flooding is more likely in a major event. "
    "It is a susceptibility map, not a forecast."
)

map_tab, about_tab = st.tabs(["Map", "About the model"])

with map_tab:
    total_points = len(grid)
    band_counts = grid["risk_band"].value_counts()
    metric_columns = st.columns(4)
    for metric_column, band_name in zip(metric_columns[:3], ["High", "Medium", "Low"]):
        band_total = int(band_counts.get(band_name, 0))
        metric_column.metric(f"{band_name} risk points", f"{band_total:,} ({band_total / total_points:.0%})")
    metric_columns[3].metric("Points shown", f"{len(visible_points):,}")

    map_column, details_column = st.columns([3, 1])
    selected_objects = []

    with map_column:
        if visible_points.empty:
            st.warning("No points match these filters.")
        else:
            flood_layer = pdk.Layer(
                "ScatterplotLayer",
                id="flood_points",
                data=visible_points,
                get_position=["lon", "lat"],
                get_fill_color="color",
                get_radius=260,
                radius_min_pixels=3,
                radius_max_pixels=25,
                pickable=True,
                stroked=False,
            )
            map_view = pdk.data_utils.compute_view(grid[["lon", "lat"]], view_proportion=0.9)
            hover_tooltip = {
                "html": "<b>{risk_band} risk</b><br/>Flood score: {score_text}<br/>Click for details",
                "style": {"color": "white"},
            }
            map_event = st.pydeck_chart(
                pdk.Deck(layers=[flood_layer], initial_view_state=map_view, tooltip=hover_tooltip),
                on_select="rerun",
                selection_mode="single-object",
                height=620,
            )
            selected_objects = map_event.selection.objects.get("flood_points", [])

    with details_column:
        st.subheader("Spot details")
        selected_rows = (
            grid[grid["point_id"] == int(selected_objects[0]["point_id"])] if selected_objects else grid.iloc[0:0]
        )
        if selected_rows.empty:
            st.info("Click a dot on the map to see the facts behind its score.")
        else:
            show_spot_details(selected_rows.iloc[0], grid)

with about_tab:
    st.markdown(
        "**How the map was built**\n\n"
        "* About 20,000 spots were labelled flooded or dry using the UNOSAT flood map of 1 May 2024.\n"
        "* Each spot has facts about the ground: height, slope, dips in the land, land cover, how built up "
        "the area is, and the distance to the nearest river.\n"
        "* A random forest model learned which facts go with flooding. On areas it had never seen it got "
        "about 86% right, with a ROC AUC of 0.94.\n"
        "* We then placed a regular grid of points across north and east Nairobi and scored every point."
    )
    st.markdown(
        "**How to read it**\n\n"
        "The flood score runs from 0 to 1. It is a relative ranking of how much a spot looks like the places "
        "that flooded. It is not a percent chance of flooding. High is above 0.66, Medium is 0.33 to 0.66 "
        "and Low is below 0.33."
    )
    st.markdown(
        "**Limits**\n\n"
        "* The model learned from one flood event.\n"
        "* The land cover data is from 2021.\n"
        "* Drains are left out because few are mapped in OpenStreetMap.\n"
        "* It is a susceptibility map, not a forecast."
    )
    st.caption("Data: UNOSAT flood map of 1 May 2024, Copernicus DEM, ESA WorldCover 2021, OpenStreetMap.")
