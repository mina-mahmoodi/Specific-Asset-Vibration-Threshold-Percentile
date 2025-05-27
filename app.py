import streamlit as st
import pandas as pd
import plotly.express as px
import math

st.set_page_config(page_title="Vibration Threshold Calculator", layout="wide")
st.title("📈 Vibration Warning & Error Threshold Calculator")

uploaded_files = st.file_uploader("Upload your vibration data files (.csv or .xlsx)", type=["csv", "xlsx"], accept_multiple_files=True)

if uploaded_files:
    # We'll combine all data from multiple files into one dataframe
    all_dfs = []

    for uploaded_file in uploaded_files:
        try:
            if uploaded_file.name.endswith(".csv"):
                df = pd.read_csv(uploaded_file)
                sheets = {"CSV Data": df}
                sheet_names = ["CSV Data"]
            else:
                xls = pd.ExcelFile(uploaded_file)
                sheet_names = xls.sheet_names
                sheets = {sheet_name: None for sheet_name in sheet_names}

            selected_sheet = st.selectbox(f"Select sheet to analyze from {uploaded_file.name}", ["⬇️ Select a sheet"] + sheet_names, key=uploaded_file.name)

            if selected_sheet != "⬇️ Select a sheet":
                if sheets[selected_sheet] is None and uploaded_file.name.endswith(".xlsx"):
                    sheets[selected_sheet] = pd.read_excel(uploaded_file, sheet_name=selected_sheet)
                df = sheets[selected_sheet]

                expected_columns = ['X', 'Y', 'Z', 'T(X)', 'T(Y)', 'T(Z)']
                optional_columns = ['T(motor state)', 'Motor State']
                all_columns = expected_columns + optional_columns
                missing_cols = [col for col in expected_columns if col not in df.columns]

                if missing_cols:
                    st.warning(f"❗ Missing required columns in '{uploaded_file.name}' sheet '{selected_sheet}': {missing_cols}")
                    continue

                # Parse timestamps
                df['T(X)'] = pd.to_datetime(df['T(X)'], errors='coerce')
                df['T(Y)'] = pd.to_datetime(df['T(Y)'], errors='coerce')
                df['T(Z)'] = pd.to_datetime(df['T(Z)'], errors='coerce')

                motor_state_available = all(col in df.columns for col in optional_columns)
                if motor_state_available:
                    df['T(motor state)'] = pd.to_datetime(df['T(motor state)'], errors='coerce')

                # Extract axis data
                df_x = df[['T(X)', 'X']].rename(columns={'T(X)': 't', 'X': 'x'}).dropna()
                df_y = df[['T(Y)', 'Y']].rename(columns={'T(Y)': 't', 'Y': 'y'}).dropna()
                df_z = df[['T(Z)', 'Z']].rename(columns={'T(Z)': 't', 'Z': 'z'}).dropna()

                if motor_state_available:
                    df_motor = df[['T(motor state)', 'Motor State']].rename(columns={'T(motor state)': 't', 'Motor State': 'motor_state'}).dropna()
                    df_combined = pd.merge_asof(df_motor.sort_values('t'), df_x.sort_values('t'), on='t', direction='nearest')
                    df_combined = pd.merge_asof(df_combined.sort_values('t'), df_y.sort_values('t'), on='t', direction='nearest')
                    df_combined = pd.merge_asof(df_combined.sort_values('t'), df_z.sort_values('t'), on='t', direction='nearest')
                    df_combined.dropna(subset=['x', 'y', 'z', 'motor_state'], inplace=True)
                    df_combined = df_combined[(df_combined[['x', 'y', 'z']] != 0).all(axis=1)]
                    df_on = df_combined[df_combined['motor_state'] == 3].copy()

                    if df_on.empty:
                        st.warning(f"⚠️ No motor ON data in '{uploaded_file.name}' sheet '{selected_sheet}'. Using all non-zero data regardless of motor state.")
                        df_use = df_combined
                    else:
                        st.success(f"✅ Motor ON data found in '{uploaded_file.name}' sheet '{selected_sheet}'. Thresholds based on motor ON data.")
                        df_use = df_on

                else:
                    df_combined = pd.merge_asof(df_x.sort_values('t'), df_y.sort_values('t'), on='t', direction='nearest')
                    df_combined = pd.merge_asof(df_combined.sort_values('t'), df_z.sort_values('t'), on='t', direction='nearest')
                    df_combined.dropna(subset=['x', 'y', 'z'], inplace=True)
                    df_combined = df_combined[(df_combined[['x', 'y', 'z']] != 0).all(axis=1)]
                    df_use = df_combined
                    st.warning(f"⚠️ Motor state data not found in '{uploaded_file.name}' sheet '{selected_sheet}'. Thresholds based on all available non-zero data.")

                if df_use.empty:
                    st.warning(f"⚠️ No usable vibration data found after filtering in '{uploaded_file.name}' sheet '{selected_sheet}'. Skipping.")
                    continue
                
                # Append to all_dfs for combined processing later
                all_dfs.append(df_use)

        except Exception as e:
            st.error(f"❌ Error processing '{uploaded_file.name}': {e}")

    if all_dfs:
        # Combine data from all files and sheets
        combined_df = pd.concat(all_dfs).sort_values('t').reset_index(drop=True)

        # Calculate thresholds on combined data
        thresholds = {
            axis: {
                'warning': math.ceil(combined_df[axis].quantile(0.85) * 100) / 100,
                'error': math.ceil(combined_df[axis].quantile(0.95) * 100) / 100
            } for axis in ['x', 'y', 'z']
        }

        st.subheader("🎯 Calculated Thresholds (Combined Data)")

        for axis in ['x', 'y', 'z']:
            col1, col2 = st.columns(2)
            col1.metric(f"{axis.upper()} - 85% Warning", f"{thresholds[axis]['warning']:.2f}")
            col2.metric(f"{axis.upper()} - 95% Error", f"{thresholds[axis]['error']:.2f}")

        selected_axis = st.selectbox("📌 Select axis to display", ['x', 'y', 'z'])

        df_plot = combined_df.sort_values('t')
        max_points = 5000
        if len(df_plot) > max_points:
            df_plot = df_plot.iloc[::len(df_plot) // max_points]

        st.subheader("📉 Vibration Plot (Combined Data)")
        fig = px.line(df_plot, x='t', y=selected_axis,
                      labels={selected_axis: f'{selected_axis.upper()} Vibration', 't': 'Timestamp'},
                      title=f"{selected_axis.upper()} Axis Vibration with Thresholds")

        fig.add_hline(y=thresholds[selected_axis]['warning'], line_dash="dash", line_color="orange",
                      annotation_text="85% Warning", annotation_position="top left")
        fig.add_hline(y=thresholds[selected_axis]['error'], line_dash="dot", line_color="red",
                      annotation_text="95% Error", annotation_position="top left")

        st.plotly_chart(fig, use_container_width=True)

    else:
        st.warning("⚠️ No usable data found in uploaded files after filtering.")
else:
    st.info("📂 Upload one or more CSV or Excel files to begin.")
