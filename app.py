import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Vibration Threshold Calculator", layout="wide")
st.title("📈 Vibration Warning & Error Threshold Calculator")

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
            sheets = {sheet_name: None for sheet_name in sheet_names}

        selected_sheet = st.selectbox("⬇️ Select a sheet to analyze", ["⬇️ Select a sheet"] + sheet_names)

        if selected_sheet != "⬇️ Select a sheet":
            if sheets[selected_sheet] is None and uploaded_file.name.endswith(".xlsx"):
                sheets[selected_sheet] = pd.read_excel(uploaded_file, sheet_name=selected_sheet)
            df = sheets[selected_sheet]

            required_columns = ['X', 'Y', 'Z', 'T(X)', 'T(Y)', 'T(Z)', 'T(motor state)', 'Motor State']
            missing_cols = [col for col in required_columns if col not in df.columns]

            if missing_cols:
                st.warning(f"❗ Missing columns in sheet '{selected_sheet}': {missing_cols}")
            else:
                df_motor = pd.DataFrame({
                    't_motor': pd.to_datetime(df['T(motor state)']),
                    'motor_state': df['Motor State']
                }).dropna()

                df_motor = df_motor[df_motor['motor_state'] == 3].sort_values('t_motor')

                if df_motor.empty:
                    st.warning("⚠️ No motor ON data in this sheet.")
                else:
                    # Prepare vibration channels with time alignment
                    vib_channels = {}
                    for axis, t_col in zip(['x', 'y', 'z'], ['T(X)', 'T(Y)', 'T(Z)']):
                        df_axis = pd.DataFrame({
                            't': pd.to_datetime(df[t_col]),
                            axis: df[axis.upper()]
                        }).dropna().sort_values('t')
                        # As-of merge to find closest motor ON timestamp within ±30s
                        df_merged = pd.merge_asof(
                            df_axis, df_motor, left_on='t', right_on='t_motor',
                            direction='nearest', tolerance=pd.Timedelta(seconds=30)
                        )
                        # Keep only rows with motor_state==3 and non-zero vibration
                        df_valid = df_merged[df_merged['motor_state'] == 3]
                        df_valid = df_valid[df_valid[axis] != 0]
                        vib_channels[axis] = df_valid

                    if all(len(vib_channels[axis]) > 0 for axis in ['x', 'y', 'z']):
                        thresholds = {}
                        for axis in ['x', 'y', 'z']:
                            thresholds[axis] = {
                                'warning': vib_channels[axis][axis].quantile(0.85),
                                'error': vib_channels[axis][axis].quantile(0.95)
                            }

                        st.subheader(f"🎯 Thresholds (Motor ON)")
                        for axis in ['x', 'y', 'z']:
                            col1, col2 = st.columns(2)
                            col1.metric(f"{axis.upper()} - 85% Warning", f"{thresholds[axis]['warning']:.4f}")
                            col2.metric(f"{axis.upper()} - 95% Error", f"{thresholds[axis]['error']:.4f}")

                        # Plotting with sampling
                        st.subheader("📉 Vibration Plot (Motor ON only)")
                        max_points = 5000
                        for axis in ['x', 'y', 'z']:
                            df_plot = vib_channels[axis]
                            if len(df_plot) > max_points:
                                df_plot = df_plot.sort_values('t').iloc[::len(df_plot)//max_points]
                            fig = px.line(df_plot, x='t', y=axis, labels={'t': 'Timestamp', axis: 'Vibration'})
                            st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.warning("⚠️ Not enough valid vibration data aligned with motor ON periods.")

    except Exception as e:
        st.error(f"❌ Error: {e}")
else:
    st.info("📂 Upload a CSV or Excel file to begin.")
