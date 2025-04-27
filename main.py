
import streamlit as st
import pandas as pd
import re
import plotly.graph_objs as go
from streamlit_extras.metric_cards import style_metric_cards

# Streamlit configuration
st.set_page_config(page_title="DVH Metrics Calculator", layout="wide")
st.title("📈 DVH Metrics Calculator")

# Custom CSS styling
custom_css = """
<style>
    div[data-testid="metric-container"] {
        background: linear-gradient(145deg, #a8d0e6, #64b5f6);
        border-radius: 15px;
        padding: 20px;
        margin: 15px;
        color: #2c3e50;
        text-align: center;
        box-shadow: 4px 4px 15px rgba(0, 0, 0, 0.1), -4px -4px 15px rgba(0, 0, 0, 0.1);
        font-family: 'Poppins', sans-serif;
        transition: all 0.3s ease;
    }
    div[data-testid="metric-container"] * {
        color: #34495e !important;
        font-weight: bold;
    }
    div[data-testid="stMetric"] div {
        font-size: 1.3em;
        color: #2980b9 !important;
    }
    div[data-testid="metric-container"]:hover {
        transform: translateY(-5px);
        box-shadow: 8px 8px 25px rgba(0, 0, 0, 0.15), -8px -8px 25px rgba(0, 0, 0, 0.15);
    }
    div[data-testid="metric-container"] .stMetric {
        background-color: #ecf0f1 !important;
        padding: 12px;
        border-radius: 12px;
    }
    .structure-card {
        background: white;
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 15px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        transition: all 0.3s ease;
    }
    .structure-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 6px 12px rgba(0, 0, 0, 0.15);
    }
    .structure-header {
        font-size: 1.2rem;
        font-weight: bold;
        color: #2c3e50;
        margin-bottom: 10px;
        border-bottom: 2px solid #64b5f6;
        padding-bottom: 5px;
    }
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

# Tabs
upload_tab, dvh_tab, structures_tab = st.tabs(["📋 Upload DVH Table", "📊 DVH", "🏗️ Structures"])

# Session state initialization
if "dvh_data" not in st.session_state:
    st.session_state.dvh_data = {}
if "meta_data" not in st.session_state:
    st.session_state.meta_data = {}
if "structure_stats" not in st.session_state:
    st.session_state.structure_stats = {}

# Upload tab
with upload_tab:
    st.header("📋 Upload DVH Table")
    uploaded_file = st.file_uploader("Choose a DVH file (txt)", type="txt")

    if uploaded_file is not None:
        try:
            content = uploaded_file.read().decode('utf-8-sig')
            lines = content.splitlines()

            meta_data = {}
            dvh_data = {}
            structure_stats = {}

            current_structure = None
            table_data = []

            for idx, line in enumerate(lines):
                line = line.strip()

                if line.startswith(("Patient Name", "﻿Patient Name")):
                    clean_line = line.replace("﻿", "")
                    parts = clean_line.split(":", 1)
                    meta_data['Name'] = parts[1].split(",")[0].strip() if len(parts) > 1 else 'N/A'

                elif line.startswith("Patient ID"):
                    meta_data['ID'] = line.split(":", 1)[1].strip()
                elif "Total dose" in line:
                    match = re.search(r'Total dose \[Gy\]:\s*([\d.]+)', line)
                    if match:
                        meta_data['Total Dose'] = float(match.group(1))
                elif line.startswith("Structure:"):
                    if current_structure and table_data:
                        df = pd.DataFrame(table_data, columns=["Dose (cGy)", "Volume (cc)", "Volume (%)"])
                        df = df.apply(pd.to_numeric, errors='coerce')
                        dvh_data[current_structure] = df
                        table_data = []
                    current_structure = line.split(":")[1].strip()
                elif re.match(r'^Volume \[cm³\]', line):
                    stats = {}
                    for i in range(10):
                        if idx + i < len(lines):
                            sub_line = lines[idx + i].strip()
                            parts = sub_line.split(":")
                            if len(parts) == 2:
                                stats[parts[0].strip()] = parts[1].strip()
                    structure_stats[current_structure] = stats
                elif re.match(r'^\d', line):
                    parts = re.split(r'[\s,]+', line)
                    if len(parts) >= 3:
                        table_data.append(parts[:3])
                elif re.match(r'^Conformity Index', line):
                    match = re.search(r'Conformity Index\s*:\s*([\d.]+)', line)
                    if match:
                        structure_stats.setdefault(current_structure, {})["Conformity Index"] = match.group(1).strip()
                elif re.match(r'^Gradient Measure \[cm\]', line):
                    match = re.search(r'Gradient Measure \[cm\]\s*:\s*([\d.]+)', line)
                    if match:
                        structure_stats.setdefault(current_structure, {})["Gradient Measure [cm]"] = match.group(1).strip()

            if current_structure and table_data:
                df = pd.DataFrame(table_data, columns=["Dose (cGy)", "Volume (cc)", "Volume (%)"])
                df = df.apply(pd.to_numeric, errors='coerce')
                dvh_data[current_structure] = df

            # Homogeneity Index for PTVs
            for structure in dvh_data:
                if "PTV" in structure.upper():
                    df = dvh_data[structure]
                    d2 = df.iloc[(df["Volume (%)"] - 2).abs().idxmin()]["Dose (cGy)"] / 100
                    d98 = df.iloc[(df["Volume (%)"] - 98).abs().idxmin()]["Dose (cGy)"] / 100
                    d50 = df.iloc[(df["Volume (%)"] - 50).abs().idxmin()]["Dose (cGy)"] / 100
                    if d50 != 0:
                        hi = ((d2 - d98) / d50) 
                        structure_stats.setdefault(structure, {})["Homogeneity Index"] = f"{hi:.2f}"

            st.session_state.dvh_data = dvh_data
            st.session_state.meta_data = meta_data
            st.session_state.structure_stats = structure_stats

            st.subheader("Patient Details")
            st.write(f"**Name:** {meta_data.get('Name', 'N/A')}")
            st.write(f"**ID:** {meta_data.get('ID', 'N/A')}")
            st.write(f"**Total Dose:** {meta_data.get('Total Dose', 'N/A')} Gy")
            st.success("DVH Data parsed and saved successfully!")

        except Exception as e:
            st.error(f"Error reading file: {e}")

# DVH tab
with dvh_tab:
    st.header("📊 DVH Curves")
    dvh_data = st.session_state.dvh_data

    if not dvh_data:
        st.info("Please upload a DVH file first.")
    else:
        fig = go.Figure()
        for structure, df in dvh_data.items():
            fig.add_trace(go.Scatter(
                x=df["Dose (cGy)"],
                y=df["Volume (%)"],
                mode='lines',
                name=structure,
                hovertemplate="<b>%{text}</b><br>Dose: %{x:.1f} cGy<br>Volume: %{y:.1f}%<extra></extra>",
                text=[structure]*len(df)
            ))
        fig.update_layout(
            title="DVH Curves for All Structures",
            xaxis_title="Dose (cGy)",
            yaxis_title="Volume (%)",
            hovermode="closest",
            height=600
        )
        st.plotly_chart(fig, use_container_width=True)

# Structures tab
with structures_tab:
    st.header("🏗️ Structure Statistics Dashboard")
    
    if not st.session_state.structure_stats:
        st.info("No structure statistics found. Please upload a DVH file first.")
    else:
        col1, col2 = st.columns([1, 3])
        
        with col1:
            st.subheader("Structure Selection")
            selected_structure = st.selectbox("Choose a structure", options=list(st.session_state.structure_stats.keys()))
            st.subheader("Filter Structures")
            search_term = st.text_input("Search structures", "")
            structure_types = {
                "Targets": ["PTV", "GTV", "CTV"],
                "OARs": ["Lung", "Heart", "Spinal Cord", "Esophagus"],
                "Other": []
            }
            selected_type = st.radio("Structure Type", options=list(structure_types.keys()), horizontal=True)
            st.subheader("Quick Metrics")
            if selected_structure:
                stats = st.session_state.structure_stats[selected_structure]
                st.metric("Volume", f"{stats.get('Volume [cm³]', 'N/A')} cm³")
                st.metric("Mean Dose", f"{stats.get('Mean Dose [%]', 'N/A')}%")
                st.metric("Max Dose", f"{stats.get('Max Dose [%]', 'N/A')}%")

        with col2:
            if selected_structure:
                stats = st.session_state.structure_stats[selected_structure]
                st.markdown(
                    f"""<div class="structure-card"><div class="structure-header">{selected_structure} Statistics</div></div>""",
                    unsafe_allow_html=True
                )
                tabs = st.tabs(["Dose Metrics", "Volume Metrics", "Other Metrics"])

                with tabs[0]:
                    cols = st.columns(2)
                    dose_metrics = [
                        ("Min Dose", "Min Dose [%]"),
                        ("Max Dose", "Max Dose [%]"),
                        ("Mean Dose", "Mean Dose [%]"),
                        ("Median Dose", "Median Dose [%]"),
                        ("Modal Dose", "Modal Dose [%]"),
                        ("STD", "STD [%]")
                    ]
                    for i, (label, key) in enumerate(dose_metrics):
                        if key in stats:
                            cols[i%2].metric(label, f"{stats[key]}{'%' if '%' not in str(stats[key]) else ''}")

                with tabs[1]:
                    cols = st.columns(2)
                    volume_metrics = [("Volume", "Volume [cm³]"), ("Equivalent Sphere Diam.", "Equiv. Sphere Diam. [cm]")]
                    for i, (label, key) in enumerate(volume_metrics):
                        if key in stats:
                            cols[i%2].metric(label, stats[key])

                with tabs[2]:
                    cols = st.columns(2)
                    other_metrics = [("Conformity Index", "Conformity Index"), ("Gradient Measure", "Gradient Measure [cm]")]
                    if "PTV" in selected_structure.upper() and "Homogeneity Index" in stats:
                        other_metrics.append(("Homogeneity Index", "Homogeneity Index"))
                        with st.expander("Homogeneity Index Info"):
                            st.write("""
                            **Homogeneity Index (HI):**
                            - Measures dose uniformity within PTV
                            - Formula: (D2% - D98%) / D50% × 100
                            - Ideal: <10%, Acceptable: <15%
                            """)
                    for i, (label, key) in enumerate(other_metrics):
                        if key in stats:
                            cols[i%2].metric(label, stats[key])

                if selected_structure in st.session_state.dvh_data:
                    st.subheader(f"{selected_structure} DVH Preview")
                    df = st.session_state.dvh_data[selected_structure]
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(
                        x=df["Dose (cGy)"],
                        y=df["Volume (%)"],
                        mode='lines',
                        name=selected_structure
                    ))
                    fig.update_layout(
                        height=300,
                        margin=dict(l=20, r=20, t=30, b=20),
                        xaxis_title="Dose (cGy)",
                        yaxis_title="Volume (%)"
                    )
                    st.plotly_chart(fig, use_container_width=True)

        st.subheader("All Structures")
        filtered_structures = [
            s for s in st.session_state.structure_stats.keys()
            if search_term.lower() in s.lower() and (
                not selected_type or 
                any(t in s for t in structure_types[selected_type])
            )
        ]
        for structure in filtered_structures:
            with st.expander(f"{structure}"):
                stats = st.session_state.structure_stats[structure]
                cols = st.columns(3)
                cols[0].metric("Volume", f"{stats.get('Volume [cm³]', 'N/A')} cm³")
                cols[1].metric("Mean Dose", f"{stats.get('Mean Dose [%]', 'N/A')}%")
                cols[2].metric("Max Dose", f"{stats.get('Max Dose [%]', 'N/A')}%")
                if "PTV" in structure.upper() and "Homogeneity Index" in stats:
                    cols = st.columns(3)
                    cols[0].metric("Homogeneity Index", stats["Homogeneity Index"])

        style_metric_cards()
