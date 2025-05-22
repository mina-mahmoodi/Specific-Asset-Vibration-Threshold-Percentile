import streamlit as st
import pandas as pd
import plotly.express as px

# Page setup
st.set_page_config(page_title="Vibration Threshold Calculator", layout="wide")
st.title("📈 Vibration Warning & Error Threshold Calculator")

# Upload
uploaded_file = st.file_uploader("Upload your vibration data (.csv or .xlsx)", type=["csv", "xlsx"])

if uploaded_file:
    try:
        # Detect file type and load sheet names
        if uploaded_file.name.endswith(".csv"):
            sheets = {"CSV Data": pd.read_csv(uploaded_file)}
        else:
            xls = pd.ExcelFile(uploaded_file)
            sheets = {sheet: xls.parse(sheet) for sheet in xls.sheet_names}

        # Create dropdown with "Select a sheet" on top
        sheet_names = list(sheets.keys())
        selected_sheet = st.selectbox("Select a sheet to analyze", ["⬇️ Select a sheet"] + sheet_names)

        # Only proceed if a valid sheet is selected
        if selected_sheet != "⬇️ Select a sheet":
            df = sheets[selected_sheet]

            expected_columns = ['X', 'Y', 'Z', 'T(X)', 'T(Y)', 'T(Z)', 'T(motor state)', 'Motor State']
            missing_cols = [col for col in expected_columns if col not in df.columns]

            if missing_cols:
                st.warning(f"❌ Missing columns in sheet '{selected_sheet}': {missing_cols}")
            else:
                # Prepare DataFrame
                df_processed = pd.DataFrame({
                    't': df['T(motor state)'],
                    'x': df['X'],
                    'y': df['Y'],
                    'z': df['Z'],
                    'motor_state': df['Motor State']
                })

                df_processed.dropna(subset=['t', 'x', 'y', 'z'], inplace=True)
                df_processed['motor_state'].fillna(3, inplace=True)

                # Fill missing dates with motor state 3
                df_all_dates = pd.DataFrame({'t': pd.date_range(start=df_processed['t'].min(), end=df_processed['t'].max())})
                df_all_dates['t'] = pd.to_datetime(df_all_dates['t'])
                df_processed['t'] = pd.to_datetime(df_processed['t'])

                df_merged = df_all_dates.merge(df_processed, on='t', how='left')
                df_merged['motor_state'].fillna(3, inplace=True)

                df_on = df_merged[df_merged['motor_state'] == 3]

                if df_on.empty:
                    st.warning("⚠️ No motor ON data in this sheet.")
                else:
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
