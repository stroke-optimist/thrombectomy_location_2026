""""""
def calculate_extra_bits(df, scenarios):
    """
    Note that we're missing some of these things calculated for LSOA-level data:
    
    'change_in_drip_ship_mt_travel_time',
    'change_in_drip_ship_mrs_0-2',
    'change_in_lvo_drip_ship_ivt_mt_mrs_0-2',
    'change_in_drip_ship_mrs_0-2_transferloss0!67',
    'change_in_lvo_drip_ship_ivt_mt_mrs_0-2_transferloss0!67',
    'changed'

    Could add these in later. TO DO.
    """
    # Changes between scenarios
    # First unit admissions doesn't depend on transfer rate:
    c = 'Admissions_2025_Est'
    df['change_in_first_admissions'] = (
        df[f'{c}_taunworc'].fillna(0.0) - df[f'{c}_base'].fillna(0.0)
    ).round(1)

    for s in ['base', 'taunworc']:
        try:
            df[f'transfer_required_{s}'] = (
                df[f'nearest_ivt_unit_{s}'] != df[f'transfer_unit_{s}'])
        except KeyError:
            pass

    def get_cols_transfer_rates(df, start, scenarios):
        cols = [c for c in df.columns if c.startswith(start)]
        for s in scenarios:
            cols = list(set([c.replace(f'_{s}', '') for c in cols]))
        return cols
    
    cols = get_cols_transfer_rates(df, 'admissions_mt', scenarios)
    for c in cols:
        df[f'change_in_{c}'] = (
            df[f'{c}_taunworc'].fillna(0.0) -
            df[f'{c}_base'].fillna(0.0)
        ).round(1)

    cols = get_cols_transfer_rates(
        df, 'admissions_weighted_lvo_drip_ship_ivt_mt_mrs_0-2', scenarios)
    for c in cols:
        df[f'change_in_{c}'] = (
            df[f'{c}_taunworc'].fillna(0.0) -
            df[f'{c}_base'].fillna(0.0)
        ).round(5)

    if 'transfer_unit_base' in df.columns:
        # Find MT units with a change in total admissions
        c = 'change_in_admissions_weighted_lvo_drip_ship_ivt_mt_mrs_0-2'
        mt_units_with_change = sorted(list(set(df.loc[
            df[c] != 0,
            ['transfer_unit_base', 'transfer_unit_taunworc']
            ].values.flatten())))
        
        # Indicate whether each MT unit's admissions changed from any IVT unit
        df['mt_unit_admissions_changed_by_any_ivt_unit'] = (
            df['transfer_unit_base'].isin(mt_units_with_change) |
            df['transfer_unit_taunworc'].isin(mt_units_with_change) 
        )
    return df