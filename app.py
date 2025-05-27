else:
    # Motor state columns not found, assume all motor ON
    st.warning(
        f"⚠️ Motor state columns not found or incomplete in '{uploaded_file.name}' sheet '{selected_sheet}'. "
        "Assuming all motor states are ON and using all non-zero data."
    )

    # Combine axis data into one DataFrame by inner join on timestamp
    df_merged = df_x.merge(df_y, on='t', how='inner').merge(df_z, on='t', how='inner')

    # Remove rows with zero or missing vibration values
    df_merged = df_merged.dropna(subset=['x', 'y', 'z'])
    df_merged = df_merged[(df_merged[['x', 'y', 'z']] != 0).all(axis=1)]

    if df_merged.empty:
        st.warning(
            f"⚠️ No usable non-zero vibration data found in '{uploaded_file.name}' sheet '{selected_sheet}' after filtering."
        )
        continue

    df_use = df_merged
