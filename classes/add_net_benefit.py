import pandas as pd

def add_net_benefit(df, prop_lvo=0.3):
    """
    Add net benefit column to the dataframe.

    Parameters:
    df (pd.DataFrame): DataFrame containing the data.
    prop_lvo (float): Proportion of large vessel occlusion (LVO) cases.
        prop_nlvo is calculated as 1 - prop_lvo.

    Returns:
    pd.DataFrame: DataFrame with added net benefit columns.
    """

    prop_nlvo = 1 - prop_lvo

    # Utility

    df['drip_ship_utility_shift'] = (
        (df['nlvo_drip_ship_ivt_utility_shift'] * prop_nlvo) +
        (df['lvo_drip_ship_ivt_mt_utility_shift'] * prop_lvo))

    df['mothership_utility_shift'] = (
        (df['nlvo_mothership_ivt_utility_shift'] * prop_nlvo) +
        (df['lvo_mothership_ivt_mt_utility_shift'] * prop_lvo))

    # Get mRS 0-2 improvements
    df['nlvo_drip_ship_ivt_improvement_over_no_treatment'] = \
        df['nlvo_drip_ship_ivt_mrs_0-2'] - df['nlvo_no_treatment_mrs_0-2']
    df['lvo_drip_ship_ivt_mt_improvement_over_no_treatment'] = \
        df['lvo_drip_ship_ivt_mt_mrs_0-2'] - df['lvo_no_treatment_mrs_0-2']

    # Get proportions mRS 0-2 for each scenario
    df['no_treatment_mrs_0-2'] = (
        (df['nlvo_no_treatment_mrs_0-2'] * prop_nlvo) +
        (df['lvo_no_treatment_mrs_0-2'] * prop_lvo))

    df['drip_ship_mrs_0-2'] = (
        (df['nlvo_drip_ship_ivt_mrs_0-2'] * prop_nlvo) +
        (df['lvo_drip_ship_ivt_mt_mrs_0-2'] * prop_lvo))

    df['drip_ship_mrs_0-2_improvement_over_no_treatment'] = \
        df['drip_ship_mrs_0-2'] - df['no_treatment_mrs_0-2']

    df['mothership_mrs_0-2'] = (
        (df['nlvo_mothership_ivt_mrs_0-2'] * prop_nlvo) +
        (df['lvo_mothership_ivt_mt_mrs_0-2'] * prop_lvo))

    df['mothership_mrs_0-2_improvement_over_no_treatment'] = \
        df['mothership_mrs_0-2'] - df['no_treatment_mrs_0-2']

    return df
