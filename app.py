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
        # Detect file type and load data
        if uploaded_file.name.endswith(".csv"):
            df = pd.read_csv(uploaded_file)
            sheet_names = ["CSV Data"]
            selected_sheet = "CSV Data"
            sheets = {"CSV Data": df}
        else:
            xls = pd.ExcelFile(uploaded_file)
            sheet_names = xls.sheet_names
            selected_sheet = st.selectbox("Select a sheet to analyze", sheet_names)
            sheets = {sheet_name: xls.parse(sheet_name) for sheet_name in sheet_names}

        if selected_sheet:
            df = sheets[selected_sheet]

            expected_columns = ['X', 'Y', 'Z', 'T(X)', 'T(Y)', 'T(Z)', 'T(motor state)', 'Motor State']
            missing_cols = [col for col in expected_columns if col not in df.columns]

            if missing_cols:
                st.warning(f"Missing columns in sheet '{selected_sheet}': {missing_cols}")
            else:
                # Rename and select necessary columns
                df_processed = pd.DataFrame({
                    't': df['T(motor state)'],
                    'x': df['X'],
                    'y': df['Y'],
                    'z': df['Z'],
                    'motor_state': df['Motor State']
                })

                df_processed.dropna(subset=['t', 'x', 'y', 'z', 'motor_state'], inplace=True)

                # Assume all dates not in motor_state as motor_state = 3
                # Since here each row is a data point, and motor_state is per row,
                # we treat missing motor_state as 3 (you can adjust if needed)
                df_processed['motor_state'] = df_processed['motor_state'].fillna(3)

                # Filter motor_state == 3 (motor ON)
                df_on = df_processed[df_processed['motor_state'] == 3].copy()

                if df_on.empty:
                    st.warning("⚠️ No motor ON data in this sheet.")
                else:
                    # Thresholds: 85th for warning, 95th for error
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
