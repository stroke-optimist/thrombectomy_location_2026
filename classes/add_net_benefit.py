import pandas as pd
import numpy as np

from classes.geography_processing import Geoprocessing
from classes.model import Model
from classes.scenario import Scenario


def calculate_geo_and_outcomes(
        mt_travel_bias,
        new_mt_units,
    ):
    # Process geographic data (only needed when hospital data changes):
    geo = Geoprocessing(limit_to_england=True,
                        mt_travel_bias=mt_travel_bias,
                        new_mt_centres=new_mt_units)
    geo.run()
    geodata = geo.combined_data.copy().reset_index()
    
    # Set up scenario
    scenario = Scenario({
        'name': 'temporary_name',
        'limit_to_england' : True
    })
    
    # Set up model
    model = Model(
        scenario=scenario,
        geodata=geodata
    )
    
    # Run model
    model.run()
    results = model.full_results
    return results


def calculate_cohort_outcomes_admissions(
        df_geo_outcomes,
        options_prop_lvo_dripship_treated_with_mt,
        col_admissions,
        mt_rate,
        prop_lvo,
    ):
    results = df_geo_outcomes.copy()
    
    list_of_dfs = [results]
    for p in options_prop_lvo_dripship_treated_with_mt:    
        # Don't overwrite shared results:
        results_here = df_geo_outcomes.copy()
        
        # Calculate numbers of thrombectomies and transfers:
        results_here = add_mt_and_transfers(
            results_here, col_admissions, mt_rate, prop_lvo_ds_mt=p)
        # Calculate outcome results that depend on transfers:
        # Add net benefit columns
        results_here = add_net_benefit(
            results_here,
            prop_lvo=prop_lvo,
            prop_lvo_ds_mt=p
        )
        # Calculate admissions-weighted outcomes:
        cols_outcome = ['drip_ship_mrs_0-2', 'lvo_drip_ship_ivt_mt_mrs_0-2']
        if p != 1.0:
            cols_outcome = [f'{c}_transferloss' for c in cols_outcome]
        results_here = add_admissions_weighted_outcomes(
            results_here, col_admissions, cols_outcome)
    
        old_cols = sum([df.columns.tolist() for df in list_of_dfs], [])
        new_cols = [c for c in results_here.columns if c not in old_cols]
        if p != 1.0:
            rename_dict = dict([(c, f'{c}{p}'.replace('.', '!'))
                for c in new_cols])
        else:
            rename_dict = dict([(c, c) for c in new_cols])
        list_of_dfs.append(results_here[new_cols].rename(columns=rename_dict))
    
    results = pd.concat(list_of_dfs, axis='columns')

    # Round outcome results:
    cols_mrs = [c for c in results.columns if (
                ('mrs' in c) | ('improvement' in c))]
    cols_util = [c for c in results.columns if ('util' in c)]
    results[cols_mrs] = results[cols_mrs].round(3)
    results[cols_util] = results[cols_util].round(5)
    return results


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


def calculate_benefit(
        results,
        p,
        col_benefit,
        dict_cols_benefit_base,
        col_admissions,
    ):
    
    total_admissions = results[col_admissions].sum()
    col_base = dict_cols_benefit_base[col_benefit]
    
    benefit_over_base_by_lsoa = results[col_benefit] - results[col_base]
    
    hospital_net_benefit_here = (
        np.average(benefit_over_base_by_lsoa,
                   weights=results[col_admissions])
        if total_admissions > 0 else np.nan
    )
    
    # Redundant check for changed stroke units due to potential for
    # floating point or rounding error in the >0 comparison.
    benefitting_lsoas = (
        ((results['nearest_ivt_unit'] != results['nearest_ivt_unit_base']) |
         (results['transfer_unit'] != results['transfer_unit_base'])) &
        (benefit_over_base_by_lsoa > 0)
    )
    benefitting_benefit = benefit_over_base_by_lsoa.loc[benefitting_lsoas]
    benefitting_admissions = results[col_admissions].loc[benefitting_lsoas]
    
    hospital_admissions_benefitting_here = benefitting_admissions.sum()
    
    benefitting_weight = benefitting_admissions.sum()
    hospital_benefit_for_those_benefitting_here = (
        np.average(benefitting_benefit, weights=benefitting_admissions)
        if benefitting_weight > 0 else np.nan
    )
    
    return (hospital_net_benefit_here, hospital_admissions_benefitting_here,
            hospital_benefit_for_those_benefitting_here)