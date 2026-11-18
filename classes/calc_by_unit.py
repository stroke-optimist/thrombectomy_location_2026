""""""
import pandas as pd
import numpy as np


def gather_unit_combos(results_paths):
    # Only load in these columns with the chosen unit names:
    cols_unit_postcodes = ['nearest_ivt_unit', 'transfer_unit']
    cols_unit_postcodes = [f'{c}_{s}' for c in cols_unit_postcodes
                           for s in ['base', 'taunworc']]
    
    # For each file, gather the unique sets of units:
    list_of_dfs = []
    for k, p in results_paths.items():
        df = pd.read_csv(p, usecols=cols_unit_postcodes)
        df_unit_combos = df[cols_unit_postcodes].drop_duplicates(
            ignore_index=True)
        df_unit_combos[k] = 1
        list_of_dfs.append(df_unit_combos.copy())
    
    # Turn unit data into a DataFrame and remove duplicate entries:
    df_unit_combos = pd.concat(list_of_dfs, axis='rows', ignore_index=True)
    df_unit_combos = df_unit_combos.drop_duplicates(subset=cols_unit_postcodes,
                                                    ignore_index=True)
    # Convert tracking columns to integer:
    df_unit_combos = df_unit_combos.fillna(0).convert_dtypes()
    
    # Label unit combinations.
    # Use labels that start with '42' so they're not confused with
    # a standard range index.
    df_unit_combos['unit_combo'] = np.arange(len(df_unit_combos)) + 42000
    df_unit_combos = df_unit_combos.set_index('unit_combo')
    return df_unit_combos


def main_unit_combos(
        df,
        df_unit_combos,
        scenarios,
        col_admissions,
        cols_unit_postcodes,
        strings_tl,
        print_cols=False
    ):
    """Gather these separate functions into a main one:"""
    ### Set up column names
    # Gather columns present in the main results dataframes.
    # Gather columns by type and without tailing scenario names (`_base`, `_taunworc`):
    col_lsoa11nm = 'area_lower'
    cols_mt_admissions = ['admissions_mt']
    cols_transfer = ['transfers_mt']
    cols_time = ['drip_ship_mt_time',
                 'drip_ship_mt_travel_time',
                 'drip_ship_mt_travel_time_with_delay']
    cols_outcome = [
        'drip_ship_mrs_0-2',
        'lvo_drip_ship_ivt_mt_mrs_0-2',
    ]
    cols_admissions_weighted_outcomes = [
        'admissions_weighted_drip_ship_mrs_0-2',
        'admissions_weighted_lvo_drip_ship_ivt_mt_mrs_0-2',
    ]
    cols_change = ['change_in_drip_ship_mrs_0-2',
                   'change_in_lvo_drip_ship_ivt_mt_mrs_0-2']
    
    
    # Add columns affected by lossy transfer rate:
    def add_str_to_columns(cols, s_list):
        return [f'{c}{s}' for c in cols for s in s_list]
    
    cols_mt_admissions = add_str_to_columns(cols_mt_admissions, strings_tl)
    cols_transfer = add_str_to_columns(cols_transfer, strings_tl)
    cols_outcome = add_str_to_columns(cols_outcome, strings_tl)
    cols_admissions_weighted_outcomes = add_str_to_columns(
        cols_admissions_weighted_outcomes, strings_tl)
    # Final gather:
    cols_change += [
        'change_in_drip_ship_mt_time',
        'change_in_drip_ship_mt_travel_time',
        'change_in_drip_ship_mt_travel_time_with_delay',
        'changed'
    ]
    cols_shared = [col_lsoa11nm, col_admissions] + cols_change
    
    # Calculate unit-level data for each scenario:
    comparison_by_unit_combo_base = calculate_results_per_scenario(
        df,
        'base',
        df_unit_combos,
        cols_shared,
        col_admissions,
        cols_unit_postcodes,
        cols_outcome,
        cols_time,
        cols_admissions_weighted_outcomes,
        cols_mt_admissions,
        cols_transfer,
        print_cols
    )
    if print_cols:
        print('')
    else:
        pass
    comparison_by_unit_combo_taunworc = calculate_results_per_scenario(
        df,
        'taunworc',
        df_unit_combos,
        cols_shared,
        col_admissions,
        cols_unit_postcodes,
        cols_outcome,
        cols_time,
        cols_admissions_weighted_outcomes,
        cols_mt_admissions,
        cols_transfer,
        print_cols
    )
    
    
    # Gather and simplify info
    # Place all results in same dataframe:
    rename_base = dict([(c, f'{c}_base')
                        for c in comparison_by_unit_combo_base.columns])
    rename_taunworc = dict([(c, f'{c}_taunworc')
                           for c in comparison_by_unit_combo_taunworc.columns])
    
    comparison_by_unit_combo = pd.concat(
        (comparison_by_unit_combo_base.rename(columns=rename_base),
         comparison_by_unit_combo_taunworc.rename(columns=rename_taunworc)),
        axis='columns'
    ).sort_index()

    # Check that there is one entry for each combination of units:
    print('Unit combos as expected:',
          (len(comparison_by_unit_combo) ==
           len(comparison_by_unit_combo.index.unique()))
         )

    # Extra calculations for comparing scenarios:
    cols = comparison_by_unit_combo.columns.tolist()
    comparison_by_unit_combo = calculate_extra_bits(comparison_by_unit_combo,
                                                    scenarios)
    # Print new columns:
    new_cols = list(set(comparison_by_unit_combo.columns.tolist()) - set(cols))
    if print_cols:
        print('comparison_by_unit_combo:', new_cols)
    else:
        pass
    
    # Reorder columns:
    col_order = [
        'nearest_ivt_unit', 'transfer_unit', 'SSNAP name', 'Hospital_City',
        'SSNAP name_transfer_unit', 'Hospital_City_transfer_unit',
    ]
    col_order = [f'{c}_{s}' for c in col_order for s in ['base', 'taunworc']]
    col_order += [c for c in comparison_by_unit_combo.columns if c not in col_order]
    
    comparison_by_unit_combo = comparison_by_unit_combo[col_order]

    return comparison_by_unit_combo

    
