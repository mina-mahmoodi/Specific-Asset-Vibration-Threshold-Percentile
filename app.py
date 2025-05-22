import streamlit as st
import pandas as pd

st.set_page_config(page_title="Vibration Threshold Calculator", layout="wide")
st.title("📈 Vibration Warning & Error Threshold Calculator")

uploaded_file = st.file_uploader("Upload an Excel or CSV file", type=["xlsx", "xls", "csv"])

if uploaded_file:
    # Load Excel or CSV
    if uploaded_file.name.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
        sheet_selected = None
    else:
        xls = pd.ExcelFile(uploaded_file)
        sheet_selected = st.selectbox("Select a sheet", xls.sheet_names)
        df = pd.read_excel(uploaded_file, sheet_name=sheet_selected)

    # Rename known columns
    col_map = {
        'X': 'x', 'Y': 'y', 'Z': 'z',
        'T(X)': 't_x', 'T(Y)': 't_y', 'T(Z)': 't_z',
        'T(motor state)': 't_motor',
        'Motor State': 'motor_state'
    }
    df = df.rename(columns={col: col_map[col] for col in col_map if col in df.columns})

    required_cols = ['x', 'y', 'z']
    if not all(col in df.columns for col in required_cols):
        st.error(f"Missing required columns: {required_cols}")
    else:
        # Handle missing motor state column
        if 'motor_state' not in df.columns:
            df['motor_state'] = 3
        else:
            df['motor_state'] = df['motor_state'].fillna(3)

        # Filter for rows where motor was ON
        df_on = df[df['motor_state'] == 3]

        if df_on.empty:
            st.warning("No vibration data found while motor was ON (state = 3).")
        else:
            st.subheader(f"📊 Vibration Thresholds (Sheet: {sheet_selected if sheet_selected else 'CSV'})")

            # Calculate thresholds
            thresholds = {}
            for axis in ['x', 'y', 'z']:
                warning = df_on[axis].quantile(0.85)
                error = df_on[axis].quantile(0.95)
                thresholds[axis.upper()] = {
                    'Warning Threshold (85%)': warning,
                    'Error Threshold (95%)': error
                }

            # Display results
            result_df = pd.DataFrame(thresholds).T
            st.dataframe(result_df.style.format("{:.2f}"))

            # Optional: show raw data preview
            if st.checkbox("Show raw vibration data (first 100 rows)"):
                st.dataframe(df_on[['x', 'y', 'z']].head(100))

            # Optional: show vibration line chart
            if st.checkbox("Show simple vibration line chart"):
                st.line_chart(df_on[['x', 'y', 'z']].reset_index(drop=True))
