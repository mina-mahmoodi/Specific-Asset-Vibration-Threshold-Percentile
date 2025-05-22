import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Vibration Threshold Calculator", layout="wide")
st.title("📈 Vibration Warning & Error Threshold Calculator")

uploaded_file = st.file_uploader("Upload an Excel or CSV file", type=["xlsx", "xls", "csv"])

if uploaded_file:
    # Load file
    if uploaded_file.name.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
        sheet_selected = None
    else:
        xls = pd.ExcelFile(uploaded_file)
        sheet_selected = st.selectbox("Select a sheet", xls.sheet_names)
        df = pd.read_excel(uploaded_file, sheet_name=sheet_selected)

    # Rename known columns for consistency
    col_map = {
        'X': 'x', 'Y': 'y', 'Z': 'z',
        'T(X)': 't_x', 'T(Y)': 't_y', 'T(Z)': 't_z',
        'T(motor state)': 't_motor',
        'Motor State': 'motor_state'
    }
    df = df.rename(columns={col: col_map[col] for col in col_map if col in df.columns})

    required_cols = ['x', 'y', 'z']
    if not all(col in df.columns for col in required_cols):
        st.error(f"Missing required columns: {required_cols}")
    else:
        # Assume missing motor_state as 3 (ON)
        if 'motor_state' not in df.columns:
            df['motor_state'] = 3
        else:
            df['motor_state'] = df['motor_state'].fillna(3)

        # Filter rows where motor_state is 3 (ON)
        df_on = df[df['motor_state'] == 3]

        if df_on.empty:
            st.warning("No vibration data found while motor was ON (state = 3).")
        else:
            st.subheader(f"📊 Vibration Thresholds (Sheet: {sheet_selected if sheet_selected else 'CSV'})")

            thresholds = {}
            for axis in ['x', 'y', 'z']:
                warning = df_on[axis].quantile(0.85)
                error = df_on[axis].quantile(0.95)
                thresholds[axis.upper()] = {
                    'Warning Threshold (85%)': warning,
                    'Error Threshold (95%)': error
                }

            # Show thresholds table
            result_df = pd.DataFrame(thresholds).T
            st.dataframe(result_df.style.format("{:.2f}"))

            # Plot vibration histograms
            st.subheader("📈 Vibration Distribution While Motor is ON")
            melted = df_on.melt(value_vars=['x', 'y', 'z'], var_name='Axis', value_name='Vibration')
            fig = px.histogram(melted, x='Vibration', color='Axis',
                               barmode='overlay', marginal='box',
                               title="Vibration Histogram (Motor State = 3)")
            st.plotly_chart(fig, use_container_width=True)