def calculate_results_per_scenario(
        df,
        scenario,
        df_unit_combos,
        cols_shared,
        col_admissions,
        cols_unit_postcodes,
        cols_outcome,
        cols_time,
        cols_admissions_weighted_outcomes,
        cols_mt_admissions,
        cols_transfer,
        print_cols=False
    ):
    """
    Use the following function to run calculations separately for
    each scenario, otherwise it's difficult to see what's happening.
    """
    cols = (['unit_combo'] + cols_shared +
            [c for c in df.columns if c.endswith(scenario)])
    df_here = df[cols]
    rename_dict = dict([(c, c.replace(f'_{scenario}', ''))
                        for c in df_here.columns])
    df_here = df_here.rename(columns=rename_dict)

    # Link each first unit to its MT unit.
    # Only keep data for this scenario:
    cols_here = ['unit_combo'] + [c for c in df_unit_combos if scenario in c]
    df_unit_info = df_unit_combos[cols_here].set_index('unit_combo').copy()
    # Only keep combos in the data here:
    combos_here = df['unit_combo'].unique()
    df_unit_info = df_unit_info[df_unit_info.index.isin(combos_here)]
    # Rename columns to match data here:
    rename_dict = dict([(c, c.replace(f'_{scenario}', ''))
                        for c in df_unit_info.columns])
    df_unit_info = df_unit_info.rename(columns=rename_dict)
    
    # Sum admissions to each unit by scenario
    df_admissions = calculate_admissions_by_unit(
        df_here,
        [col_admissions] + cols_mt_admissions + cols_transfer
    )

    # Admissions-weighted outcomes:
    df_unit_outcomes = calculate_outcomes_by_unit(
        df_here,
        cols_admissions_weighted_outcomes,
        col_admissions
    )
    
    # Admissions-weighted travel times:
    df_unit_times = calculate_times_by_unit(
        df_here,
        cols_time,
        col_admissions
    )

    if print_cols:
        print(scenario)
        print('df_unit_info:', df_unit_info.columns)
        # display(df_unit_info)
        print('df_admissions:', df_admissions.columns)
        # display(df_admissions)
        print('df_unit_outcomes:', df_unit_outcomes.columns)
        # display(df_unit_outcomes)
        print('df_unit_times:', df_unit_times.columns)
        # display(df_unit_outcomes)
    else:
        pass
        
    # Gather all results:
    comparison_by_unit_combo = pd.concat(
        (df_unit_info, df_admissions, df_unit_outcomes, df_unit_times),
        axis='columns'
    )
    return comparison_by_unit_combo


