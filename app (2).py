import pandas as pd
import streamlit as st

st.set_page_config(page_title='Nairobi Flood Susceptibility', layout='wide')

band_colors = {'Low': '#FFD54F', 'Medium': '#FB8C00', 'High': '#B71C1C'}
point_size_metres = 250


@st.cache_data
def load_grid_scores():
    return pd.read_csv('grid_scores.csv')


grid_scores = load_grid_scores()
grid_scores['color'] = grid_scores['risk_band'].map(band_colors)

st.title('Nairobi Flood Susceptibility Map')
st.caption(
    'North and east Nairobi. Shows where flooding is more likely in a major event. '
    'It is a susceptibility map, not a forecast.'
)

chosen_bands = st.sidebar.multiselect(
    'Show these risk bands',
    options=['Low', 'Medium', 'High'],
    default=['Low', 'Medium', 'High'],
)

visible_points = grid_scores[grid_scores['risk_band'].isin(chosen_bands)]

st.map(visible_points, latitude='lat', longitude='lon', color='color', size=point_size_metres)

band_counts = grid_scores['risk_band'].value_counts().reindex(['Low', 'Medium', 'High'])
st.sidebar.subheader('Points in each band')
st.sidebar.write(band_counts)
