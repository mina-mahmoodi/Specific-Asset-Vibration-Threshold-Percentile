import streamlit as st
import pandas as pd
import plotly.express as px
import math
from io import StringIO

st.set_page_config(page_title="Vibration Threshold Calculator", layout="wide")
st.title("📈 Vibration Warning & Error Threshold Calculator")

uploaded_files = st.file_uploader(
    "Upload vibration data files (.csv or .xlsx)", type=["csv", "xlsx"], accept_multiple_files=True
)

if uploaded_files:
    all_dfs = []
    sheet_selections = {}

    for uploaded_file in uploaded_files:
        if uploaded_file.name.endswith(".csv"):
            sheet_selections[uploaded_file.name] = "CSV Data"
        else:
            try:
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
        sheet_selections.get(fname) and sheet_selections[fname] != "-- Select a sheet --"
        for fname in sheet_selections
    )

    if ready_to_process:
        for uploaded_file in uploaded_files:
            sheet = sheet_selections[uploaded_file.name]

            try:
                if uploaded_file.name.endswith(".csv"):
                    df = pd.read_csv(uploaded_file)
                else:
                    df = pd.read_excel(uploaded_file, sheet_name=sheet)

                if not all(col in df.columns for col in ['T(X)', 'T(Y)', 'T(Z)', 'X', 'Y', 'Z']):
                    st.warning(f"Missing required columns in {uploaded_file.name} / {sheet}")
                    continue

                for col in ['T(X)', 'T(Y)', 'T(Z)']:
                    df[col] = pd.to_datetime(df[col], errors='coerce')

                df_use = df.dropna(subset=['T(X)', 'T(Y)', 'T(Z)'])
                df_use = df_use[(df_use[['X', 'Y', 'Z']] != 0).all(axis=1)]

                row_count = len(df_use)
                if row_count == 0:
                    st.warning(f"⚠️ No usable vibration data after filtering in '{uploaded_file.name}' sheet '{sheet}'. Skipping.")
                    continue

                st.success(f"✅ Using {row_count} rows of non-zero vibration data from '{uploaded_file.name}' sheet '{sheet}'.")

                df_use = df_use.rename(columns={'T(X)': 't', 'X': 'x', 'Y': 'y', 'Z': 'z'})
                df_use = df_use[['t', 'x', 'y', 'z']]
                all_dfs.append(df_use)

            except Exception as e:
                st.error(f"❌ Error processing {uploaded_file.name}: {e}")

        if all_dfs:
            combined_df = pd.concat(all_dfs).sort_values('t').reset_index(drop=True)

            start_time = combined_df['t'].min()
            end_time = combined_df['t'].max()
            st.markdown(f"🕒 **Dataset Time Period:** From {start_time.strftime('%Y-%m-%d %H:%M:%S')} to {end_time.strftime('%Y-%m-%d %H:%M:%S')}")

            thresholds = {
                axis: {
                    'warning': math.ceil(combined_df[axis].quantile(0.85) * 100) / 100,
                    'error': math.ceil(combined_df[axis].quantile(0.95) * 100) / 100,
                }
                for axis in ['x', 'y', 'z']
            }

            st.subheader("🎯 Calculated Thresholds")
            for axis in ['x', 'y', 'z']:
                col1, col2 = st.columns(2)
                col1.metric(f"{axis.upper()} - 85% Warning", f"{thresholds[axis]['warning']:.2f}")
                col2.metric(f"{axis.upper()} - 95% Error", f"{thresholds[axis]['error']:.2f}")

            # Create and offer download for the thresholds
            threshold_df = pd.DataFrame([
                {'Axis': axis.upper(), '85% Warning': thresholds[axis]['warning'], '95% Error': thresholds[axis]['error']}
                for axis in ['x', 'y', 'z']
            ])
            csv_output = threshold_df.to_csv(index=False)
            st.download_button("⬇️ Download Thresholds as CSV", csv_output, file_name="vibration_thresholds.csv", mime="text/csv")

            selected_axis = st.selectbox("📌 Select axis to display", ['x', 'y', 'z'])

            df_plot = combined_df.sort_values('t')
            max_points = 5000
            if len(df_plot) > max_points:
                df_plot = df_plot.iloc[::len(df_plot) // max_points]

            st.subheader("📉 Vibration Plot")
            fig = px.line(
                df_plot,
                x='t',
                y=selected_axis,
                title=f"{selected_axis.upper()} Vibration with Thresholds",
                labels={'t': 'Timestamp', selected_axis: f"{selected_axis.upper()} Amplitude"},
            )
            fig.add_hline(y=thresholds[selected_axis]['warning'], line_dash="dash", line_color="orange",
                          annotation_text="85% Warning", annotation_position="top left")
            fig.add_hline(y=thresholds[selected_axis]['error'], line_dash="dot", line_color="red",
                          annotation_text="95% Error", annotation_position="top left")

            st.plotly_chart(fig, use_container_width=True)

        else:
            st.warning("⚠️ No usable data found in uploaded files after filtering.")
    else:
        st.info("📄 Please select a sheet for each uploaded file.")
else:
    st.info("📂 Upload one or more CSV or Excel files to begin.")
