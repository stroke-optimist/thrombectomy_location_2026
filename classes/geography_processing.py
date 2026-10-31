"""
Processing of raw geographic data for model
"""

import pandas as pd


class Geoprocessing(object):
    """
    Processing of raw geographic data for model.
    """

    def __init__(self,
                 limit_to_england=False,
                 mt_travel_bias=0.1,
                 new_mt_centres=[]):
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

    def run(self):
        """
        Run all processing methods.
        """
        self.load_data()
        self.find_nearest_ivt_unit()
        self.find_nearest_mt_unit()
        self.find_nearest_transfer_mt_unit()
        self.collate_data()
        self.save_processed_data()
        

    def collate_data(self):
        """
        Combine data
        """

        self.combined_data = pd.DataFrame()
        self.combined_data['nearest_ivt_unit'] = self.nearest_ivt_unit['unit']
        self.combined_data['nearest_ivt_time'] = self.nearest_ivt_unit['time']
        self.combined_data['nearest_ivt_unit_no_bias'] = self.nearest_ivt_unit['nearest_ivt_unit_no_bias']  
        self.combined_data['nearest_ivt_time_no_bias'] = self.nearest_ivt_unit['nearest_ivt_time_no_bias']
        self.combined_data['nearest_mt_unit'] = self.nearest_mt_unit['unit']
        self.combined_data['nearest_mt_time'] = self.nearest_mt_unit['time']
        self.combined_data = self.combined_data.merge(
            self.transfer_mt_unit, how='left', left_on='nearest_ivt_unit', right_index=True)
        self.combined_data = self.combined_data.merge(
            self.admissions, how='left', left_index=True, right_index=True)

    def find_nearest_ivt_unit(self):
        """
        Find the nearest IVT unit to each LSOA.
        """

        # Limit data to hospitals providing IVT
        mask = self.hospitals['Use_IVT'] == 1
        self.IVT_hospitals = self.hospitals[mask]['Postcode'].tolist()
        
        # Use only the travel times to IVT hospitals
        travel_matrix = self.lsoa_travel_time[self.IVT_hospitals]
        
        # Apply the MT travel bias when choosing the nearest IVT hospital.
        adjusted_travel_matrix = travel_matrix.copy().astype(float)
        mt_hospitals = self.hospitals.loc[
            self.hospitals['Use_MT'] == 1, 'Postcode']
        mt_columns = travel_matrix.columns.intersection(mt_hospitals)
        adjusted_travel_matrix.loc[:, mt_columns] -= self.mt_travel_bias

        # Choose by adjusted time.
        self.nearest_ivt_unit = pd.DataFrame()
        self.nearest_ivt_unit['unit'] = adjusted_travel_matrix.idxmin(axis=1)
        column_positions = travel_matrix.columns.get_indexer(
            self.nearest_ivt_unit['unit'])
        self.nearest_ivt_unit['time'] = adjusted_travel_matrix.to_numpy()[
            list(range(len(travel_matrix))), column_positions]

        # Store the nearest IVT unit and time without the MT travel bias for reference
        self.nearest_ivt_unit['nearest_ivt_unit_no_bias'] = travel_matrix.idxmin(axis=1)
        column_positions_no_bias = travel_matrix.columns.get_indexer(
            self.nearest_ivt_unit['nearest_ivt_unit_no_bias'])
        self.nearest_ivt_unit['nearest_ivt_time_no_bias'] = travel_matrix.to_numpy()[
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
        # Find the value and index for the lowest travel time for each LSOA
        self.nearest_mt_unit = pd.DataFrame()
        self.nearest_mt_unit['unit'] = travel_matrix.idxmin(axis=1)
        self.nearest_mt_unit['time'] = travel_matrix.min(axis=1)

    def find_nearest_transfer_mt_unit(self):
        """
        Find the nearest transfer MT unit for each IVT unit
        """

        # Use only the travel times to MT hospitals
        travel_matrix = self.inter_hospital_time[self.MT_hospitals]
        # Find the value and index for the lowest travel time for each LSOA
        self.transfer_mt_unit = pd.DataFrame()
        self.transfer_mt_unit['transfer_unit'] = travel_matrix.idxmin(axis=1)
        self.transfer_mt_unit['transfer_required'] = \
            self.transfer_mt_unit['transfer_unit'] != travel_matrix.index.tolist(
        )
        self.transfer_mt_unit['transfer_time'] = travel_matrix.min(axis=1)

    def load_data(self):
        """
        Load raw geographic data.
        """
        self.hospitals = pd.read_csv(
            './data/stroke_hospitals_2025.csv')

        # If there are new MT centres, change the Use_MT column to 1 for those hospitals
        if len(self.new_mt_centres) > 0 :
            for new_mt_centre in self.new_mt_centres:
                self.hospitals.loc[self.hospitals['Postcode'] == new_mt_centre, 'Use_MT'] = 1
        
        if self.limit_to_england:
            self.hospitals = self.hospitals[self.hospitals['Country'] == 'England']

        used_hospitals = self.hospitals.index.tolist()

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
        
        
        # limit to used LSOAs and hospitals
        self.lsoa_travel_time = self.lsoa_travel_time.loc[used_lsoas]


    def save_processed_data(self):
        """
        Save combined data
        """

        # Apply limit to England if required
        if self.limit_to_england:
            self.combined_data = self.combined_data[self.combined_data['England'] == 1]
        
        self.combined_data.to_csv(
            './processed_data/processed_data.csv', index_label='LSOA')
