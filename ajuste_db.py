import streamlit as st
import plotly.graph_objects as go

fig1 = go.Figure(go.Indicator(
    mode="gauge",
    value=20,
    delta={'reference': 100},
    number={'suffix': "%"},
    domain={'x': [0, 1], 'y': [0, 1]},
    gauge={
        'axis': {'range': [0, 30], 'tickvals': [10, 30], 'ticktext': ['10', '30']},
        'bar': {'color': 'lightblue', 'thickness': 1},
        'threshold': {'line': {'color': '#000000', 'width': 2}, 'thickness': 1, 'value': 20}
    },
    title={'text': "Test", 'font': {'size': 20}},
))

fig1.add_annotation(
    x=0.5,
    y=0.35,
    text=f"20 ({87.8}%)",
    showarrow=False,
    font=dict(size=20),
)

fig1.add_annotation(
    x=0.5,
    y=-0.1,
    text=f"9 ({50}%)",
    showarrow=False,
    font=dict(size=15),
)

fig1.add_annotation(
    x=0.5,
    y=1.2,
    text="Máximo: 30",
    showarrow=False,
    font=dict(size=12),
)

fig1.update_layout(height=220, margin=dict(t=30))

st.plotly_chart(fig1, use_container_width=True)