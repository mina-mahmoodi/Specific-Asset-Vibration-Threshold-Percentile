import streamlit as st
import pandas as pd
import plotly.express as px

# Setup
st.set_page_config(page_title="Vibration Threshold Calculator", layout="wide")
st.title("📈 Vibration Warning & Error Threshold Calculator")

# Upload
uploaded_file = st.file_uploader("Upload your vibration data (.csv or .xlsx)", type=["csv", "xlsx"])

if uploaded_file:
    try:
        if uploaded_file.name.endswith(".csv"):
            df = pd.read_csv(uploaded_file)
            sheets = {"CSV Data": df}
            sheet_names = ["CSV Data"]
        else:
            xls = pd.ExcelFile(uploaded_file)
            sheet_names = xls.sheet_names
            sheets = {s: xls.parse(s) for s in sheet_names}

        sheet_options = ["⬇️ Select a sheet"] + sheet_names
        selected_sheet = st.selectbox("Select a sheet to analyze", options=sheet_options, index=0)

        if selected_sheet != "⬇️ Select a sheet":
            df = sheets[selected_sheet]

            expected_cols = ['X', 'Y', 'Z', 'T(motor state)', 'Motor State']
            missing = [col for col in expected_cols if col not in df.columns]
            if missing:
                st.warning(f"Missing columns: {missing}")
            else:
                df_processed = pd.DataFrame({
                    't': pd.to_datetime(df['T(motor state)'], errors='coerce'),
                    'x': df['X'],
                    'y': df['Y'],
                    'z': df['Z'],
                    'motor_state': df['Motor State']
                }).dropna(subset=['t', 'x', 'y', 'z', 'motor_state'])

                df_processed.sort_values('t', inplace=True)

                # Step 1: OFF/IDLE ranges for motor_state 0 or 1
                off_idle = df_processed[df_processed['motor_state'].isin([0,1])]
                limits = {
                    axis: {
                        'min': off_idle[axis].min(),
                        'max': off_idle[axis].max()
                    } for axis in ['x','y','z']
                }

                st.info("⚙️ OFF/IDLE vibration ranges:")
                for axis in ['x','y','z']:
                    st.write(f"{axis.upper()}: {limits[axis]['min']:.4f} to {limits[axis]['max']:.4f}")

                # Step 2: Filter out data within OFF/IDLE ranges
                outside_off_idle = df_processed[
                    ~(
                        (df_processed['x'] >= limits['x']['min']) & (df_processed['x'] <= limits['x']['max']) &
                        (df_processed['y'] >= limits['y']['min']) & (df_processed['y'] <= limits['y']['max']) &
                        (df_processed['z'] >= limits['z']['min']) & (df_processed['z'] <= limits['z']['max'])
                    )
                ]

                # Step 3: Keep only motor_state == 3 (strict ON)
                motor_on = outside_off_idle[outside_off_idle['motor_state'] == 3]

                if motor_on.empty:
                    st.warning("⚠️ No ON-state data found after filtering.")
                else:
                    thresholds = {
                        axis: {
                            'warning': motor_on[axis].quantile(0.85),
                            'error': motor_on[axis].quantile(0.95)
                        } for axis in ['x','y','z']
                    }

                    st.subheader(f"🎯 Thresholds (Motor ON, filtered) - Sheet: {selected_sheet}")
                    for axis in ['x','y','z']:
                        col1, col2 = st.columns(2)
                        col1.metric(f"{axis.upper()} - 85% Warning", f"{thresholds[axis]['warning']:.4f}")
                        col2.metric(f"{axis.upper()} - 95% Error", f"{thresholds[axis]['error']:.4f}")

                    st.subheader("📉 Vibration Plot (Motor ON, filtered)")
                    fig = px.line(motor_on, x='t', y=['x','y','z'], labels={'value': 'Vibration', 't': 'Timestamp'})
                    st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.error(f"❌ Error: {e}")
else:
    st.info("📂 Upload a CSV or Excel file to begin.")
