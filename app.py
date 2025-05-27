import streamlit as st
import pandas as pd
import plotly.express as px
import math

st.set_page_config(page_title="Vibration Threshold Calculator", layout="wide")
st.title("📈 Vibration Warning & Error Threshold Calculator")

uploaded_file = st.file_uploader("Upload your vibration data (.csv or .xlsx)", type=["csv", "xlsx"])

if uploaded_file:
    try:
        # Read file
        if uploaded_file.name.endswith(".csv"):
            df = pd.read_csv(uploaded_file)
            sheets = {"CSV Data": df}
            sheet_names = ["CSV Data"]
        else:
            xls = pd.ExcelFile(uploaded_file)
            sheet_names = xls.sheet_names
            sheets = {sheet_name: None for sheet_name in sheet_names}

        selected_sheet = st.selectbox("⬇️ Select a sheet to analyze", ["⬇️ Select a sheet"] + sheet_names)

        if selected_sheet != "⬇️ Select a sheet":
            if sheets[selected_sheet] is None and uploaded_file.name.endswith(".xlsx"):
                sheets[selected_sheet] = pd.read_excel(uploaded_file, sheet_name=selected_sheet)
            df = sheets[selected_sheet]

            # Check which columns exist
            base_cols = ['X', 'Y', 'Z', 'T(X)', 'T(Y)', 'T(Z)']
            optional_cols = ['T(motor state)', 'Motor State']
            missing_cols = [col for col in base_cols if col not in df.columns]

            if missing_cols:
                st.warning(f"❗ Missing required columns in sheet '{selected_sheet}': {missing_cols}")
            else:
                # Convert timestamps
                df['T(X)'] = pd.to_datetime(df['T(X)'], errors='coerce')
                df['T(Y)'] = pd.to_datetime(df['T(Y)'], errors='coerce')
                df['T(Z)'] = pd.to_datetime(df['T(Z)'], errors='coerce')

                # Show date range and duration
                if df['T(X)'].notna().any():
                    min_date = df['T(X)'].min()
                    max_date = df['T(X)'].max()
                    duration = max_date - min_date
                    st.markdown(f"🕒 **Data range in T(X)**: {min_date} → {max_date} ({duration})")

                # Create vibration dataframes
                df_x = df[['T(X)', 'X']].rename(columns={'T(X)': 't', 'X': 'x'}).dropna()
                df_y = df[['T(Y)', 'Y']].rename(columns={'T(Y)': 't', 'Y': 'y'}).dropna()
                df_z = df[['T(Z)', 'Z']].rename(columns={'T(Z)': 't', 'Z': 'z'}).dropna()

                # Motor state logic (optional)
                has_motor = all(col in df.columns for col in optional_cols)
                if has_motor:
                    df_motor = df[['T(motor state)', 'Motor State']].rename(
                        columns={'T(motor state)': 't', 'Motor State': 'motor_state'}).dropna()
                    df_combined = pd.merge_asof(df_motor.sort_values('t'), df_x.sort_values('t'), on='t', direction='nearest')
                    df_combined = pd.merge_asof(df_combined.sort_values('t'), df_y.sort_values('t'), on='t', direction='nearest')
                    df_combined = pd.merge_asof(df_combined.sort_values('t'), df_z.sort_values('t'), on='t', direction='nearest')
                    df_combined.dropna(subset=['x', 'y', 'z', 'motor_state'], inplace=True)
                    df_combined = df_combined[(df_combined[['x', 'y', 'z']] != 0).all(axis=1)]
                    df_use = df_combined[df_combined['motor_state'] == 3]
                    if df_use.empty:
                        st.warning("⚠️ No motor ON data in this sheet after alignment and filtering.")
                        st.stop()
                else:
                    st.info("ℹ️ No motor state data found. Using full vibration data (zero values excluded).")
                    # Merge X, Y, Z on nearest timestamps without motor
                    df_temp = df_x.merge(df_y, on='t', how='inner').merge(df_z, on='t', how='inner')
                    df_use = df_temp[(df_temp[['x', 'y', 'z']] != 0).all(axis=1)]

                if df_use.empty:
                    st.warning("⚠️ No usable vibration data found.")
                    st.stop()

                # Threshold calculation
                thresholds = {
                    axis: {
                        'warning': math.ceil(df_use[axis].quantile(0.85) * 100) / 100,
                        'error': math.ceil(df_use[axis].quantile(0.95) * 100) / 100
                    } for axis in ['x', 'y', 'z']
                }

                st.subheader(f"🎯 Thresholds - Sheet: {selected_sheet}")
                for axis in ['x', 'y', 'z']:
                    col1, col2 = st.columns(2)
                    col1.metric(f"{axis.upper()} - 85% Warning", f"{thresholds[axis]['warning']:.2f}")
                    col2.metric(f"{axis.upper()} - 95% Error", f"{thresholds[axis]['error']:.2f}")

                selected_axis = st.selectbox("📌 Select axis to display", ['x', 'y', 'z'])

                # Downsample if needed
                max_points = 5000
                df_plot = df_use.sort_values('t')
                if len(df_plot) > max_points:
                    df_plot = df_plot.iloc[::len(df_plot)//max_points]

                # Plotting
                st.subheader("📉 Vibration Plot")
                fig = px.line(df_plot, x='t', y=selected_axis,
                              labels={selected_axis: f'{selected_axis.upper()} Vibration', 't': 'Timestamp'},
                              title=f"{selected_axis.upper()} Axis Vibration with Thresholds")

                fig.add_hline(y=thresholds[selected_axis]['warning'], line_dash="dash", line_color="orange",
                              annotation_text="85% Warning", annotation_position="top left")
                fig.add_hline(y=thresholds[selected_axis]['error'], line_dash="dot", line_color="red",
                              annotation_text="95% Error", annotation_position="top left")

                st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.error(f"❌ Error: {e}")
else:
    st.info("📂 Upload a CSV or Excel file to begin.")
