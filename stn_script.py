'''
Created on Jul 17, 2017

@author: gpetrochenkov
'''
#!/usr/bin/env python3
import sys
import csv
current_path = sys.path[0]
sys.path.append(''.join([current_path,'\\..']))
sys.path.append(''.join([current_path,'\\..\\netCDF_Utils']))

import numpy as np
import netCDF_Utils.nc as nc
from pytz import timezone
from csv_readers import Leveltroll, MeasureSysLogger, House, Hobo, RBRSolo, Waveguage
import unit_conversion as uc
import argparse
from tools.storm_options import StormOptions
from tools.storm_netCDF import Storm_netCDF
from tools.storm_graph import StormGraph, Bool
from tools.storm_statistics import StormStatistics


INSTRUMENTS = {
    'LevelTroll': Leveltroll,
    'RBRSolo': RBRSolo,
    'Wave Guage': Waveguage,
    'USGS Homebrew': House,
    'MS TruBlue 255': MeasureSysLogger,
    'Onset Hobo U20': Hobo }

def convert_to_netcdf(inputs):
    translated = translate_inputs(inputs)
    instrument = INSTRUMENTS[translated['instrument_name']]()
    instrument.user_data_start_flag = 0
    for key in translated:
        setattr(instrument, key, translated[key])
    instrument.read()
    instrument.write(pressure_type=translated['pressure_type'])
    return instrument.bad_data


DATATYPES = {
    'latitude': np.float32,
    'longitude': np.float32,
    'initial_water_depth': np.float32,
    'final_water_depth': np.float32,
    'device_depth': np.float32,
    'tzinfo': timezone,
    'sea_pressure' : bool }

def translate(inputs):
    translated = translate_inputs(inputs)
    instrument = INSTRUMENTS[translated['instrument_name']]()
    instrument.user_data_start_flag = 0
    for key in translated:
        setattr(instrument, key, translated[key])

def translate_inputs(inputs):
    translated = dict()
    for key in inputs: # cast everything to the right type
        if key in DATATYPES:
            translated[key] = DATATYPES[key](inputs[key])
        else:
            translated[key] = inputs[key]
    return translated

def find_index(array, value):
    
    array = np.array(array)
    idx = (np.abs(array-value)).argmin()
    
    return idx

def check_file_type(file_name):
    index = file_name.rfind('.')
    if index == -1:
        csv_file = open(file_name)
        try:
            dialect = csv.Sniffer().sniff(csv_file.read(1024))
            return True
        except:
            return False
    else: 
        if file_name[index:] == '.csv':
            return True
        else:
            return False
    
def process_file(args):
    daylight_savings = False
    if args['daylight_savings'].lower() == 'true':
        daylight_savings = True
        
    inputs = {
        'in_filename' : args['in_fname'],
        'out_filename' : args['out_fname'],
        'creator_name' : args['creator_name'],
        'creator_email' : args['creator_email'],
        'creator_url' : args['creator_url'],
        'instrument_name' : args['instrument_name'],
        'stn_station_number': args['stn_station_number'],
        'stn_instrument_id': args['stn_instrument_id'],
        'latitude' : args['latitude'],
        'longitude' : args['longitude'],
        'tz_info' : args['tz_info'],
        'daylight_savings': daylight_savings,
        'datum': args['datum'],
        'initial_sensor_orifice_elevation': args['initial_sensor_orifice_elevation'],
        'final_sensor_orifice_elevation': args['final_sensor_orifice_elevation'],
        'salinity' : args['salinity'],
        'initial_land_surface_elevation': args['initial_land_surface_elevation'],
        'final_land_surface_elevation': args['final_land_surface_elevation'],
        'deployment_time' : args['deployment_time'],
        'retrieval_time' : args['retrieval_time'],
        'sea_name' : args['sea_name'],    
        'pressure_type' : args['pressure_type'],
        'good_start_date': args['good_start_date'],
        'good_end_date': args['good_end_date'],
        }
     
    #checks for the correct file type
    if check_file_type(inputs['in_filename']) == False:
        return (2, None)
       
    #check for dates in chronological order if sea pressure file
    if inputs['pressure_type'] == 'Sea Pressure':
        inputs['deployment_time'] = uc.datestring_to_ms(inputs['deployment_time'], '%Y%m%d %H%M', \
                                                             inputs['tz_info'],
                                                             inputs['daylight_savings'])
        
        inputs['retrieval_time'] = uc.datestring_to_ms(inputs['retrieval_time'], '%Y%m%d %H%M', \
                                                             inputs['tz_info'],
                                                             inputs['daylight_savings'])
        if inputs['retrieval_time'] <= inputs['deployment_time']:
            return (3, None)
        
    
    try:
        data_issues = convert_to_netcdf(inputs)
    except:
        return (5, None)
     
    time = nc.get_time(inputs['out_filename'])
    
    start_index = find_index(time,uc.datestring_to_ms(inputs['good_start_date'], '%Y%m%d %H%M', \
                                                         inputs['tz_info'],
                                                         inputs['daylight_savings']))
    end_index = find_index(time,uc.datestring_to_ms(inputs['good_end_date'], '%Y%m%d %H%M', \
                                                         inputs['tz_info'],
            
                                                         inputs['daylight_savings']))
    #checks for chronological order of dates
    if end_index <= start_index:
        return (3, None)
       
    air_pressure = False
    if args['pressure_type'] == 'Air Pressure':
        air_pressure = True
         
    try:
        nc.chop_netcdf(inputs['out_filename'], ''.join([inputs['out_filename'],'chop.nc']), 
                           start_index, end_index, air_pressure)
    except:
        return (5, None)
  
    
    if data_issues:
        return (1, ''.join([inputs['out_filename'],'chop.nc']))
    else:
        return (0, ''.join([inputs['out_filename'],'chop.nc']))
    #will be either 0 for perfect overlap or 1 for slicing some data
    
