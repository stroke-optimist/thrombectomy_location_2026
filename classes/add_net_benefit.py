import pandas as pd

def add_net_benefit(df, prop_lvo=0.3, prop_lvo_ds_mt=1.0):
    """
    Add net benefit column to the dataframe.

    For drip-ship, calculate IVT&MT benefit assuming that loss is zero
    (everyone who needs MT gets a transfer), then scale down to account
    for loss (patients who would get MT from direct admission but do
    not receive a transfer to the MT unit).

    Parameters:
    df (pd.DataFrame): DataFrame containing the data.
    prop_lvo (float): Proportion of large vessel occlusion (LVO) cases.
        prop_nlvo is calculated as 1 - prop_lvo.
    prop_lvo_ds_mt (float): Proportion of LVO cases
        that are treated with MT in the drip and ship case. Ranges from
        0.0 (nobody gets MT after first travelling to local unit) to
        1.0 (everybody gets a transfer for MT).

    Returns:
    pd.DataFrame: DataFrame with added net benefit columns.
    """
    cols_start = df.columns

    prop_nlvo = 1 - prop_lvo
    m_ds = df['transfer_required'] == True
    outcome_columns = ['utility_shift', 'mrs_0-2',
                       'mrs_0-2_improvement_over_no_treatment']  # 'mrs_shift', 'utility'
    use_mt_only = 0

    df['no_treatment_mrs_0-2'] = (
        (df['nlvo_no_treatment_mrs_0-2'] * prop_nlvo) +
        (df['lvo_no_treatment_mrs_0-2'] * prop_lvo)
    )
    # Utility and proportions mRS 0-2 for each scenario
    for s in ['utility_shift', 'mrs_0-2']:
        # Assume everyone can have MT:
        n = f'drip_ship_{s}'
        df[n] = (
            (df[f'nlvo_drip_ship_ivt_{s}'] * prop_nlvo) +
            (df[f'lvo_drip_ship_ivt_mt_{s}'] * prop_lvo)
        )
        if prop_lvo_ds_mt != 1.0:
            # Scale for patients who don't get a transfer for MT:
            n = f'drip_ship_{s}_transferloss'
            df[n] = df[f'drip_ship_{s}'].copy()
            df.loc[m_ds, n] = (
                (df.loc[m_ds, f'nlvo_drip_ship_ivt_{s}'] * prop_nlvo) +
                (df.loc[m_ds, f'lvo_drip_ship_ivt_mt_{s}'] *
                 prop_lvo * prop_lvo_ds_mt) +
                (df.loc[m_ds, f'lvo_drip_ship_ivt_{s}'] *
                 prop_lvo * (1.0 - prop_lvo_ds_mt))
            )

        df[f'mothership_{s}'] = (
            (df[f'nlvo_mothership_ivt_{s}'] * prop_nlvo) +
            (df[f'lvo_mothership_ivt_mt_{s}'] * prop_lvo)
        )

    # Get mRS 0-2 improvements
    # Whole cohort:
    for s in ['drip_ship', 'mothership']:
        df[f'{s}_mrs_0-2_improvement_over_no_treatment'] = \
            df[f'{s}_mrs_0-2'] - df['no_treatment_mrs_0-2']
    if prop_lvo_ds_mt != 1.0:
        df[f'drip_ship_mrs_0-2_improvement_over_no_treatment_transferloss'] = (
            df[f'drip_ship_mrs_0-2_transferloss'] - df['no_treatment_mrs_0-2'])

    # By occlusion-treatment pair:
    for (o, t) in [('nlvo', 'ivt'), ('lvo', 'ivt'), ('lvo', 'ivt_mt')]:
        n = f'{o}_drip_ship_{t}_mrs_0-2_improvement_over_no_treatment'
        df[n] = (
            df[f'{o}_drip_ship_{t}_mrs_0-2'] -
            df[f'{o}_no_treatment_mrs_0-2']
        )

    if prop_lvo_ds_mt != 1.0:
        # Calculate results for mixed LVO cohort - some transferred
        # and receive MT, some only receive IVT.
        for s in ['mrs_0-2', 'mrs_0-2_improvement_over_no_treatment']:  # outcome_columns:
            # Start with all IVT+MT results, then for patients who need
            # a transfer, use a mix of IVT-only and IVT+MT.
            n = f'lvo_drip_ship_ivt_mt_{s}_transferloss'
            df[n] = df[f'lvo_drip_ship_ivt_mt_{s}'].copy()
            df.loc[m_ds, n] = (
                (df.loc[m_ds, f'lvo_drip_ship_ivt_mt_{s}'] * prop_lvo_ds_mt) +
                (df.loc[m_ds, f'lvo_drip_ship_ivt_{s}'] * (1.0 - prop_lvo_ds_mt))
            )
            if use_mt_only:
                # For patients who don't receive IVT, use a mix of 
                # MT-only and no-treatment results.
                n = f'lvo_drip_ship_mt_{s}_transferloss'
                df[n] = df[f'lvo_drip_ship_mt_{s}'].copy()
                df.loc[m_ds, n] = (
                    (df.loc[m_ds, f'lvo_drip_ship_mt_{s}'] * prop_lvo_ds_mt) +
                    (df.loc[m_ds, f'lvo_no_treatment_{s}'] * (1.0 - prop_lvo_ds_mt))
                )
            
    cols_new = list(set(df.columns) - set(cols_start))
    df[cols_new] = df[cols_new].round(5)
    return df


def add_mt_and_transfers(df, col_admissions, mt_rate, prop_lvo_ds_mt=1.0):
    """
    Calculate numbers of MT and transfers.

    Numbers of MT is just a simple scaling of all admissions.
    Numbers of transfers depend on the loss rate in the drip-and-ship
    case, and are zero when the first unit provides MT.
    """
    s = '' if prop_lvo_ds_mt == 1.0 else f'_transferloss'
    col_new_ad = f'admissions_mt{s}'
    col_new_tr = f'transfers_mt{s}'
    
    m = df['transfer_required']
    # Start with everybody receiving MT:
    df[col_new_ad] = df[col_admissions] * mt_rate
    # Account for drip-and-ship transfer loss:
    if prop_lvo_ds_mt != 1.0:
        df.loc[m, col_new_ad] *= prop_lvo_ds_mt

    # If the first unit offers MT, set transfers to zero:
    df[col_new_tr] = df[col_new_ad].copy()
    df.loc[~m, col_new_tr] = 0.0

    df[[col_new_ad, col_new_tr]] = df[[col_new_ad, col_new_tr]].round(3)
    return df


def add_admissions_weighted_outcomes(
            df, col_admissions, cols_outcome):
    """LSOA-level"""
    list_weighted_outcomes = []
    for col in cols_outcome:
        s = df[col] * df[col_admissions]
        s = s.rename(f'admissions_weighted_{col}')
        list_weighted_outcomes.append(s)

    df = pd.concat([df] + list_weighted_outcomes, axis='columns')
    df = df.round(5)
    return df