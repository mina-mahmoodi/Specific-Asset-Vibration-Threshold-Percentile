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
        # Handle file loading
        if uploaded_file.name.endswith(".csv"):
            df = pd.read_csv(uploaded_file)
            sheets = {"CSV Data": df}
            sheet_names = ["CSV Data"]
        else:
            xls = pd.ExcelFile(uploaded_file)
            sheet_names = xls.sheet_names
            sheets = {sheet_name: None for sheet_name in sheet_names}  # Lazy load

        # Sheet selector with placeholder on top
        selected_sheet = st.selectbox("⬇️ Select a sheet to analyze", ["⬇️ Select a sheet"] + sheet_names)

        if selected_sheet != "⬇️ Select a sheet":
            # Load selected sheet lazily
            if sheets[selected_sheet] is None:
                if uploaded_file.name.endswith(".xlsx"):
                    sheets[selected_sheet] = pd.read_excel(uploaded_file, sheet_name=selected_sheet)
            df = sheets[selected_sheet]

            # Expected columns
            expected_columns = ['X', 'Y', 'Z', 'T(X)', 'T(Y)', 'T(Z)', 'T(motor state)', 'Motor State']
            missing_cols = [col for col in expected_columns if col not in df.columns]

            if missing_cols:
                st.warning(f"❗ Missing columns in sheet '{selected_sheet}': {missing_cols}")
            else:
                # Build initial DataFrame
                df_processed = pd.DataFrame({
                    't': pd.to_datetime(df['T(motor state)']),
                    'x': df['X'],
                    'y': df['Y'],
                    'z': df['Z'],
                    'motor_state': df['Motor State']
                }).dropna(subset=['t', 'x', 'y', 'z'])

                # Create full time index
                full_time = pd.date_range(start=df_processed['t'].min(), end=df_processed['t'].max(), freq='T')
                df_all = pd.DataFrame({'t': full_time})

                # Merge with actual data
                df_merged = df_all.merge(df_processed, on='t', how='left')

                # Assume missing motor state = 3
                df_merged['motor_state'] = df_merged['motor_state'].fillna(3)

                # Filter motor ON only
                df_on = df_merged[df_merged['motor_state'] == 3].copy()

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
