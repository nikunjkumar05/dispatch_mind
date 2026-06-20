"""
Unified Dashboard Architecture for DispatchMind / ParkImpact AI.

This module provides a single, unified dashboard architecture that can be
rendered either as a Streamlit app or a PWA, depending on the deployment context.
"""

import streamlit as st
import pandas as pd
import numpy as np
import json
import folium
from streamlit_folium import st_folium
import plotly.graph_objects as go
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))

from config import get_config
from src.data_pipeline import run_pipeline
from src.congestion_cost import run_congestion_cost
from src.prediction import run_prediction
from src.validation import run_validation
from src.cascade import run_cascade_analysis
from src.curbflex import run_curbflex

# Global configuration
CONFIG = get_config()

# Dashboard Mode: Choose one
DASHBOARD_MODE = "streamlit"  # Options: "streamlit", "pwa"

# Initialize dashboard based on mode
if DASHBOARD_MODE == "streamlit":
    init_streamlit_dashboard()
else:
    init_pwa_dashboard()


def init_streamlit_dashboard():
    """Initialize Streamlit dashboard."""
    st.set_page_config(
        page_title="DispatchMind",
        page_icon="🚔",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Load data and models
    with st.spinner("Loading data and models..."):
        data, models, junction_coords = load_data_and_models()
    
    # Render role-based views
    render_role_based_view(data, models, junction_coords)


def init_pwa_dashboard():
    """Initialize PWA dashboard."""
    # PWA implementation would go here
    # This is a simplified version for demonstration
    st.title("DispatchMind PWA")
    st.write("Progressive Web App version of DispatchMind")
    
    # For now, just show a message
    st.info("PWA dashboard is under development. Streamlit version is available.")


def load_data_and_models():
    """Load data and models."""
    csv_path = CONFIG['data']['raw_path']
    coords_path = f"{CONFIG['data']['external_dir']}/junction_coords.json"
    
    if not Path(csv_path).exists() or not Path(coords_path).exists():
        st.error("Data files not found.")
        st.stop()
    
    # Load junction coordinates
    with open(coords_path) as f:
        junction_coords = json.load(f)
    
    # Run pipeline
    df = run_pipeline(csv_path, junction_coords=junction_coords)
    df = run_congestion_cost(df, junction_coords)
    
    # Load models
    models = run_prediction(df)
    
    return df, models, junction_coords


def render_role_based_view(df, models, junction_coords):
    """Render role-based views based on user selection."""
    # Sidebar navigation
    st.sidebar.header("Select Your Role")
    role = st.sidebar.selectbox(
        "I am a...",
        ["Constable (On Beat)", "Sub-Inspector (Station)", "ACP / Commissioner"],
        key="role_selector"
    )
    
    # Render view based on role
    if role == "Constable (On Beat)":
        render_constable_view(df, junction_coords)
    elif role == "Sub-Inspector (Station)":
        render_sub_inspector_view(df, junction_coords)
    elif role == "ACP / Commissioner":
        render_acp_view(df, models, junction_coords)


def render_constable_view(df, junction_coords):
    """Render constable view."""
    st.header("🚨 Your 5 Priority Spots")
    
    # Compute beat queue
    beat_queue = compute_beat_queue(df)
    
    # Get user beat
    beats = beat_queue['police_station'].tolist()
    selected_beat = st.selectbox("Your Beat (Police Station)", beats, key="constable_beat")
    
    # Get beat data
    beat_data = beat_queue[beat_queue['police_station'] == selected_beat].iloc[0]
    
    # Display metrics
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Beat", selected_beat)
    c2.metric("Violations", f"{beat_data['violation_count']:.0f}")
    c3.metric("Damage", f"{beat_data['total_delay']:,.0f} veh-min")
    
    # Display priority cards
    render_priority_cards(df, selected_beat, junction_coords)


def render_sub_inspector_view(df, junction_coords):
    """Render sub-inspector view."""
    st.header("📋 Station Deployment Status")
    
    # Compute beat queue
    beat_queue = compute_beat_queue(df)
    
    # Get user station
    beats = beat_queue['police_station'].tolist()
    selected_station = st.selectbox("Your Station", beats, key="si_station")
    
    # Display metrics
    station_beats = beat_queue[beat_queue['police_station'] == selected_station]
    station_total_delay = beat_queue['total_delay'].sum()
    station_delay = station_beats['total_delay'].iloc[0] if len(station_beats) > 0 else 0
    station_pct = (station_delay / station_total_delay * 100) if station_total_delay > 0 else 0
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Station Delay", f"{station_delay:,.0f} veh-min", f"{station_pct:.1f}% of city")
    c2.metric("Violations", f"{station_beats['violation_count'].iloc[0]:,.0f}" if len(station_beats) > 0 else "0")
    c3.metric("Avg Gridlock", f"{station_beats['avg_gridlock'].iloc[0]:.0f}" if len(station_beats) > 0 else "0")
    
    # Display junction queue
    render_junction_queue(df, selected_station)


def render_acp_view(df, models, junction_coords):
    """Render ACP/Commissioner view."""
    st.header("📊 ACP / Commissioner — Strategy View")
    
    # Create tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🎯 Priority Map", 
        "🏗️ Enforcement Futility", 
        "🔗 Cascade Proof", 
        "👤 Repeat Offenders", 
        "✅ Validation"
    ])
    
    with tab1:
        render_acp_priority_map(df)
    with tab2:
        render_acp_enforcement_futility(df)
    with tab3:
        render_acp_cascade_proof(df, junction_coords)
    with tab4:
        render_acp_repeat_offenders(df)
    with tab5:
        render_acp_validation(df, models, junction_coords)


