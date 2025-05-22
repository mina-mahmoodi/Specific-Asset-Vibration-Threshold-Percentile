import streamlit as st
import pandas as pd
import plotly.express as px

# Page setup
st.set_page_config(page_title="Vibration Threshold Calculator", layout="wide")
st.title("📈 Vibration Warning & Error Threshold Calculator")

# Upload file
uploaded_file = st.file_uploader("Upload your vibration data (.csv or .xlsx)", type=["csv", "xlsx"])

if uploaded_file:
    try:
        # Load sheets
        if uploaded_file.name.endswith(".csv"):
            sheets = {"Sheet1": pd.read_csv(uploaded_file)}
        else:
            xls = pd.ExcelFile(uploaded_file)
            sheets = {sheet_name: xls.parse(sheet_name) for sheet_name in xls.sheet_names}

        # Let user select the sheet
        sheet_selected = st.selectbox("Select a sheet to analyze", list(sheets.keys()))
        df = sheets[sheet_selected]

        # Check required columns exist (any of the required timestamp columns must exist)
        required_columns = ['X', 'Y', 'Z', 'T(X)', 'T(Y)', 'T(Z)', 'T(motor state)', 'Motor State']
        missing_cols = [col for col in ['X', 'Y', 'Z'] if col not in df.columns]
        if missing_cols:
            st.error(f"Missing required vibration columns: {missing_cols}")
        else:
            # Rename and select vibration timestamp (prefer T(X), else T(Y), else T(Z))
            # We assume vibration timestamps come from one of these three timestamp columns
            if 'T(X)' in df.columns:
                df['t'] = pd.to_datetime(df['T(X)'])
            elif 'T(Y)' in df.columns:
                df['t'] = pd.to_datetime(df['T(Y)'])
            elif 'T(Z)' in df.columns:
                df['t'] = pd.to_datetime(df['T(Z)'])
            else:
                st.error("No vibration timestamp columns (T(X), T(Y), T(Z)) found.")
                st.stop()

            # Extract motor state timestamps and motor states if present
            if 'T(motor state)' in df.columns and 'Motor State' in df.columns:
                motor_state_df = df[['T(motor state)', 'Motor State']].dropna()
                motor_state_df['T(motor state)'] = pd.to_datetime(motor_state_df['T(motor state)'])
                motor_state_df = motor_state_df.drop_duplicates(subset=['T(motor state)'])
            else:
                # If no motor state data, assume motor state = 3 for all vibration times
                motor_state_df = pd.DataFrame(columns=['T(motor state)', 'Motor State'])

            # Create dataframe of all vibration timestamps and merge with motor states
            vibration_df = df[['t', 'X', 'Y', 'Z']].copy()
            vibration_df.rename(columns={'X':'x', 'Y':'y', 'Z':'z'}, inplace=True)

            if not motor_state_df.empty:
                # Merge vibration timestamps with motor states on timestamp, nearest match within a tolerance
                # We use merge_asof to match nearest motor state timestamp <= vibration timestamp
                motor_state_df = motor_state_df.sort_values('T(motor state)')
                vibration_df = vibration_df.sort_values('t')

                merged_df = pd.merge_asof(
                    vibration_df,
                    motor_state_df.rename(columns={'T(motor state)': 't', 'Motor State': 'motor_state'}),
                    on='t',
                    direction='backward',
                    tolerance=pd.Timedelta('1min')  # adjust tolerance if needed
                )

                # For vibration timestamps with no motor state match, assign motor_state = 3
                merged_df['motor_state'] = merged_df['motor_state'].fillna(3)
            else:
                # No motor state data at all, assign motor_state = 3
                merged_df = vibration_df.copy()
                merged_df['motor_state'] = 3

            # Filter data where motor_state == 3 (motor ON)
            df_on = merged_df[merged_df['motor_state'] == 3]

            if df_on.empty:
                st.warning("⚠️ No motor ON data found in the selected sheet.")
            else:
                # Calculate thresholds
                thresholds = {
                    axis: {
                        'warning': df_on[axis].quantile(0.85),
                        'error': df_on[axis].quantile(0.95)
                    } for axis in ['x', 'y', 'z']
                }

                # Display thresholds
                st.subheader(f"🎯 Vibration Thresholds (Motor ON) - Sheet: {sheet_selected}")
                for axis in ['x', 'y', 'z']:
                    col1, col2 = st.columns(2)
                    col1.metric(f"{axis.upper()} - 85% Warning", f"{thresholds[axis]['warning']:.4f}")
                    col2.metric(f"{axis.upper()} - 95% Error", f"{thresholds[axis]['error']:.4f}")

                # Plot vibration data over time
                st.subheader("📉 Vibration Plot (Motor ON only)")
                fig = px.line(df_on, x='t', y=['x', 'y', 'z'],
                              labels={'value': 'Vibration', 't': 'Timestamp'},
                              title="Vibration Over Time (Motor State = 3)")
                st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.error(f"❌ Error: {e}")

else:
    st.info("📂 Upload a CSV or Excel file to begin.")