def process_storm_files(args):
    
    so = StormOptions()
    
    so.air_fname = args['air_fname']
    so.sea_fname = args['sea_fname']
    
    #check to see if the correct type of files were uploaded
    if so.check_file_types() == False:
        return 2
    
    so.wind_fname = None
    
    so.format_output_fname(args['out_fname'])
    so.timezone = args['tz_info']
    so.daylight_savings = args['daylight_savings']
    
    if 'baro_y_min' in args and args['baro_y_min'] is not None:
        so.baroYLims = []
        so.baroYLims.append(args['baro_y_min'])
        so.baroYLims.append(args['baro_y_max'])
        
    if 'wl_y_min' in args and args['wl_y_min'] is not None:
        so.wlYLims = []
        so.wlYLims.append(args['wl_y_min'])
        so.wlYLims.append(args['wl_y_max'])
    
    #check to see if the time series of the water and air file overlap
    overlap = so.time_comparison()
       
    #if there is no overlap             
    if overlap == 2:
        return 4
    
    try:
        snc = Storm_netCDF()
        so.netCDF['Storm Tide with Unfiltered Water Level'] = Bool(True)
        so.netCDF['Storm Tide Water Level'] = Bool(True)
        snc.process_netCDFs(so)
                 
                
        sg = StormGraph()
        so.graph['Storm Tide with Wind Data'] = Bool(False)
        so.graph['Storm Tide with Unfiltered Water Level'] = Bool(True)
        so.graph['Storm Tide Water Level'] = Bool(True)
        so.graph['Atmospheric Pressure'] = Bool(True)
        sg.process_graphs(so)
        
        if args['sea_4hz'].lower() == 'true':
            so.int_units = False
            so.high_cut = 1.0
            so.low_cut = 0.045
            so.from_water_level_file = False
        
            
            ss = StormStatistics()
            
            for y in so.statistics:
                so.statistics[y] = Bool(False)
                
            so.statistics['H1/3'] = Bool(True)
            so.statistics['Average Z Cross'] = Bool(True)
            so.statistics['PSD Contour'] = Bool(True)
    
            ss.process_graphs(so)
        
        return 0
    except:
        return 5
     
    


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    
    
    parser.add_argument('sea_fname',
                        help='directory location of raw sea pressure csv file')
    parser.add_argument('air_fname',
                        help='directory location of raw air pressure csv file')
    parser.add_argument('out_fname',
                        help='directory location to output netCDF file')
    parser.add_argument('creator_name',
                        help='name of user running the script')
    parser.add_argument('creator_email',
                        help='email of user running the script')
    parser.add_argument('creator_url',
                        help='url of organization the user running the script belongs to')
    parser.add_argument('sea_instrument_name',
                        help='name of the instrument used to measure pressure')
    parser.add_argument('air_instrument_name',
                        help='name of the instrument used to measure pressure')
    parser.add_argument('sea_stn_station_number',
                        help='STN Site ID')
    parser.add_argument('air_stn_station_number',
                        help='STN Site ID')
    parser.add_argument('sea_stn_instrument_id',
                        help='STN Instrument ID')
    parser.add_argument('air_stn_instrument_id',
                        help='STN Instrument ID')
    parser.add_argument('sea_latitude', type=float,
                        help='latitude of instrument')
    parser.add_argument('air_latitude', type=float,
                        help='latitude of instrument')
    parser.add_argument('sea_longitude', type=float,
                        help='longitude of instrument')
    parser.add_argument('air_longitude', type=float,
                        help='longitude of instrument')
    parser.add_argument('tz_info', 
                        help='time zone of instrument output dates')
    parser.add_argument('daylight_savings', 
                        help='if time zone is in daylight savings')
    parser.add_argument('datum', 
                        help='geospatial vertical reference point')
    parser.add_argument('sea_initial_sensor_orifice_elevation', type=float,
                        help='tape down to sensor at deployment time')
    parser.add_argument('air_initial_sensor_orifice_elevation', type=float,
                        help='tape down to sensor at deployment time')
    parser.add_argument('sea_final_sensor_orifice_elevation', type=float,
                        help='tape down to sensor at retrieval time')
    parser.add_argument('air_final_sensor_orifice_elevation', type=float,
                        help='tape down to sensor at retrieval time')
    parser.add_argument('salinity',
                        help='salinity of the sea surface')
    parser.add_argument('initial_land_surface_elevation', type=float,
                        help='tape down to sea floor at deployment time')
    parser.add_argument('final_land_surface_elevation', type=float,
                        help='tape down to sea floor at retrieval time')
    parser.add_argument('deployment_time',
                        help='time when the instrument was deployed')
    parser.add_argument('retrieval_time',
                        help='time when the instrument was retrieved')
    parser.add_argument('sea_name',
                        help='name of the body of water the instrument was deployed in')
    parser.add_argument('sea_good_start_date',
                        help='first date for chopping the time series')
    parser.add_argument('air_good_start_date',
                        help='first date for chopping the time series')
    parser.add_argument('sea_good_end_date',
                        help='last date for chopping the time series')
    parser.add_argument('air_good_end_date',
                        help='last date for chopping the time series')
    parser.add_argument('sea_4hz',
                        help='True if sea instrument is sampled at 4hz')
    parser.add_argument('--baro_y_min', 
                        help='y axis minimum for barometric pressure graph')
    parser.add_argument('--bar_y_max',
                        help='y axis maximum for barometric pressure graph')
    parser.add_argument('--wl_y_min', 
                        help='y axis minimum for water level graph')
    parser.add_argument('--wl_y_max',
                        help='y axis maximum for water level graph')
      
      
      
    args = vars(parser.parse_args(sys.argv[1:]))