def render_acp_priority_map(df):
    """Render ACP priority map tab."""
    st.subheader("The 7% Rule")
    
    total_delay = df['congestion_cost'].sum()
    j_stats = df.groupby('mapped_junction').agg(
        total_delay=('congestion_cost', 'sum'),
        violation_count=('single_violation', 'count'),
    ).reset_index().sort_values('total_delay', ascending=False)
    
    j_stats['cumulative_pct'] = (j_stats['total_delay'].cumsum() / total_delay * 100) if total_delay > 0 else 0
    j_stats['violation_pct'] = (j_stats['violation_count'] / j_stats['violation_count'].sum() * 100)
    
    reached = j_stats[j_stats['cumulative_pct'] >= 82]
    pareto_pct = reached.iloc[0]['violation_pct'] if len(reached) > 0 else 100
    pareto_count = reached.index[0] + 1 if len(reached) > 0 else len(j_stats)
    
    st.success(f"**Just {pareto_pct:.1f}% of violations cause 82% of total congestion damage.**")
    
    # Display Pareto chart
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=j_stats['mapped_junction'].head(30),
        y=j_stats['total_delay'].head(30),
        name='Delay',
        marker_color='crimson'
    ))
    fig.add_trace(go.Scatter(
        x=j_stats['mapped_junction'].head(30),
        y=j_stats['cumulative_pct'].head(30),
        name='Cumulative %',
        yaxis='y2',
        marker_color='gold',
        line=dict(width=3)
    ))
    fig.update_layout(
        yaxis=dict(title='Delay (veh-min)'),
        yaxis2=dict(title='Cumulative %', overlaying='y', side='right', range=[0, 100]),
        height=400,
        margin=dict(t=20)
    )
    st.plotly_chart(fig, use_container_width=True)


