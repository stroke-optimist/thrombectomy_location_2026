import pandas as pd

def add_net_benefit(df, prop_lvo=0.3):
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


    # Utility and proportions mRS 0-2 for each scenario
    for s in ['utility_shift', 'mrs_0-2']:
        # Assume everyone can have MT:
        df[f'drip_ship_{s}'] = (
            (df[f'nlvo_drip_ship_ivt_{s}'] * prop_nlvo) +
            (df[f'lvo_drip_ship_ivt_mt_{s}'] * prop_lvo)
        )

        df[f'mothership_{s}'] = (
            (df[f'nlvo_mothership_ivt_{s}'] * prop_nlvo) +
            (df[f'lvo_mothership_ivt_mt_{s}'] * prop_lvo)
        )
    df['no_treatment_mrs_0-2'] = (
        (df['nlvo_no_treatment_mrs_0-2'] * prop_nlvo) +
        (df['lvo_no_treatment_mrs_0-2'] * prop_lvo)
    )

    # Get mRS 0-2 improvements
    # Whole cohort:
    for s in ['drip_ship', 'mothership']:
        df[f'{s}_mrs_0-2_improvement_over_no_treatment'] = \
            df[f'{s}_mrs_0-2'] - df['no_treatment_mrs_0-2']

    # By occlusion-treatment pair:
    for (o, t) in [('nlvo', 'ivt'), ('lvo', 'ivt'), ('lvo', 'ivt_mt')]:
        df[f'{o}_drip_ship_{t}_improvement_over_no_treatment'] = (
            df[f'{o}_drip_ship_{t}_mrs_0-2'] -
            df[f'{o}_no_treatment_mrs_0-2']
        )

    return df


def add_lossy_net_benefit(df, prop_lvo=0.3, prop_lvo_ds_mt=1.0):
    """
    # Accounting for not all drip-ship patients getting a transfer.

    prop_lvo_ds_mt is proportion that get transfer.
    """
    if prop_lvo_ds_mt == 1.0:
        return df
    else:
        pass

    cols_start = df.columns

    prop_nlvo = 1 - prop_lvo

    p = f'{prop_lvo_ds_mt}'.replace('.', '!')  # no . in column names.

    m_ds = df['transfer_required'] == True

    for s in ['utility_shift', 'mrs_0-2']:
        # Scale for patients who don't get a transfer for MT:
        n = f'drip_ship_transfer{p}_{s}'
        df[n] = df[f'drip_ship_{s}'].copy()
        df.loc[m_ds, n] = (
            (df.loc[m_ds, f'nlvo_drip_ship_ivt_{s}'] * prop_nlvo) +
            (df.loc[m_ds, f'lvo_drip_ship_ivt_mt_{s}'] *
             prop_lvo * prop_lvo_ds_mt) +
            (df.loc[m_ds, f'lvo_drip_ship_ivt_{s}'] *
             prop_lvo * (1.0 - prop_lvo_ds_mt))
        )

    s = 'improvement_over_no_treatment'
    n = f'lvo_drip_ship_transfer{p}_ivt_mt_{s}'
    df[n] = df[f'lvo_drip_ship_ivt_mt_{s}'].copy()
    df.loc[m_ds, n] = (
        (df.loc[m_ds, f'lvo_drip_ship_ivt_mt_{s}'] * prop_lvo_ds_mt) +
        (df.loc[m_ds, f'lvo_drip_ship_ivt_{s}'] * (1.0 - prop_lvo_ds_mt))
    )

    cols_new = list(set(df.columns) - set(cols_start))
    df[cols_new] = df[cols_new].round(5)
    return df