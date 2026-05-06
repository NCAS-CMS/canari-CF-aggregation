#!/bin/bash
#SBATCH --account=canari
#SBATCH --partition=standard
#SBATCH --qos=standard
#SBATCH --qos=high
#SBATCH --partition=debug
#SBATCH --qos=debug
#SBATCH -o %j.out
#SBATCH -e %j.err
##SBATCH --cpus-per-task=16    
##SBATCH --mem=128G           
#SBATCH --ntasks=1
##SBATCH --time=04:00:00


conda activate cfa_env

python -u seed.py --member "$member" --realm "$realm" --scenario "$scenario" \
   --data_path "/gws/ssde/j25b/canari/shared/large-ensemble/priority/${scenario}/${member}/${realm}/yearly/" 