#     args = {
#         'sea_fname': 'NCCAR00007_1511451_sea.csv',
#         'air_fname': 'NCCAR12248_9983816_air.csv',
#         'out_fname': 'storm',
#         'creator_name': "greg",
#         'creator_email': 'g@g.com',
#         'creator_url': 'g.com',
#         'sea_instrument_name': "MS TruBlue 255",
#         'air_instrument_name': "Onset Hobo U20",
#         'sea_stn_station_number': '1',
#         'air_stn_station_number': '2',
#         'sea_stn_instrument_id': '3',
#         'air_stn_instrument_id': '4',
#         'sea_latitude': 20.0,
#         'air_latitude': 30.0,
#         'sea_longitude': 40.0,
#         'air_longitude': 50.0,
#         'tz_info': 'US/Central',
#         'daylight_savings': 'False',
#         'datum': 'NAVD88',
#         'sea_initial_sensor_orifice_elevation': 1,
#         'air_initial_sensor_orifice_elevation': 1,
#         'sea_final_sensor_orifice_elevation': 1.5,
#         'air_final_sensor_orifice_elevation': 1.5,
#         'salinity': "Salt Water (^> 30 ppt)",
#         'initial_land_surface_elevation': 1,
#         'final_land_surface_elevation': 1.2,
#         'deployment_time': "20151002 0000",
#         'retrieval_time': "20151010 0000",
#         'sea_name': "Chesapeake Bay",
#         'sea_good_start_date': "20161008 0800",
#         'air_good_start_date': "20161008 0800",
#         'sea_good_end_date': "20161010 0800",
#         'air_good_end_date': "20161010 0800",
#         'sea_4hz': 'True'
#         }
     
    output = args['out_fname']
    
    args['in_fname'] = args['sea_fname']
    args['out_fname'] = ''.join([args['out_fname'], '_sea'])
    args['pressure_type'] = 'Sea Pressure'
    args['instrument_name'] = args['sea_instrument_name']
    args['stn_station_number'] = args['sea_stn_station_number']
    args['stn_instrument_id'] = args['sea_stn_instrument_id']
    args['latitude'] = args['sea_latitude']
    args['longitude'] = args['sea_longitude']
    args['initial_sensor_orifice_elevation'] = args['sea_initial_sensor_orifice_elevation']
    args['final_sensor_orifice_elevation'] = args['sea_final_sensor_orifice_elevation']
    args['good_start_date'] = args['sea_good_start_date']
    args['good_end_date'] = args['sea_good_end_date']
    sea_code, args['sea_fname'] = process_file(args)
    args['out_fname'] = output
    
    args['in_fname'] = args['air_fname'] 
    args['out_fname'] = ''.join([args['out_fname'], '_air'])
    args['pressure_type'] = 'Air Pressure'
    args['instrument_name'] = args['air_instrument_name']
    args['stn_station_number'] = args['air_stn_station_number']
    args['stn_instrument_id'] = args['air_stn_instrument_id']
    args['latitude'] = args['air_latitude']
    args['longitude'] = args['air_longitude']
    args['initial_sensor_orifice_elevation'] = args['air_initial_sensor_orifice_elevation']
    args['final_sensor_orifice_elevation'] = args['air_final_sensor_orifice_elevation']
    args['good_start_date'] = args['air_good_start_date']
    args['good_end_date'] = args['air_good_end_date']
    air_code, args['air_fname'] = process_file(args)
    args['out_fname'] = output
    
    code = process_storm_files(args)
    
    sys.stdout.write(str(sea_code))
    sys.stdout.write('\n')
    sys.stdout.write(str(air_code))
    sys.stdout.write('\n')
    sys.stdout.write(str(code))
    sys.stdout.write('\n')
    sys.stdout.flush()
    
    