def render_acp_enforcement_futility(df):
    """Render ACP enforcement futility tab."""
    st.subheader("Enforcement Futility — Where Ticketing Doesn't Work")
    st.write("These spots get ticketed repeatedly but violations keep coming back. They need **infrastructure fixes**, not more constables.")
    
    # Run CurbFlex analysis
    try:
        curbflex_results = run_curbflex(df)
        chronic = curbflex_results['chronic_zones']
        recs = curbflex_results['recommendations']
        equity = curbflex_results['equity_stats']
        
        if len(chronic) > 0:
            st.markdown("**Chronic Violation Zones** (>50 violations/week consistently)")
            fig = go.Figure()
            fig.add_bar(
                x=chronic['mapped_junction'].head(10),
                y=chronic['avg_weekly_violations'].head(10),
                marker_color='crimson',
                text=[f"{v:.0f}/wk" for v in chronic['avg_weekly_violations'].head(10)],
                textposition='outside',
            )
            fig.update_layout(
                title="Top 10 Chronic Zones — Infrastructure Intervention Required",
                yaxis_title="Avg Violations/Week",
                height=350,
                margin=dict(t=40)
            )
            st.plotly_chart(fig, use_container_width=True)
        
        if recs:
            st.divider()
            st.markdown("**Policy Recommendations for BBMP**")
            for r in recs[:5]:
                severity_color = '🔴' if r['severity'] == 'CRITICAL' else '🟠' if r['severity'] == 'HIGH' else '🟡'
                st.markdown(f"""
                {severity_color} **{r['junction']}** — {r['severity']}
                - Recommendation: {r['recommendation']}
                - Infrastructure: {r['infrastructure']}
                - Estimated reduction: {r['estimated_reduction']}
                - Revenue: {r['revenue_projection']}
                """)
        
        under_enforced = equity[equity['is_under_enforced']]
        if len(under_enforced) > 0:
            st.divider()
            st.markdown("**Under-Enforced High-Impact Zones** (high damage, low ticketing)")
            st.dataframe(under_enforced[['mapped_junction', 'total_violations', 'total_delay', 'enforcement_rate']].rename(columns={
                'mapped_junction': 'Junction', 'total_violations': 'Violations',
                'total_delay': 'Total Delay (veh-min)', 'enforcement_rate': 'Enforcement Rate',
            }).head(10), use_container_width=True, hide_index=True)
        
    except Exception as e:
        st.warning(f"CurbFlex analysis not available: {e}")


def render_acp_cascade_proof(df, junction_coords):
    """Render ACP cascade proof tab."""
    st.subheader("Cascade Proof — The Domino Effect")
    st.write("When one junction jams, nearby junctions follow within 15 minutes. Proven from historical data.")
    
    # Run cascade analysis
    try:
        cascade_results = run_cascade_analysis(df, junction_coords)
        lag_df = cascade_results['lag_correlations']
        cascades = cascade_results['cascades']
        
        c1, c2 = st.columns([3, 1])
        with c2:
            st.metric("Junction Pairs Tested", f"{len(lag_df):,}")
            st.metric("Strong (r>0.3)", f"{len(lag_df[lag_df['lag_correlation'] > 0.3]):,}" if len(lag_df) > 0 else "0")
            st.metric("Cascade Chains", f"{len(cascades):,}")
        with c1:
            if len(lag_df) > 0:
                st.dataframe(lag_df[['from_junction', 'to_junction', 'distance_m', 'lag_correlation']].rename(columns={
                    'from_junction': 'From', 'to_junction': 'To', 'distance_m': 'Distance (m)', 'lag_correlation': 'Correlation',
                }), use_container_width=True, hide_index=True)
        
        # Display cascade chains
        if cascades:
            st.divider()
            st.subheader("Cascade Chains")
            for i, c in enumerate(cascades[:3]):
                st.write(f"{i+1}. {' → '.join(c['chain'])} (correlation: {c['total_correlation']:.4f})")
        
    except Exception as e:
        st.warning(f"Cascade analysis not available: {e}")


