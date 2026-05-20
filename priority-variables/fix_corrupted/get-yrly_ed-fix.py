#!/usr/bin/env python

# Ed reported an issue with monthly mean precip mem5 mar2031:
#/gws/ssde/j25b/canari/shared/large-ensemble/priority/SSP370/5/ATM/yearly/2031/df220a_5_mon_m01s05i216_3.nc
#
# I retrieved relevant mon file from tape and all looks good:
# ./jdma_get_monthly_heavyside.py --start 2031 --end 2031 --ens 5 u-df220
#
# This script: do the priority extraction for that variable
# ./get-yrly_ed-fix.py u-df220 5 1 SSP370
import time
import cf
import os

SOURCE_DIR = '/work/xfc/vol10/user_cache/canari/bjharvey/temp'
#TARGET_DIR = '/gws/nopw/j04/canari/shared/large-ensemble/extras'
TARGET_DIR = '/gws/ssde/j25b/canari/shared/large-ensemble/extras'

#years = {'HIST2': range(1950, 2015),
#         'SSP370': range(2015, 2100)}
years = {'SSP370': range(2031, 2032)}

# Dictionary holding all variables you might want to extract
# Select which one using var_index (start from 1 to allow slurm array index as input)
files_type = {1 :  ['_mon_', 'ncvar%m01s05i216_3', 'ATM']}

def get_my_data(sid, ens, var_index, exp):
   
   # Select field to extract
   file_type = files_type[var_index]
   print('file:  ', file_type[0])
   print('field: ', file_type[1])
   print('component: ', file_type[2])
   cptstr = {'ATM': 'a', 'OCN': 'o', 'CICE': 'i'}[file_type[2]]
   
   # Loop over years
   for yr in years[exp]:

      # Read files
      in_dir = SOURCE_DIR + '/' + sid + '/' + str(yr) + '*Z'
      file_name = in_dir + '/' + sid[-5:] + cptstr + '_' + str(ens) + file_type[0] + '_*.nc'
      print(' year', yr, 'file: ', file_name)
      aggregate_time = time.time()
      f = cf.read(file_name,
                  aggregate={'ncvar_identities':True, 'concatenate':False},
                  select=file_type[1], dask_chunks=None)
      print(f)
      print(' year', yr, 'aggregate --- %s seconds ---' % (time.time() - aggregate_time))

      # Write file
      out_dir = TARGET_DIR + '/' + exp + '/' + str(ens) + '/' + file_type[2] + '/yearly/' + str(yr)
      try:
         os.makedirs(out_dir)
      except FileExistsError:
         pass
      out_file_name = out_dir + '/' + sid[-5:] + cptstr + '_' + str(ens) + file_type[0] + file_type[1][6:] + '.nc'
      print (' year', yr, 'out_file: ',  out_file_name)
      write_time = time.time()
      cf.write(f, out_file_name, compress=1)
      print(' year', yr, 'finished writing ', '--- %s seconds ---' % (time.time() - write_time))


if __name__ == '__main__':

    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('suite', help='Suite ID to extract data from')
    parser.add_argument('ens_num', type=int, help='Ensemble number of suite')
    parser.add_argument('var_index', type=int, help='Job array index')
    parser.add_argument('exp', help='Experiment name (HIST2 or SSP370)')
    args = parser.parse_args()

    suite = args.suite
    ens   = args.ens_num
    var_index = args.var_index
    exp = args.exp

    print ('suite ', suite)
    print ('ens ', ens)
    print ('var_index ', var_index)
    print ('exp ', exp)

    get_my_data(suite, ens, var_index, exp)
