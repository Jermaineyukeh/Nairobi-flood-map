import pandas as pd
import pydeck as pdk
import streamlit as st

st.set_page_config(page_title="Nairobi Flood Susceptibility", layout="wide")

band_colors = {
    "Low": [255, 213, 79],
    "Medium": [251, 140, 0],
    "High": [220, 38, 38],
}


@st.cache_data
def load_grid_scores():
    grid_scores = pd.read_csv("grid_scores.csv")
    grid_scores["score_text"] = grid_scores["flood_score"].round(2).astype(str)
    grid_scores["color"] = grid_scores["risk_band"].map(band_colors)
    return grid_scores.sort_values("flood_score")


grid_scores = load_grid_scores()

st.title("Nairobi Flood Susceptibility Map")
st.caption(
    "North and east Nairobi. Shows where flooding is more likely in a major event. "
    "It is a susceptibility map, not a forecast."
)

chosen_bands = st.sidebar.multiselect(
    "Risk bands to show",
    options=["Low", "Medium", "High"],
    default=["Low", "Medium", "High"],
)
minimum_score = st.sidebar.slider("Minimum flood score", 0.0, 1.0, 0.0, 0.05)

visible_points = grid_scores[
    grid_scores["risk_band"].isin(chosen_bands) & (grid_scores["flood_score"] >= minimum_score)
]

total_points = len(grid_scores)
band_counts = grid_scores["risk_band"].value_counts()

metric_columns = st.columns(4)
for metric_column, band_name in zip(metric_columns[:3], ["High", "Medium", "Low"]):
    band_total = int(band_counts.get(band_name, 0))
    metric_column.metric(f"{band_name} risk points", f"{band_total:,} ({band_total / total_points:.0%})")
metric_columns[3].metric("Points shown", f"{len(visible_points):,}")

if visible_points.empty:
    st.warning("No points match these filters.")
else:
    flood_layer = pdk.Layer(
        "ScatterplotLayer",
        data=visible_points,
        get_position=["lon", "lat"],
        get_fill_color="color",
        get_radius=260,
        radius_min_pixels=3,
        radius_max_pixels=25,
        opacity=0.8,
        pickable=True,
    )
    map_view = pdk.ViewState(
        latitude=float(grid_scores["lat"].mean()),
        longitude=float(grid_scores["lon"].mean()),
        zoom=10.3,
    )
    hover_tooltip = {
        "html": "<b>{risk_band} risk</b><br/>Flood score: {score_text}",
        "style": {"color": "white"},
    }
    st.pydeck_chart(
        pdk.Deck(layers=[flood_layer], initial_view_state=map_view, tooltip=hover_tooltip),
        height=600,
    )

st.markdown(
    "<span style='color:#FFD54F'>&#9679;</span> Low, below 0.33 &nbsp;&nbsp;&nbsp; "
    "<span style='color:#FB8C00'>&#9679;</span> Medium, 0.33 to 0.66 &nbsp;&nbsp;&nbsp; "
    "<span style='color:#DC2626'>&#9679;</span> High, above 0.66",
    unsafe_allow_html=True,
)

with st.expander("How to read this map"):
    st.write(
        "Each dot is a spot on a regular grid across north and east Nairobi. The colour shows how much "
        "that spot looks like the places that flooded on 1 May 2024. Hover over a dot to see its score."
    )
    st.write(
        "The flood score runs from 0 to 1. It is a relative ranking, not a percent chance of flooding."
    )
    st.write(
        "The model is a random forest. On areas it had never seen it got about 86% right, "
        "with a ROC AUC of 0.94."
    )
    st.write(
        "Limits: it learned from one flood event, the land cover data is from 2021, and drains are "
        "left out because few are mapped. It is not a forecast."
    )

st.caption("Data: UNOSAT flood map of 1 May 2024, Copernicus DEM, ESA WorldCover 2021, OpenStreetMap.")
