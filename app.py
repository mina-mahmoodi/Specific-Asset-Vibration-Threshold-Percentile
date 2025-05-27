import streamlit as st
import pandas as pd
import plotly.express as px
import math

st.set_page_config(page_title="Vibration Threshold Calculator", layout="wide")
st.title("📈 Vibration Warning & Error Threshold Calculator")

uploaded_files = st.file_uploader(
    "Upload your vibration data files (.csv or .xlsx). You can select multiple files.",
    type=["csv", "xlsx"], accept_multiple_files=True)

if uploaded_files:
    # Dict to hold sheet names and dfs across files
    all_sheets = {}
    sheet_options = []

    # Load sheets from all files
    for file in uploaded_files:
        if file.name.endswith(".csv"):
            df = pd.read_csv(file)
            key = f"{file.name} - CSV Data"
            all_sheets[key] = df
            sheet_options.append(key)
        else:
            xls = pd.ExcelFile(file)
            for sheet_name in xls.sheet_names:
                key = f"{file.name} - {sheet_name}"
                all_sheets[key] = None  # lazy load
                sheet_options.append(key)

    selected_sheet = st.selectbox("⬇️ Select a sheet to analyze", ["⬇️ Select a sheet"] + sheet_options)

    if selected_sheet != "⬇️ Select a sheet":
        # Lazy load sheet if Excel
        if all_sheets[selected_sheet] is None:
            # Extract filename and sheetname
            filename, sheetname = selected_sheet.split(" - ", 1)
            for file in uploaded_files:
                if file.name == filename and filename.endswith(".xlsx"):
                    all_sheets[selected_sheet] = pd.read_excel(file, sheet_name=sheetname)
                    break

        df = all_sheets[selected_sheet]

        # Expected and optional columns
        expected_columns = ['X', 'Y', 'Z', 'T(X)', 'T(Y)', 'T(Z)']
        optional_columns = ['T(motor state)', 'Motor State']

        missing_cols = [col for col in expected_columns if col not in df.columns]
        if missing_cols:
            st.warning(f"❗ Missing required columns in sheet '{selected_sheet}': {missing_cols}")
        else:
            # Convert timestamps to datetime
            df['T(X)'] = pd.to_datetime(df['T(X)'], errors='coerce')
            df['T(Y)'] = pd.to_datetime(df['T(Y)'], errors='coerce')
            df['T(Z)'] = pd.to_datetime(df['T(Z)'], errors='coerce')

            motor_state_available = all(col in df.columns for col in optional_columns)
            if motor_state_available:
                df['T(motor state)'] = pd.to_datetime(df['T(motor state)'], errors='coerce')

            # Show data range
            if df['T(X)'].notna().any():
                min_date = df['T(X)'].min()
                max_date = df['T(X)'].max()
                duration = max_date - min_date
                st.markdown(f"🕒 **Data range in T(X)**: {min_date} → {max_date} ({duration})")

            # Create axis DataFrames
            df_x = df[['T(X)', 'X']].rename(columns={'T(X)': 't', 'X': 'x'}).dropna()
            df_y = df[['T(Y)', 'Y']].rename(columns={'T(Y)': 't', 'Y': 'y'}).dropna()
            df_z = df[['T(Z)', 'Z']].rename(columns={'T(Z)': 't', 'Z': 'z'}).dropna()

            # Make sure all 't' columns are datetime
            df_x['t'] = pd.to_datetime(df_x['t'], errors='coerce')
            df_y['t'] = pd.to_datetime(df_y['t'], errors='coerce')
            df_z['t'] = pd.to_datetime(df_z['t'], errors='coerce')

            if motor_state_available:
                df_motor = df[['T(motor state)', 'Motor State']].rename(columns={'T(motor state)': 't', 'Motor State': 'motor_state'}).dropna()
                df_motor['t'] = pd.to_datetime(df_motor['t'], errors='coerce')

                # Merge all on time using merge_asof (nearest)
                df_combined = pd.merge_asof(df_motor.sort_values('t'), df_x.sort_values('t'), on='t', direction='nearest')
                df_combined = pd.merge_asof(df_combined.sort_values('t'), df_y.sort_values('t'), on='t', direction='nearest')
                df_combined = pd.merge_asof(df_combined.sort_values('t'), df_z.sort_values('t'), on='t', direction='nearest')

                # Drop missing & zero values
                df_combined.dropna(subset=['x', 'y', 'z', 'motor_state'], inplace=True)
                df_combined = df_combined[(df_combined[['x', 'y', 'z']] != 0).all(axis=1)]

                # Filter where motor_state == 3 (motor ON)
                df_use = df_combined[df_combined['motor_state'] == 3].copy()

                if df_use.empty:
                    st.warning("⚠️ No motor ON data after filtering. Using all data regardless of motor state.")
                    # Fallback to combined without motor filter
                    df_use = df_combined.copy()
            else:
                # No motor state, merge x,y,z only
                df_combined = pd.merge_asof(df_x.sort_values('t'), df_y.sort_values('t'), on='t', direction='nearest')
                df_combined = pd.merge_asof(df_combined.sort_values('t'), df_z.sort_values('t'), on='t', direction='nearest')
                df_combined.dropna(subset=['x', 'y', 'z'], inplace=True)
                df_combined = df_combined[(df_combined[['x', 'y', 'z']] != 0).all(axis=1)]
                df_use = df_combined.copy()
                st.warning("⚠️ Motor state data not found. Thresholds based on all non-zero data.")

            if not df_use.empty:
                # Calculate thresholds
                thresholds = {
                    axis: {
                        'warning': math.ceil(df_use[axis].quantile(0.85) * 100) / 100,
                        'error': math.ceil(df_use[axis].quantile(0.95) * 100) / 100
                    } for axis in ['x', 'y', 'z']
                }

                st.subheader("🎯 Calculated Thresholds")
                for axis in ['x', 'y', 'z']:
                    col1, col2 = st.columns(2)
                    col1.metric(f"{axis.upper()} - 85% Warning", f"{thresholds[axis]['warning']:.2f}")
                    col2.metric(f"{axis.upper()} - 95% Error", f"{thresholds[axis]['error']:.2f}")

                selected_axis = st.selectbox("📌 Select axis to display", ['x', 'y', 'z'])
                df_plot = df_use.sort_values('t')

                max_points = 5000
                if len(df_plot) > max_points:
                    df_plot = df_plot.iloc[::len(df_plot) // max_points]

                st.subheader("📉 Vibration Plot")
                fig = px.line(
                    df_plot,
                    x='t',
                    y=selected_axis,
                    labels={selected_axis: f'{selected_axis.upper()} Vibration', 't': 'Timestamp'},
                    title=f"{selected_axis.upper()} Axis Vibration with Thresholds"
                )

                fig.add_hline(y=thresholds[selected_axis]['warning'], line_dash="dash", line_color="orange",
                              annotation_text="85% Warning", annotation_position="top left")
                fig.add_hline(y=thresholds[selected_axis]['error'], line_dash="dot", line_color="red",
                              annotation_text="95% Error", annotation_position="top left")

                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("⚠️ No usable vibration data available after filtering.")
else:
    st.info("📂 Upload one or more CSV or Excel files to begin.")