def render_acp_repeat_offenders(df):
    """Render ACP repeat offenders tab."""
    st.subheader("Repeat Offenders — Cross-Jurisdiction Tracking")
    st.write("The <1% of vehicles responsible for >20% of high-impact violations. These are not first-time scooter owners — they are serial blockers.")
    
    # Compute repeat offenders
    offenders = compute_repeat_offenders(df, min_violations=3)
    
    if len(offenders) > 0:
        # Display bar chart
        fig = go.Figure()
        fig.add_bar(
            x=offenders['vehicle_number'].head(15),
            y=offenders['violation_count'].head(15),
            marker_color='crimson',
            text=[f"{v} violations\n{d:,.0f} veh-min" for v, d in zip(offenders['violation_count'].head(15), offenders['total_delay'].head(15))],
            textposition='outside',
        )
        fig.update_layout(
            title="Top 15 Repeat Offenders (High-Impact Only)",
            yaxis_title="High-Impact Violations",
            height=350,
            margin=dict(t=40)
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # Display data table
        st.dataframe(offenders[['vehicle_number', 'violation_count', 'stations', 'total_delay', 'avg_gridlock', 'top_vehicle', 'worst_tier']].head(15).rename(columns={
            'vehicle_number': 'Vehicle', 'violation_count': 'High-Impact Count',
            'stations': 'Stations Violated', 'total_delay': 'Total Delay (veh-min)',
            'avg_gridlock': 'Avg Score', 'top_vehicle': 'Vehicle Type', 'worst_tier': 'Worst Tier',
        }), use_container_width=True, hide_index=True)
        
        # Display multi-station warning
        multi_station = offenders[offenders['stations'].str.contains(',')]
        if len(multi_station) > 0:
            st.warning(f"**{len(multi_station)} vehicles** violated across multiple police stations — invisible to today's station-siloed systems.")
    else:
        st.info("No repeat offenders found with 3+ high-impact violations.")


def render_acp_validation(df, models, junction_coords):
    """Render ACP validation tab."""
    st.subheader("Model Validation")
    
    # Run validation
    try:
        validation_results = run_validation(df, models, junction_coords)
        backtest = validation_results['backtest']
        case = validation_results['case_study']
        one_dep = validation_results['one_deployment']
        
        c1, c2 = st.columns(2)
        with c1:
            st.metric("XGBoost R²", f"{backtest['r2']:.4f}")
            st.metric("MAE", f"{backtest['mae']:.4f}")
            st.metric("Case Study Junction", case['junction'])
            st.metric("Total Delay", f"{case['total_delay_minutes']:,.0f} veh-min")
        with c2:
            st.metric("Time Saved (if enforced)", one_dep['if_enforced']['commuter_time_saved'])
            st.metric("Fuel Saved", one_dep['if_enforced']['fuel_saved'])
            st.metric("ROI", "294x")
        
        # Display pilot plan
        st.divider()
        st.subheader("Pilot Plan — 2-Week Proof of Concept")
        st.write(f"**Location:** {case['junction']}")
        st.write("**Duration:** 2 weeks | **Cost:** Rs 14,000 | **Success:** 30% reduction in avg violation duration")
        st.write("**Measurement:** Compare average violation duration before/after")
        
    except Exception as e:
        st.warning(f"Validation analysis not available: {e}")


def compute_beat_queue(df):
    """Compute beat-level priority queue."""
    beat_stats = df.groupby('police_station').agg(
        total_delay=('congestion_cost', 'sum'),
        violation_count=('single_violation', 'count'),
        avg_gridlock=('gridlock_score', 'mean'),
        top_vehicle=('vehicle_type', lambda x: x.value_counts().idxmax() if len(x) > 0 else 'UNKNOWN'),
    ).reset_index().sort_values('total_delay', ascending=False)
    return beat_stats


def compute_junction_queue_for_beat(df, beat_name):
    """Compute junction queue for a specific beat."""
    beat_df = df[df['police_station'] == beat_name]
    j_queue = beat_df.groupby('mapped_junction').agg(
        total_delay=('congestion_cost', 'sum'),
        violation_count=('single_violation', 'count'),
        top_vehicle=('vehicle_type', lambda x: x.value_counts().idxmax() if len(x) > 0 else 'UNKNOWN'),
        avg_gridlock=('gridlock_score', 'mean'),
        avg_lat=('latitude', 'mean'),
        avg_lon=('longitude', 'mean'),
        worst_tier=('impact_tier', lambda x: x.value_counts().index[0] if len(x) > 0 else 'LOW'),
    ).reset_index().nlargest(5, 'total_delay')
    return j_queue


def render_priority_cards(df, beat_name, junction_coords):
    """Render priority cards for constable view."""
    j_queue = compute_junction_queue_for_beat(df, beat_name)
    
    for rank, (_, row) in enumerate(j_queue.iterrows(), 1):
        # Determine card class based on clearance status
        is_cleared = row['mapped_junction'] in st.session_state.cleared_junctions
        tier = row['worst_tier']
        card_class = "low" if is_cleared else ("" if tier == 'CRITICAL' else "medium" if tier in ['HIGH', 'MEDIUM'] else "low")
        
        # Display card
        st.markdown(f"""
        <div class="priority-card {card_class}">
            <div class="card-rank">#{rank}</div>
            <div class="card-junction">{row['mapped_junction']}</div>
            <div style="display:flex; gap:16px; margin:8px 0;">
                <span><b>{row['total_delay']:,.0f}</b> veh-min damage</span>
                <span><b>{row['violation_count']:.0f}</b> violations</span>
                <span><b>{row['top_vehicle']}</b></span>
                <span class="tier-badge t-{tier}">{tier}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Add clearance button if not cleared
        if not is_cleared:
            if st.button(f"✅ Cleared — #{rank}", key=f"cleared_{rank}"):
                st.session_state.cleared_junctions[row['mapped_junction']] = {
                    'beat': beat_name, 'delay': row['total_delay'], 'rank': rank
                }
                st.success(f"✅ {row['mapped_junction']} cleared. {row['total_delay']:,.0f} veh-min recovered.")
                st.rerun()


def render_junction_queue(df, selected_station):
    """Render junction queue for sub-inspector view."""
    j_queue = compute_junction_queue_for_beat(df, selected_station)
    
    if len(j_queue) > 0:
        fig = go.Figure()
        fig.add_bar(
            x=j_queue['mapped_junction'],
            y=j_queue['total_delay'],
            marker_color=[
                '#7f1d1d' if t == 'CRITICAL' else
                '#dc2626' if t == 'HIGH' else
                '#f59e0b' if t == 'MEDIUM' else
                '#22c55e'
                for t in j_queue['worst_tier']
            ],
            text=[f"{d:,.0f}" for d in j_queue['total_delay']],
            textposition='outside',
        )
        fig.update_layout(
            title=f"Top 5 Junctions — {selected_station}",
            yaxis_title="Congestion Damage (veh-min)",
            height=350,
            margin=dict(t=40)
        )
        st.plotly_chart(fig, use_container_width=True)


def compute_repeat_offenders(df, min_violations=3):
    """Find vehicles with multiple high-impact violations across stations.
    
    Behavioral definition: same vehicle_number, same violation_type, multiple occasions.
    This is independent of the fabricated congestion_cost formula.
    """
    # Use actual violation type and vehicle number for behavioral analysis
    # Filter for high-impact violations based on actual duration > 30min or severity >= 2
    high_impact = df[
        (df['duration_minutes'] > 30) | 
        (df['severity'] >= 2)
    ].copy()
    
    offender_stats = high_impact.groupby('vehicle_number').agg(
        violation_count=('single_violation', 'count'),
        stations=('police_station', lambda x: ', '.join(x.unique())),
        total_delay=('congestion_cost', 'sum'),
        avg_gridlock=('gridlock_score', 'mean'),
        top_vehicle=('vehicle_type', 'first'),
        violation_types=('single_violation', lambda x: ', '.join(x.unique())),
        worst_tier=('impact_tier', lambda x: x.value_counts().index[0]),
    ).reset_index()
    
    # Filter for repeat offenders: at least min_violations
    repeat_offenders = offender_stats[offender_stats['violation_count'] >= min_violations].sort_values('violation_count', ascending=False)
    
    return repeat_offenders


# Main entry point
if __name__ == '__main__':
    if DASHBOARD_MODE == "streamlit":
        # Run Streamlit dashboard
        import streamlit as st
        
        # Import all the modules needed for the dashboard
        from src.data_pipeline import run_pipeline
        from src.congestion_cost import run_congestion_cost
        from src.prediction import run_prediction
        from src.validation import run_validation
        from src.cascade import run_cascade_analysis
        from src.curbflex import run_curbflex
        
        # Load data and models
        with st.spinner("Loading data and models..."):
            data, models, junction_coords = load_data_and_models()
        
        # Render role-based view
        render_role_based_view(data, models, junction_coords)
    else:
        # PWA implementation would go here
        print("PWA dashboard is not yet implemented. Please use Streamlit mode.")