def calculate_admissions_by_unit(
        df,
        cols_admissions
    ):
    """
    """
    df_admissions = (
        df[['unit_combo'] + cols_admissions].groupby('unit_combo').sum())
    
    df_admissions = df_admissions.fillna(0.0)
    df_admissions = df_admissions.round(1)
    return df_admissions


def calculate_outcomes_by_unit(
    df,  # by LSOA
    cols_admissions_weighted_outcomes,
    col_admissions
    ):
    """
    """
    # First sum by all patients:
    df_unit_outcomes = (
        df[['unit_combo', col_admissions] + cols_admissions_weighted_outcomes]
        .groupby('unit_combo').sum()
    )
    # Divide outcomes by the direct admissions to each unit:
    df_unit_outcomes[cols_admissions_weighted_outcomes] = (
        df_unit_outcomes[cols_admissions_weighted_outcomes]
            .div(df_unit_outcomes[col_admissions], axis='rows')
    )
    df_unit_outcomes = df_unit_outcomes.drop(col_admissions, axis='columns')
    df_unit_outcomes = df_unit_outcomes.round(5)
    return df_unit_outcomes

    
def calculate_times_by_unit(
    df,  # by LSOA
    cols_times,
    col_admissions
    ):
    """
    """
    # First sum by all patients:
    df_unit_times = df.copy()
    df_unit_times[cols_times] = df_unit_times[cols_times].multiply(
                                df_unit_times[col_admissions], axis='rows')

    df_unit_times = (
        df_unit_times[['unit_combo', col_admissions] + cols_times]
        .groupby('unit_combo').sum()
    )
    df_unit_times[cols_times] = df_unit_times[cols_times].div(
                                df_unit_times[col_admissions], axis='rows')

    df_unit_times = df_unit_times.drop(col_admissions, axis='columns')
    df_unit_times = df_unit_times.round(1)
    return df_unit_times


