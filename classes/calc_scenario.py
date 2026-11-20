""""""
import pandas as pd


def build_scenario_parameters(
        scenario_names,
        options_new_units,
        dict_mt_travel_bias
    ):

    df = pd.DataFrame()
    
    # Variable parameters:
    # Start with all unit combinations.
    df['scenario_name'] = pd.Series(scenario_names, dtype=str)
    df['scenario_geoprocess_name'] = pd.Series(scenario_names, dtype=str)
    df['new_mt_units'] = pd.Series(options_new_units, dtype=object)
    # Add in proportion 
    list_of_dfs = []
    for label_b, b in dict_mt_travel_bias.items():    
        df_b = df.copy()
        df_b['mt_travel_bias_minutes'] = b
        df_b['scenario_geoprocess_name'] = (
            df_b['scenario_geoprocess_name'] + label_b)
        df_b['scenario_name'] = df_b['scenario_name'] + label_b
        list_of_dfs.append(df_b)
    
    df = pd.concat(list_of_dfs, axis='rows').sort_index(
        kind='stable', ignore_index=True)
    return df


def load_scenario_parameters(p):
    # Use converters to turn units column from strings to lists.
    # Assumes that no postcodes contain spaces!
    converters = {
        'new_mt_units': lambda x: (
            x.replace("'", '').replace(',', '')[1:-1].split()),
    }
    df_scen_full = pd.read_csv(p, converters=converters)
    return df_scen_full

    
def load_geo_cohort_data(p, p2, cols_geo=None, cols_results=None):
    """
    Function to load in cohort outcome and admissions data:"""
    df_base = pd.concat(
        (pd.read_csv(p, index_col='LSOA', usecols=cols_geo),
         pd.read_csv(p2, index_col='LSOA', usecols=cols_results)),
        axis='columns'
    )
    return df_base


def gather_data(df_base, df_taunworc):
    """Function to gather data from the two dataframes:"""
    cols_same = ['area_lower', 'Admissions_2025_Est']
    
    cols_to_gather = [
        'nearest_ivt_unit',
        'transfer_unit',
        'transfer_required',
        'drip_ship_mt_time',
        'drip_ship_mt_travel_time',
        'drip_ship_mt_travel_time_with_delay',
        'admissions_mt',
        'transfers_mt',
        'admissions_mt_transferloss0!67',
        'transfers_mt_transferloss0!67',
        'admissions_weighted_drip_ship_mrs_0-2',
        'admissions_weighted_lvo_drip_ship_ivt_mt_mrs_0-2',
        'admissions_weighted_drip_ship_mrs_0-2_transferloss0!67',
        'admissions_weighted_lvo_drip_ship_ivt_mt_mrs_0-2_transferloss0!67',
        'drip_ship_mrs_0-2',
        'lvo_drip_ship_ivt_mt_mrs_0-2',
        'drip_ship_mrs_0-2_transferloss0!67',
        'lvo_drip_ship_ivt_mt_mrs_0-2_transferloss0!67'
    ]
    
    rename_dict_base = dict([(c, f'{c}_base') for c in cols_to_gather])
    rename_dict_taunworc = dict([(c, f'{c}_taunworc') for c in cols_to_gather])
    
    df = pd.concat(
        (df_base[cols_same],
         df_base[cols_to_gather].rename(columns=rename_dict_base),
         df_taunworc[cols_to_gather].rename(columns=rename_dict_taunworc)),
        axis='columns'
    )
    return df


def calculate_changes(df):
    """Function to calculate changes from base:"""
    cols_for_change = [
        'drip_ship_mt_time',
        'drip_ship_mt_travel_time',
        'drip_ship_mt_travel_time_with_delay',
        'admissions_mt',
        'transfers_mt',
        'admissions_mt_transferloss0!67',
        'transfers_mt_transferloss0!67',
        'admissions_weighted_drip_ship_mrs_0-2',
        'admissions_weighted_lvo_drip_ship_ivt_mt_mrs_0-2',
        'admissions_weighted_drip_ship_mrs_0-2_transferloss0!67',
        'admissions_weighted_lvo_drip_ship_ivt_mt_mrs_0-2_transferloss0!67',
        'drip_ship_mrs_0-2',
        'lvo_drip_ship_ivt_mt_mrs_0-2',
        'drip_ship_mrs_0-2_transferloss0!67',
        'lvo_drip_ship_ivt_mt_mrs_0-2_transferloss0!67'
    ]
    
    for col in cols_for_change:
        df[f'change_in_{col}'] = df[f'{col}_taunworc'] - df[f'{col}_base']
        r = 1 if 'time' in col else 5
        df[f'change_in_{col}'] = df[f'change_in_{col}'].round(r)
    
    df['changed'] = (
        (df['nearest_ivt_unit_base'] != df['nearest_ivt_unit_taunworc']) |
        (df['transfer_unit_base'] != df['transfer_unit_taunworc'])
    )
    # df['change_in_lvo_drip_ship_ivt_mt_mrs_0-2'] != 0
    return df