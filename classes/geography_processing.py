"""
Processing of raw geographic data for model
"""

import pandas as pd
import numpy as np


class Geoprocessing(object):
    """
    Processing of raw geographic data for model.
    """

    def __init__(self,
                 limit_to_england=False,
                 mt_travel_bias=0.1,
                 new_mt_centres=[],
                 use_extra_travel_checks=True):
        """
        Initialise geographic class.


        Attributes
        ----------

        admissions : pandas dataframe
            Raw data of stroke admissions in the UK.

        combined_data : pandas dataframe
            Combined data of all processed geographic data.
        
        hospitals : pandas dataframe
            Raw data of hospitals in the UK.

        inter_hospital_time : pandas dataframe
            Raw data of inter hospital transfer times in the UK.

        lsoa_travel_time : pandas dataframe
            Raw data of travel times between LSOAs and hospitals in the UK.
            
        nearest_ivt_unit : pandas dataframe
            Nearest IVT unit to each LSOA.

        nearest_mt_unit : pandas dataframe
            Nearest MT unit to each LSOA.

        transfer_mt_unit : pandas dataframe
            Nearest transfer MT unit to each IVT unit.

        Methods
        -------
        collate_data
            Combine data.

        find_nearest_ivt_unit
            Find the nearest IVT unit to each LSOA.

        find_nearest_mt_unit
            Find the nearest MT unit to each LSOA.

        find_nearest_transfer_mt_unit
            Find the nearest transfer MT unit for each IVT unit.

        load_data
            Load raw geographic data.

        run
            Run all processing methods.

        save_processed_data
            Save combined data
                
        """

        self.limit_to_england = limit_to_england
        self.mt_travel_bias = mt_travel_bias
        self.new_mt_centres = new_mt_centres
        self.use_extra_travel_checks = use_extra_travel_checks

    def run(self):
        """
        Run all processing methods.
        """
        self.load_data()
        self.find_nearest_ivt_unit()
        self.find_nearest_mt_unit()
        self.find_nearest_transfer_mt_unit()
        self.collate_data()
        # self.save_processed_data()
        

    def collate_data(self):
        """
        Combine data
        """
        rename_dict_ivt = dict([
            (c, f'nearest_ivt_{c}') for c in self.nearest_ivt_unit.columns])
        rename_dict_mt = dict([
            (c, f'nearest_mt_{c}') for c in self.nearest_mt_unit.columns])
        self.combined_data = pd.concat(
            (self.nearest_ivt_unit.rename(columns=rename_dict_ivt),
             self.nearest_mt_unit.rename(columns=rename_dict_mt)),
            axis='columns'
        )
        self.combined_data = self.combined_data.merge(
            self.transfer_mt_unit, how='left', left_on='nearest_ivt_unit', right_index=True)
        self.combined_data = self.combined_data.merge(
            self.admissions, how='left', left_index=True, right_index=True)

        # Apply limit to England if required
        if self.limit_to_england:
            self.combined_data = self.combined_data[self.combined_data['England'] == 1]

    def find_nearest_ivt_unit(self):
        """
        Find the nearest IVT unit to each LSOA.
        """

        # Limit data to hospitals providing IVT
        mask = self.hospitals['Use_IVT'] == 1
        self.IVT_hospitals = self.hospitals[mask]['Postcode'].tolist()
        
        # Use only the travel times to IVT hospitals
        travel_matrix = self.lsoa_travel_time[self.IVT_hospitals]
        distance_matrix = self.lsoa_travel_distance[self.IVT_hospitals]
        
        # Apply the MT travel bias when choosing the nearest IVT hospital.
        adjusted_travel_matrix = travel_matrix.copy().astype(float)
        mt_hospitals = self.hospitals.loc[
            self.hospitals['Use_MT'] == 1, 'Postcode']
        mt_columns = travel_matrix.columns.intersection(mt_hospitals)
        adjusted_travel_matrix.loc[:, mt_columns] -= self.mt_travel_bias
        adjusted_travel_matrix = adjusted_travel_matrix.round(1)

        # Choose by adjusted time.
        self.nearest_ivt_unit = pd.DataFrame()

        # Basic unit assignment: pick the first unit in the list
        # that has the nearest time:
        self.nearest_ivt_unit['unit'] = adjusted_travel_matrix.idxmin(axis=1)
        name_index = self.nearest_ivt_unit.index.name
        if self.use_extra_travel_checks:
            # Copy in the adjusted travel time to set up the index:
            self.nearest_ivt_unit['adjusted_time'] = (
                adjusted_travel_matrix.min(axis=1))
            # Extra check: choose from multiple units with the same
            # minimum travel time. Pick the shortest distance.
            self.nearest_ivt_unit = self.find_nearest_unit_extra(
                self.nearest_ivt_unit,
                adjusted_travel_matrix,
                distance_matrix,
                'unit',
                'adjusted_time'
            )
            self.nearest_ivt_unit.index.name = name_index
        else:
            pass
            
        # Copy in the original travel time, not the adjusted:
        column_positions = travel_matrix.columns.get_indexer(
            self.nearest_ivt_unit['unit'])
        # Store time without bias:
        self.nearest_ivt_unit['time'] = travel_matrix.to_numpy()[
            list(range(len(travel_matrix))), column_positions]

        # Store the nearest IVT unit and time
        # without the MT travel bias for reference
        self.nearest_ivt_unit['unit_no_bias'] = (
            travel_matrix.idxmin(axis=1))
        column_positions_no_bias = travel_matrix.columns.get_indexer(
            self.nearest_ivt_unit['unit_no_bias'])
        self.nearest_ivt_unit['time_no_bias'] = travel_matrix.to_numpy()[
            list(range(len(travel_matrix))), column_positions_no_bias]


    def find_nearest_mt_unit(self):
        """
        Find the nearest MT unit to each LSOA.
        """

        # Limit data to hospitals providing MT
        mask = self.hospitals['Use_MT'] == 1
        self.MT_hospitals = self.hospitals[mask]['Postcode'].tolist()
        # Use only the travel times to MT hospitals
        travel_matrix = self.lsoa_travel_time[self.MT_hospitals]
        distance_matrix = self.lsoa_travel_distance[self.MT_hospitals]
        # Find the value and index for the lowest travel time for each LSOA
        self.nearest_mt_unit = pd.DataFrame()
        self.nearest_mt_unit['time'] = travel_matrix.min(axis=1)
        name_index = self.nearest_mt_unit.index.name
    
        # Basic unit assignment: pick the first unit in the list
        # that has the nearest time:
        self.nearest_mt_unit['unit'] = travel_matrix.idxmin(axis=1)
        if self.use_extra_travel_checks:
            # Extra check: choose from multiple units with the same
            # minimum travel time. Pick the shortest distance.
            self.nearest_mt_unit = self.find_nearest_unit_extra(
                self.nearest_mt_unit,
                travel_matrix,
                distance_matrix,
                'unit',
                'time'
            )
            self.nearest_mt_unit.index.name = name_index
        else:
            pass

    
    def find_nearest_transfer_mt_unit(self):
        """
        Find the nearest transfer MT unit for each IVT unit
        """

        # Use only the travel times to MT hospitals
        travel_matrix = self.inter_hospital_time[self.MT_hospitals]
        distance_matrix = self.inter_hospital_distance[self.MT_hospitals]
        # Find the value and index for the lowest travel time for each LSOA
        self.transfer_mt_unit = pd.DataFrame()
        self.transfer_mt_unit['transfer_time'] = travel_matrix.min(axis=1)
        name_index = self.transfer_mt_unit.index.name

        # Basic unit assignment: pick the first unit in the list
        # that has the nearest time:
        self.transfer_mt_unit['transfer_unit'] = travel_matrix.idxmin(axis=1)
        if self.use_extra_travel_checks:
            # Extra check: choose from multiple units with the same
            # minimum travel time. Pick the shortest distance.
            self.transfer_mt_unit = self.find_nearest_unit_extra(
                self.transfer_mt_unit,
                travel_matrix,
                distance_matrix,
                'transfer_unit',
                'transfer_time'
            )
            self.transfer_mt_unit.index.name = name_index
        else:
            pass

        self.transfer_mt_unit['transfer_required'] = \
            self.transfer_mt_unit['transfer_unit'] != travel_matrix.index.tolist(
        )


    def find_nearest_unit_extra(
            self,
            df,
            travel_matrix,
            distance_matrix,
            label='transfer_unit',
            label_time='time'
        ):
        # Find which places to check:
        s_to_concat = np.empty(len(travel_matrix.columns), dtype=object)
        for i, c in enumerate(travel_matrix.columns):
            s = (travel_matrix[c] == df[label_time])
            s.name = c
            s_to_concat[i] = s
        df_bool_min_times = pd.concat(s_to_concat, axis='columns')
        s = df_bool_min_times.sum(axis='columns')
        places_to_check = s[s > 1].index

        s_nearest_units = pd.Series(name=label)
        s_nearest_units_flag = pd.Series(name=f'{label}_multiple_same_time')
        s_nearest_units_distance_flag = pd.Series(
            name=f'{label}_multiple_same_time_and_distance')
        s_nearest_units_options = pd.Series(
            name=f'{label}_multiple_same_time_and_distance_options')

        for place in places_to_check:
            # Shortest travel time:
            t = df[label_time][place]
            # Units with shortest travel time:
            s = travel_matrix.loc[place]
            units_nearest = s[s == t].index.tolist()
            if len(units_nearest) == 0:
                # This shouldn't happen!
                print('place:', place)
                print('t:', t)
                print('s:', s)
                raise IndexError('Missing units by time.')
            elif len(units_nearest) == 1:
                u = units_nearest[0]
                ft = 0
                fd = 0
                options = []
            else:
                # Flag that multiple units had the same time:
                ft = 1
                # Check which has the nearer distance:
                d = distance_matrix.loc[place][units_nearest]
                d_min = d.min()
                units_nearest_dist = d[d == d_min].index.tolist()
                # Check whether there are still multiple units:
                if len(units_nearest_dist) == 0:
                    # This shouldn't happen!
                    print('place:', place)
                    print('t:', t)
                    print('d_min:', d_min)
                    print('units_nearest:', units_nearest)
                    print('d:', d)
                    raise IndexError('Missing units by distance.')
                elif len(units_nearest_dist) == 1:
                    fd = 0
                    options = []
                else:
                    fd = 1
                    # Arbitrarily pick the first option alphabetically
                    # by postcode:
                    options = sorted(units_nearest_dist)
                u = sorted(units_nearest_dist)[0]
            # Store result:
            s_nearest_units[place] = u
            s_nearest_units_flag[place] = ft
            s_nearest_units_distance_flag[place] = fd
            s_nearest_units_options[place] = options

        df = pd.concat(
            (df, s_nearest_units_flag,
             s_nearest_units_distance_flag, s_nearest_units_options),
            axis='columns'
        )
        df[label] = s_nearest_units.combine_first(df[label])
        return df
    

    def load_data(self):
        """
        Load raw geographic data.
        """
        self.hospitals = pd.read_csv(
            './data/stroke_hospitals_2025.csv')
        # Make sure hospitals are alphabetical by postcode:
        self.hospitals = self.hospitals.sort_values('Postcode')

        # If there are new MT centres, change the Use_MT column to 1 for those hospitals
        if len(self.new_mt_centres) > 0 :
            for new_mt_centre in self.new_mt_centres:
                self.hospitals.loc[self.hospitals['Postcode'] == new_mt_centre, 'Use_MT'] = 1
        
        if self.limit_to_england:
            self.hospitals = self.hospitals[self.hospitals['Country'] == 'England']

        used_hospitals = self.hospitals['Postcode'].tolist()

        self.admissions = pd.read_csv(
            './data/admissions_2025_simple_scaled.csv', index_col='area')
        self.admissions.sort_index(inplace=True)

        if self.limit_to_england:
            self.admissions = self.admissions[self.admissions['England'] == 1]

        used_lsoas = self.admissions.index.tolist()

        self.inter_hospital_time = pd.read_csv(
            './data/inter_hospital_pivoted_time.csv', index_col='from_postcode')
        
        self.lsoa_travel_time = pd.read_csv(
            './data/pivoted_time.csv', index_col='LSOA')
        
        self.inter_hospital_distance = pd.read_csv(
            './data/inter_hospital_pivoted_distance.csv', index_col='from_postcode')
        
        self.lsoa_travel_distance = pd.read_csv(
            './data/pivoted_distance_km.csv', index_col='LSOA')
        
        # limit to used LSOAs and hospitals
        self.inter_hospital_time = self.inter_hospital_time.loc[
            used_hospitals, used_hospitals]
        self.inter_hospital_distance = self.inter_hospital_distance.loc[
            used_hospitals, used_hospitals]
        self.lsoa_travel_time = self.lsoa_travel_time.loc[used_lsoas]
        self.lsoa_travel_distance = self.lsoa_travel_distance.loc[used_lsoas]


    def save_processed_data(self):
        """
        Save combined data
        """

        # Apply limit to England if required
        if self.limit_to_england:
            self.combined_data = self.combined_data[self.combined_data['England'] == 1]
        
        self.combined_data.to_csv(
            './processed_data/processed_data.csv', index_label='LSOA')
