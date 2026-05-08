#!/bin/bash
#SBATCH --account=canari
#SBATCH --partition=standard
#SBATCH --qos=short
#SBATCH -o %x.out
#SBATCH -e %x.err
##SBATCH --cpus-per-task=16    
#SBATCH --mem=200G           
##SBATCH --ntasks=1
##SBATCH --time=04:00:00
##SBATCH --partition=debug
##SBATCH --qos=debug


conda activate cfa_env

python -u seed.py --member "$member" --realm "$realm" --scenario "$scenario" \
   --data_path "/gws/ssde/j25b/canari/shared/large-ensemble/priority/${scenario}/${member}/${realm}/yearly/" 

# Check the exit code of the PREVIOUS command (the python script)
if [ $? -eq 0 ]; then
    echo "----------------------------------------"
    echo "JOB COMPLETED SUCCESSFULLY"
    echo "Finished at: $(date)"
    echo "----------------------------------------"
else
    echo "----------------------------------------"
    echo "JOB FAILED"
    echo "Exit code: $?"
    echo "Finished at: $(date)"
    echo "----------------------------------------"
    exit 1
fi
