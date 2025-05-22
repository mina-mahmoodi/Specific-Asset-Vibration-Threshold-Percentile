import streamlit as st
import pandas as pd
import plotly.express as px

# Page setup
st.set_page_config(page_title="Vibration Threshold Calculator", layout="wide")
st.title("📈 Vibration Warning & Error Threshold Calculator")

# Upload section
uploaded_file = st.file_uploader("Upload your vibration data (.csv or .xlsx)", type=["csv", "xlsx"])

if uploaded_file:
    try:
        # Load file
        if uploaded_file.name.endswith(".csv"):
            df = pd.read_csv(uploaded_file)
            sheets = {"CSV Data": df}
            sheet_names = ["CSV Data"]
        else:
            xls = pd.ExcelFile(uploaded_file)
            sheet_names = xls.sheet_names
            sheets = {sheet: xls.parse(sheet) for sheet in sheet_names}

        # Dropdown with default placeholder on top
        sheet_options = ["⬇️ Select a sheet"] + sheet_names
        selected_sheet = st.selectbox("Select a sheet to analyze", options=sheet_options, index=0)

        # Proceed only if a valid sheet is selected
        if selected_sheet != "⬇️ Select a sheet":
            df = sheets[selected_sheet]

            # Validate columns
            expected_cols = ['X', 'Y', 'Z', 'T(X)', 'T(Y)', 'T(Z)', 'T(motor state)', 'Motor State']
            missing_cols = [col for col in expected_cols if col not in df.columns]

            if missing_cols:
                st.warning(f"Missing columns in sheet '{selected_sheet}': {missing_cols}")
            else:
                # Format DataFrame
                df_processed = pd.DataFrame({
                    't': pd.to_datetime(df['T(motor state)'], errors='coerce'),
                    'x': df['X'],
                    'y': df['Y'],
                    'z': df['Z'],
                    'motor_state': df['Motor State']
                }).dropna(subset=['t', 'x', 'y', 'z'])

                df_processed.sort_values('t', inplace=True)

                # Step 1: Identify timestamps with motor_state != 3
                non_on_mask = df_processed['motor_state'].notna() & (df_processed['motor_state'] != 3)
                non_on_times = df_processed.loc[non_on_mask, 't']

                # Step 2: Filter ON-state data
                if non_on_times.empty:
                    df_on = df_processed.copy()
                    comment = "No OFF-state found. Assuming all data is ON."
                else:
                    df_on = df_processed[~df_processed['t'].isin(non_on_times)].copy()
                    df_on = df_on[df_on['motor_state'].isna() | (df_on['motor_state'] == 3)]
                    comment = f"Filtered out {len(non_on_times)} rows with known OFF/IDLE states."

                # Step 3: Continue if valid ON data exists
                if df_on.empty:
                    st.warning("⚠️ No valid ON-state data available after filtering.")
                else:
                    st.success(comment)

                    # Calculate thresholds
                    thresholds = {
                        axis: {
                            'warning': df_on[axis].quantile(0.85),
                            'error': df_on[axis].quantile(0.95)
                        } for axis in ['x', 'y', 'z']
                    }

                    # Display metrics
                    st.subheader(f"🎯 Thresholds (Motor ON) - Sheet: {selected_sheet}")
                    for axis in ['x', 'y', 'z']:
                        col1, col2 = st.columns(2)
                        col1.metric(f"{axis.upper()} - 85% Warning", f"{thresholds[axis]['warning']:.4f}")
                        col2.metric(f"{axis.upper()} - 95% Error", f"{thresholds[axis]['error']:.4f}")

                    # Plot
                    st.subheader("📉 Vibration Plot (Motor ON only)")
                    fig = px.line(df_on, x='t', y=['x', 'y', 'z'], labels={'value': 'Vibration', 't': 'Timestamp'})
                    st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.error(f"❌ Error: {e}")

else:
    st.info("📂 Upload a CSV or Excel file to begin.")
