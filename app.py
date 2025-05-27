import streamlit as st
import pandas as pd
import plotly.express as px
import math

st.set_page_config(page_title="Vibration Threshold Calculator", layout="wide")
st.title("📈 Vibration Warning & Error Threshold Calculator")

uploaded_files = st.file_uploader(
    "Upload vibration data files (.csv or .xlsx)", type=["csv", "xlsx"], accept_multiple_files=True
)

if uploaded_files:
    all_dfs = []
    sheet_selections = {}

    # Ask user to select sheet for each uploaded Excel file
    for uploaded_file in uploaded_files:
        try:
            if uploaded_file.name.endswith(".csv"):
                sheet_selections[uploaded_file.name] = "CSV Data"
            else:
                xls = pd.ExcelFile(uploaded_file)
                sheet_names = xls.sheet_names
                sheet_selections[uploaded_file.name] = st.selectbox(
                    f"Select sheet from {uploaded_file.name}",
                    options=["-- Select a sheet --"] + sheet_names,
                    key=uploaded_file.name
                )
        except Exception as e:
            st.error(f"Error reading {uploaded_file.name}: {e}")

    ready_to_process = all(
        (sheet_selections.get(fname) and sheet_selections[fname] != "-- Select a sheet --")
        for fname in sheet_selections
    ) if sheet_selections else False

    if ready_to_process:
        for uploaded_file in uploaded_files:
            selected_sheet = sheet_selections.get(uploaded_file.name)
            if not selected_sheet or selected_sheet == "-- Select a sheet --":
                continue

            try:
                if uploaded_file.name.endswith(".csv"):
                    df = pd.read_csv(uploaded_file)
                else:
                    df = pd.read_excel(uploaded_file, sheet_name=selected_sheet)

                required_cols = ['X', 'Y', 'Z', 'T(X)', 'T(Y)', 'T(Z)']
                missing_cols = [c for c in required_cols if c not in df.columns]
                if missing_cols:
                    st.warning(
                        f"❗ Missing required columns in '{uploaded_file.name}' sheet '{selected_sheet}': {missing_cols}"
                    )
                    continue

                for col in ['T(X)', 'T(Y)', 'T(Z)']:
                    df[col] = pd.to_datetime(df[col], errors='coerce')

                df_x = df[['T(X)', 'X']].rename(columns={'T(X)': 't', 'X': 'x'}).dropna()
                df_y = df[['T(Y)', 'Y']].rename(columns={'T(Y)': 't', 'Y': 'y'}).dropna()
                df_z = df[['T(Z)', 'Z']].rename(columns={'T(Z)': 't', 'Z': 'z'}).dropna()

                motor_state_cols = [col for col in ['T(motor state)', 'Motor State'] if col in df.columns]
                motor_state_available = len(motor_state_cols) == 2

                if motor_state_available:
                    df['T(motor state)'] = pd.to_datetime(df['T(motor state)'], errors='coerce')
                    df_motor = df[['T(motor state)', 'Motor State']].rename(
                        columns={'T(motor state)': 't', 'Motor State': 'motor_state'}
                    ).dropna()

                    df_combined = pd.merge_asof(
                        df_motor.sort_values('t'),
                        df_x.sort_values('t'),
                        on='t',
                        direction='nearest'
                    )
                    df_combined = pd.merge_asof(
                        df_combined.sort_values('t'),
                        df_y.sort_values('t'),
                        on='t',
                        direction='nearest'
                    )
                    df_combined = pd.merge_asof(
                        df_combined.sort_values('t'),
                        df_z.sort_values('t'),
                        on='t',
                        direction='nearest'
                    )

                    df_combined.dropna(subset=['x', 'y', 'z', 'motor_state'], inplace=True)
                    df_combined = df_combined[(df_combined[['x', 'y', 'z']] != 0).all(axis=1)]

                    df_on = df_combined[df_combined['motor_state'] == 3]

                    if df_on.empty:
                        st.warning(
                            f"⚠️ No motor ON data in '{uploaded_file.name}' sheet '{selected_sheet}'. "
                            "Assuming all states are ON and using all non-zero data."
                        )
                        df_use = df_combined
                    else:
                        st.success(
                            f"✅ Motor ON data found in '{uploaded_file.name}' sheet '{selected_sheet}'. "
                            "Calculating thresholds based on motor ON data."
                        )
                        df_use = df_on

                else:
                    st.warning(
                        f"⚠️ Motor state columns not found or incomplete in '{uploaded_file.name}' sheet '{selected_sheet}'. "
                        "Assuming all motor states are ON and using all non-zero data."
                    )

                    # Merge axis data directly on exact timestamp
                    df_combined = df_x.merge(df_y, on='t', how='inner').merge(df_z, on='t', how='inner')
                    df_combined = df_combined.dropna(subset=['x', 'y', 'z'])
                    df_combined = df_combined[(df_combined[['x', 'y', 'z']] != 0).all(axis=1)]

                    if df_combined.empty:
                        st.warning(
                            f"⚠️ No usable non-zero vibration data found in '{uploaded_file.name}' sheet '{selected_sheet}' after filtering."
                        )
                        continue

                    df_use = df_combined

                if df_use.empty:
                    st.warning(
                        f"⚠️ No usable vibration data after filtering in '{uploaded_file.name}' sheet '{selected_sheet}'. Skipping."
                    )
                    continue

                all_dfs.append(df_use)

            except Exception as e:
                st.error(f"❌ Error processing '{uploaded_file.name}' sheet '{selected_sheet}': {e}")

        if all_dfs:
            combined_df = pd.concat(all_dfs).sort_values('t').reset_index(drop=True)

            thresholds = {
                axis: {
                    'warning': math.ceil(combined_df[axis].quantile(0.85) * 100) / 100,
                    'error': math.ceil(combined_df[axis].quantile(0.95) * 100) / 100,
                }
                for axis in ['x', 'y', 'z']
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
            fig = px.line(
                df_plot,
                x='t',
                y=selected_axis,
                labels={selected_axis: f"{selected_axis.upper()} Vibration", 't': 'Timestamp'},
                title=f"{selected_axis.upper()} Axis Vibration with Thresholds",
            )
            fig.add_hline(
                y=thresholds[selected_axis]['warning'],
                line_dash="dash",
                line_color="orange",
                annotation_text="85% Warning",
                annotation_position="top left",
            )
            fig.add_hline(
                y=thresholds[selected_axis]['error'],
                line_dash="dot",
                line_color="red",
                annotation_text="95% Error",
                annotation_position="top left",
            )

            st.plotly_chart(fig, use_container_width=True)

        else:
            st.warning("⚠️ No usable data found in uploaded files after filtering.")
    else:
        st.info("⏳ Please select sheets for all uploaded Excel files to proceed.")
else:
    st.info("📂 Upload one or more CSV or Excel files to begin.")
