#!/bin/bash
#SBATCH --account=canari
#SBATCH --partition=debug
#SBATCH --qos=debug
##SBATCH -o %x.out
##SBATCH -e %x.err
#SBATCH -o %x_%j.out   # JobName_JobID.out
#SBATCH -e %x_%j.err   # JobName_JobID.err
##SBATCH --cpus-per-task=16    
#SBATCH --mem=200G           
##SBATCH --time=04:00:00

conda activate cfa_env

python get-yearly.py --year "$year" --runid "$runid" --member "$member" --scenario "$scenario" --realm "$realm" --filetype "$filetype" --var "$var"


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

# Example...
# for scenario in HIST2 ; do for realm in CICE; do for member in 18; do for year in 1993 ; do for runid in cy879;  do for filetype in day; do for var in aicen  ; do sbatch --export=ALL,year=$year,runid=$runid,member=$member,realm=$realm,scenario=$scenario,filetype=$filetype,var=$var batch.sl ; done;  done; done ; done; done ; done ; done
