#!/bin/bash
#SBATCH --account=canari
#SBATCH --partition=standard
#SBATCH --qos=short
##SBATCH -o %x.out
##SBATCH -e %x.err
#SBATCH -o %x_%j.out   # JobName_JobID.out
#SBATCH -e %x_%j.err   # JobName_JobID.err
##SBATCH --cpus-per-task=16    
#SBATCH --mem=200G           
#SBATCH --time=04:00:00

conda activate cfa_env

python -u priority-variables.py --member "$member" --realm "$realm" --scenario "$scenario" \
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

# for scenario in HIST2 SSP370; do for realm in OCN CICE; do for member in {1..40}; do sbatch --export=ALL,member=$member,realm=$realm,scenario=$scenario batch.sl ; done;  done; done