def calculate_extra_bits(df, scenarios):
    """
    Note that we're missing some of these things calculated for LSOA-level data:
    
    'change_in_drip_ship_mt_time',
    'change_in_drip_ship_mt_travel_time',
    'change_in_drip_ship_mt_travel_time_with_delay',
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


# Single unit:
def main_unit_single_all_unit_types(
        comparison_by_unit_combo,
        scenarios,
        col_admissions
    ):
    """Wrapper for main_unit_single()."""
    cols_unit = ['nearest_ivt_unit', 'transfer_unit']
    dict_by_unit = {}
    for s in ['base', 'taunworc']:
        cols_unit_here = [f'{c}_{s}' for c in cols_unit]
        for col_unit in cols_unit_here:
            df_here = main_unit_single(
                comparison_by_unit_combo,
                s,
                col_unit,
                col_admissions,
            )
            dict_by_unit[col_unit] = df_here.copy()
    
    # Combine scenarios.    
    # Keep the nearest IVT unit and transfer unit data separate
    # because they're not always the same pair between scenarios.
    comparison_by_nearest_ivt_unit = pd.concat(
        (dict_by_unit['nearest_ivt_unit_base'],
         dict_by_unit['nearest_ivt_unit_taunworc']),
        axis='columns'
    )
    comparison_by_transfer_unit = pd.concat(
        (dict_by_unit['transfer_unit_base'],
         dict_by_unit['transfer_unit_taunworc']),
        axis='columns'
    )
    
    comparison_by_nearest_ivt_unit = calculate_extra_bits(
        comparison_by_nearest_ivt_unit, scenarios)
    comparison_by_transfer_unit = calculate_extra_bits(
        comparison_by_transfer_unit, scenarios)
    return comparison_by_nearest_ivt_unit, comparison_by_transfer_unit


def main_unit_single(
        comparison_by_unit_combo,
        s,
        col_unit,
        col_admissions,
    ):
    """### Function to combine units

    Admissions can just be summed.
    
    Admission-weighted outcomes and travel times need to be weighted more carefully.
    """   
    # Set up columns:
    cols_scen = [c for c in comparison_by_unit_combo.columns if s in c]
    cols_adweight = [c for c in cols_scen if 'weighted' in c]
    cols_time_here = [c for c in cols_scen if 'drip_ship_mt_' in c]
    cols_ad = [c for c in cols_scen if
                   ((('dmissions' in c) | ('transfers_mt' in c)) &
                    (c not in cols_adweight))]
    col_ad = f'{col_admissions}_{s}'

    # Stroke unit info:
    if 'transfer' in col_unit:
        cols_this_unit = [f'SSNAP name_transfer_unit_{s}',
                          f'Hospital_City_transfer_unit_{s}']
    else:
        cols_this_unit = [f'SSNAP name_{s}', f'Hospital_City_{s}']
    df_units = (comparison_by_unit_combo[[col_unit] + cols_this_unit]
        .drop_duplicates(ignore_index=True))
    df_units = df_units.set_index(col_unit)

    df_ad = comparison_by_unit_combo[[col_unit] + cols_ad].copy()
    df_ad = df_ad.groupby(col_unit).sum()

    df_adweight = comparison_by_unit_combo[
        [col_unit, col_ad] + cols_adweight].copy()
    df_adweight = combine_units_admissions_weighted_outcomes(
        df_adweight,  # by unit, units may appear more than once
        cols_adweight,
        col_ad,
        col_unit
    )

    df_times = comparison_by_unit_combo[
        [col_unit, col_ad] + cols_time_here].copy()
    df_times = combine_units_average_times(
        df_times,  # by unit, units may appear more than once
        cols_time_here,
        col_ad,
        col_unit
    )

    df_here = pd.concat((df_units, df_ad, df_adweight, df_times),
                        axis='columns')
    return df_here


def combine_units_admissions_weighted_outcomes(
        df,  # by unit, units may appear more than once
        cols_admissions_weighted_outcomes,
        col_admissions,
        col_unit
    ):
    df = df.copy()
    df[cols_admissions_weighted_outcomes] = (
        df[cols_admissions_weighted_outcomes]
            .multiply(df[col_admissions], axis='rows')
    )
    cols = [col_unit, col_admissions] + cols_admissions_weighted_outcomes
    df_here = df[cols].groupby(col_unit).sum()
    # Divide outcomes by the direct admissions to each unit:
    df_here[cols_admissions_weighted_outcomes] = (
        df_here[cols_admissions_weighted_outcomes]
            .div(df_here[col_admissions], axis='rows')
    )
    df_here = df_here.drop(col_admissions, axis='columns')
    df_here = df_here.round(5)

    return df_here

def combine_units_average_times(
        df,  # by unit, units may appear more than once
        cols_time,
        col_admissions,
        col_unit
    ):
    df = df.copy()
    # Convert average time per patient to total time for all patients:
    df[cols_time] = df[cols_time].multiply(df[col_admissions], axis='rows')

    cols = [col_unit, col_admissions] + cols_time
    df_here = df[cols].groupby(col_unit).sum()

    # Divide total times by the total number of patients to each unit:
    df_here[cols_time] = df_here[cols_time].div(
        df_here[col_admissions], axis='rows')

    df_here = df_here.drop(col_admissions, axis='columns')
    df_here = df_here.round(1)

    return df_here