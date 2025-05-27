# Motor state logic (optional)
has_motor = all(col in df.columns for col in optional_cols)
if has_motor:
    # Convert motor timestamp to datetime (critical!)
    df['T(motor state)'] = pd.to_datetime(df['T(motor state)'], errors='coerce')

    df_motor = df[['T(motor state)', 'Motor State']].rename(
        columns={'T(motor state)': 't', 'Motor State': 'motor_state'}).dropna()
    
    # Ensure all other timestamps are datetime
    df_x['t'] = pd.to_datetime(df_x['t'], errors='coerce')
    df_y['t'] = pd.to_datetime(df_y['t'], errors='coerce')
    df_z['t'] = pd.to_datetime(df_z['t'], errors='coerce')

    df_combined = pd.merge_asof(df_motor.sort_values('t'), df_x.sort_values('t'), on='t', direction='nearest')
    df_combined = pd.merge_asof(df_combined.sort_values('t'), df_y.sort_values('t'), on='t', direction='nearest')
    df_combined = pd.merge_asof(df_combined.sort_values('t'), df_z.sort_values('t'), on='t', direction='nearest')
    
    df_combined.dropna(subset=['x', 'y', 'z', 'motor_state'], inplace=True)
    df_combined = df_combined[(df_combined[['x', 'y', 'z']] != 0).all(axis=1)]
    df_use = df_combined[df_combined['motor_state'] == 3]

    if df_use.empty:
        st.warning("⚠️ No motor ON data in this sheet after alignment and filtering.")
        st.stop()
