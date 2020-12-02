from argschema import ArgSchemaParser
import os
import logging
import subprocess
import time
import shutil
from ...common.utils import catGT_ex_params_from_str

import numpy as np


def get_psth_events(args):

    # simple function to read in extracted edges file created by CatGT
    # then write out a file of events, formatted as csv, to the
    # kilosort_output directory which contains the phy files

    # assumes that CatGT was run using -prb_fld, so extracted SY edges
    # reside in the directory with the binary data and extracted NI edges
    # reside in the parent of that folder

    print('ecephys spike sorting: PSTH events module')
    start = time.time()

    input_file = args['ephys_params']['ap_band_file']
    extract_str = args['psth_events']['event_ex_param_str']

    # get extraction parameters, build name for output file
    ex_type, prb_index, ex_name_str = catGT_ex_params_from_str(extract_str)

    # build path to the CatGT edge extraction file
    if args['ephys_params']['probe_type'] == '3A':
        # no probe folders, so path is catGT_output/catGT_run_name/run_name.bin
        if 'X' in extract_str:
            # nidq channel -- these are hard to parse, because it could be
            # associated with any of the probes, and the folder organization
            # isn't known
            print('3A + nidq not supported by psth_events module\n')
        else:
            # SY channel. will be on this probe, with probe index = 0
            # no probe folder, no probe string in ex_file_name
            run_fld, bin_name = os.path.split(input_file)
            run_name = bin_name[0:bin_name.find('ap.bin')]
            ex_file_name = run_name + ex_name_str + '.txt'
            ex_path = os.path.join(run_fld, ex_file_name)
    else:
        # 3B/NP1.0/NP2.0, assume run and probe folders  
        prb_fld, bin_name = os.path.split(input_file)
        run_fld, prb_fld_name = os.path.split(prb_fld)
        parent_fld, run_fld_name = os.path.split(run_fld)

        # since these data have been through CatGT, the name of the run folder
        # is: catGT_<run_name>
        run_name = run_fld_name[6:]

        if 'X' in extract_str:
            # nidq channel
            ex_file_name = run_name + '_tcat.nidq.' + ex_name_str + '.txt'
            ex_path = os.path.join(run_fld, ex_file_name)
        else:
            # SY channel. could be on any probe, so get the probe string
            prb = str(prb_index)
            ex_file_name = run_name + '_tcat.imec' + prb + '.' + ex_name_str + '.txt'
            ex_prb_fld_name = run_name + '_imec' + prb
            ex_path = os.path.join(run_fld, ex_prb_fld_name, ex_file_name)

    # the CatGT extracted edge files are a single column with </n>
    # event viewer needs .csv
    edgeTimes = np.zeros((0), dtype='float')
    # check if there are events
    if os.stat(ex_path).st_size > 0:
        with open(ex_path, 'r') as inFile:
            line = inFile.readline()
            while line != '':  # The EOF char is an empty string
                currEdge = float(line)
                edgeTimes = np.append(edgeTimes, currEdge)
                line = inFile.readline()
        # eliminate events closer than 0.9 seconds
        edgeTimes = np.array(edgeTimes)
        edgeTimes =  edgeTimes[np.append(5,[np.diff(edgeTimes)]) > 0.9]
        edgeTimes = edgeTimes.tolist()

        # The output should be saved with the phy output, where the event viewer
        # plugin can read it

        phy_dir = args['directories']['kilosort_output_directory']
        event_path = os.path.join(phy_dir, 'events.csv')
        nEvent = len(edgeTimes)
        with open(event_path, 'w') as outfile:
            for i in range(0, nEvent-1):
                outfile.write(f'{edgeTimes[i]:.6f},')
            outfile.write(f'{edgeTimes[nEvent-1]:.6f}')
    else:
        print("No events detected")

    execution_time = time.time() - start

    print('total time: ' + str(np.around(execution_time, 2)) + ' seconds')

    return {"execution_time": execution_time}  # output manifest


def main():

    from ._schemas import InputParameters, OutputParameters

    """Main entry point:"""
    mod = ArgSchemaParser(schema_type=InputParameters,
                          output_schema_type=OutputParameters)

    output = get_psth_events(mod.args)

    output.update({"input_parameters": mod.args})
    if "output_json" in mod.args:
        mod.output(output, indent=2)
    else:
        print(mod.get_output_json(output))


if __name__ == "__main__":
    main()
