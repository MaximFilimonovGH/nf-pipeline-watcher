import os
import time
from datetime import datetime
import subprocess
import re

# import pyyaml
import yaml

this_file_dir = os.path.dirname(__file__)

## read config file
config = yaml.safe_load(open('config.yaml'))
nextflow_path = config['nextflow_path']
input_dir = config['input_dir']
output_dir = config['output_dir']
log_dir = config['log_dir']
tower_address = config['tower_address']
pipelines = config['pipelines']

service_log_file = os.path.join(log_dir, 'service.log')
processed_files_location = os.path.join(output_dir, 'processed')
# running location for pipelines
run_location = os.path.join(output_dir, 'run_location')

## function to return files in a directory
def files_in_directory(dir: str):
    files = []
    for f in os.listdir(dir):
        if os.path.isfile(os.path.join(dir, f)):
            files.append(f)
    return files

## function to compare old files list with a new files list
def compare_filelists(original_list: list, new_list: list):
    dif_list = []
    for f in new_list:
        if f not in original_list:
            dif_list.append(f)
    return dif_list

## function to get correct prefix from filename
# prefix format is '<prefix>_<rest_of_filename>'
def get_prefix(file: str):
    # if no '_' symbol then there is no prefix
    if '_' not in file:
        # return error
        return 'error'
    else:
        # get prefix and return it
        prefix = file[:file.index('_')]
        return prefix

## function to generate command for launching pipeline based on params etc.
def get_nextflow_run_command(pipeline, input_path, output_path, file: str):
    cmd = ''
    # check if there is a version supplied
    if 'version' in pipeline:
        if pipeline['version']:
            cmd = f"NXF_VER={pipeline['version']} {nextflow_path} run"
        else:
            cmd = f"{nextflow_path} run"
    # add main pipeline command
    cmd += f" {pipeline['run_command']}"
    # add profile string if supplied
    if 'profile' in pipeline:
        if pipeline['profile']:
            cmd += f" -profile {pipeline['profile']}"
    # add config string if supplied
    if 'config' in pipeline:
        if pipeline['config']:
            cmd += f" -config {pipeline['config']}"
    # check if tower is needed
    if 'with_tower' in pipeline:
        if pipeline['with_tower']:
            if pipeline['with_tower'] == True:
                cmd += f" -with-tower {tower_address}"
    ## form parameters string is supplied
    if 'params' in pipeline:
        if pipeline['params']:
            param_string = ''
            for param in pipeline['params']:
                param_string += f" --{list(param.keys())[0]} {param[list(param.keys())[0]]}"
            # add params to cmd
            cmd += param_string
    ## process input parameter
    # check the name of the input parameter for the pipeline
    if 'input_parameter' in pipeline:
        if pipeline['input_parameter']:
            # input parameter is a directory, adjust input_path accordingly
            if pipeline['input_type'] == 'directory':
                pipeline_input_dir = os.path.abspath(os.path.join(input_path, os.pardir))
                cmd += f" --{pipeline['input_parameter']} {pipeline_input_dir}"
            # input parameter is file
            else:
                cmd += f" --{pipeline['input_parameter']} {input_path}"
    # check for output parameter name and append it
    if 'output_parameter' in pipeline:
        if pipeline['output_parameter']:
            cmd += f" --{pipeline['output_parameter']} {output_path}"

    ## filetype unique parameter if provided
    if 'filetype' in pipeline:
        if pipeline['filetype']:
            if pipeline['filetype'] == 'find':
                ftype = os.path.basename(file).split('.')[1]
                cmd += f" --filetype {ftype}"
            else:
                cmd += f" --filetype {pipeline['filetype']}"
    
    # add background parameter for nextflow run
    cmd += " -bg"
    return cmd

# function to launch pipelines
def launch_pipeline(file: str, prefix: str):
    original_location = os.getcwd()
    # get basename of the file
    file_basename = os.path.basename(file)
    # log filename
    log_filename = f"{prefix}_{os.path.splitext(file_basename)[0]}"
    # get log and err file names
    log_file = os.path.join(log_dir, log_filename + '.log')
    err_file = os.path.join(log_dir, log_filename + '.err')

    with open(service_log_file, 'a') as sf:
        sf.write(f"{datetime.now().replace(microsecond=0)}: Processing file: {file}\n")

    # check the prefix
    # some testing prefixes
    if prefix.lower() == 'test':
        cmd = 'ls -a'
        with open(service_log_file, 'a') as sf:
            sf.write(f"{datetime.now().replace(microsecond=0)}: Launching test '{cmd}' command\n")
            sf.write(f"{datetime.now().replace(microsecond=0)}: See {log_file} for details.\n")
        with open(log_file, 'w+') as log_f:
            subprocess.Popen(cmd, stdout=log_f, stderr=subprocess.STDOUT, universal_newlines=True, shell=True)
        return
    elif prefix.lower() == 'nextflow':
        cmd = f'{nextflow_path} -version'
        with open(service_log_file, 'a') as sf:
            sf.write(f"{datetime.now().replace(microsecond=0)}: Launching test '{cmd}' command\n")
            sf.write(f"{datetime.now().replace(microsecond=0)}: See {log_file} for details.\n")
        with open(log_file, 'w+') as log_f:
            subprocess.Popen(cmd, stdout=log_f, stderr=subprocess.STDOUT, universal_newlines=True, shell=True)
        return
    elif prefix.lower() == 'path':
        cmd = 'echo $PATH'
        with open(service_log_file, 'a') as sf:
            sf.write(f"{datetime.now().replace(microsecond=0)}: Launching test '{cmd}' command\n")
            sf.write(f"{datetime.now().replace(microsecond=0)}: See {log_file} for details.\n")
        with open(log_file, 'w+') as log_f:
            subprocess.Popen(cmd, stdout=log_f, stderr=subprocess.STDOUT, universal_newlines=True, shell=True)
        return
    elif prefix.lower() == 'home':
        cmd = 'echo $HOME'
        with open(service_log_file, 'a') as sf:
            sf.write(f"{datetime.now().replace(microsecond=0)}: Launching test '{cmd}' command\n")
            sf.write(f"{datetime.now().replace(microsecond=0)}: See {log_file} for details.\n")
        with open(log_file, 'w+') as log_f:
            subprocess.Popen(cmd, stdout=log_f, stderr=subprocess.STDOUT, universal_newlines=True, shell=True)
        return

    # cycle through pipelines if not any of the testing prefixes
    for pipeline in pipelines:
        # if prefix is found then form a command to launch
        if prefix.lower() == pipeline['prefix']:
            # input path is the file itself
            input_path = file
            # generate output path in output directory based on file basename without extension
            output_path = os.path.join(output_dir, log_filename)
            cmd = get_nextflow_run_command(pipeline, input_path, output_path, file)
            with open(service_log_file, 'a') as sf:
                sf.write(f"{datetime.now().replace(microsecond=0)}: Launching pipeline based on prefix: {prefix}. Command: {cmd}\n")
                sf.write(f"{datetime.now().replace(microsecond=0)}: See {log_file} for details.\n")
            with open(log_file, 'w+') as log_f:
                # with open(err_file, 'w+') as err_f:
                # log_f.write(f"Log file working?")
                subprocess.Popen(cmd, stdout=log_f, stderr=subprocess.STDOUT, universal_newlines=True, shell=True, cwd=run_location)
            return

    # if no pipeline found just print that not a correct prefix for the file
    with open(service_log_file, 'a') as sf:
        sf.write(f"{datetime.now().replace(microsecond=0)}: No prefix found. See {log_file} for details.\n\n")
    with open(log_file, 'w+') as log_f:
        subprocess.Popen('echo "Not a correct prefix"', stdout=log_f, stderr=subprocess.STDOUT, universal_newlines=True, shell=True)

## detect file pairs based on possible paired file extensions
# possible file extensions: 
#   - "*_R{1,2}.fastq.gz"
def check_and_detect_pair(file: str, dif_list: list):
    pair_file = []
    # find out if file is ending with "*_R{1,2}.fastq.gz"
    pair_file_1 = re.findall(r"_R(1|2).fastq.gz$", file)
    # if match found
    if len(pair_file_1) > 0:
        pair_file.append(file)
        for file2 in dif_list:
            # find a pair file
            if pair_file_1[0] == '1':
                pair_file_2 = re.findall(r"_R2.fastq.gz$", file2)
            elif pair_file_1[0] == '2':
                pair_file_2 = re.findall(r"_R1.fastq.gz$", file2)
            if len(pair_file_2) > 0:
                # found the paired file, can progress to the pipeline
                pair_file.append(file2)
                break
    return pair_file

## function to monitor the folder in poll_time interval
def file_watcher(dir: str, poll_time: int):

    while True:
        # check if that is the first time the function is running
        if 'watching' not in locals():
            # get original files in the folder
            previous_list = files_in_directory(dir)
            watching = True
            with open(service_log_file, 'a') as sf:
                sf.write(f'{datetime.now().replace(microsecond=0)}: Watching started\n')
        
        # sleep for poll_time
        time.sleep(poll_time)

        # get current files in the folder
        new_list = files_in_directory(dir)
        # find difference between files
        dif_list = compare_filelists(previous_list, new_list)
        # new list is now previous list for next iteration
        previous_list = new_list

        # check if processed files directory exists and create it if not
        os.makedirs(processed_files_location, exist_ok=True)
        # check if run location exists and create it if not
        os.makedirs(run_location, exist_ok=True)

        # if no difference just continue
        if len(dif_list) == 0:
            continue
        else:
            with open(service_log_file, 'a') as sf:
                sf.write(f'{datetime.now().replace(microsecond=0)}: New files detected: {dif_list}\n')

            # cycle through all the new files
            for f in dif_list:
                # check if the file needs a pair and detect it
                try:
                    pair_file = check_and_detect_pair(f, dif_list)
                
                except Exception as e:
                    with open(service_log_file, 'a') as sf:
                        sf.write(f'{datetime.now().replace(microsecond=0)}: An error while trying to find if the file needs a pair and/or finding that pair\n')

                try:
                    # if file needs a pair but for some reason it wasn't found yet (possibly directory read after 1st file was uploaded but 2nd file was not)
                    if len(pair_file) == 1:
                        # deduct the file from previous list (so that it is detected once again until we get a pair)
                        previous_list.remove(pair_file[0])

                    # if file does not need pairs according to possible pair extensions or a pair is already found
                    elif len(pair_file) == 0 or len(pair_file) == 2:
                        # create directory in 'processed_files_location' to move the processed file into
                        # that directory is a filename without extension
                        processed_dir_name = os.path.join(processed_files_location, os.path.splitext(f)[0])
                        os.makedirs(processed_dir_name, exist_ok=True)
                        # get prefix of the file
                        prefix = get_prefix(f)
                        if prefix != 'error':
                            # remove prefix from the filename itself
                            f_no_prefix = f[f.index('_') + 1:]
                        # generate path to the file in the new 'processed_dir_name' directory
                        file_to_pipeline = os.path.join(processed_dir_name, f_no_prefix)
                        # move the file to that new location
                        os.replace(os.path.join(input_dir, f), file_to_pipeline)
                        
                        # move paired file if it is a pair of files
                        if len(pair_file) == 2:
                            # remove 2nd file from the pair from dif_list so that it is not processed again
                            dif_list.remove(pair_file[1])
                            # remove prefix for the filename itself
                            if prefix != 'error':
                                pair_file_no_prefix = pair_file[1][pair_file[1].index('_') + 1:]
                            # generate path to the pair file in the new 'processed_dir_name' directory
                            file_pair_to_pipeline = os.path.join(processed_dir_name, pair_file_no_prefix)
                            # move the fair file to that new location
                            os.replace(os.path.join(input_dir, pair_file[1]), file_pair_to_pipeline)
                        
                        # launch the pipeline based on the input file (or a pair)
                        launch_pipeline(file_to_pipeline, prefix)

                except Exception as e:
                    with open(service_log_file, 'a') as sf:
                        sf.write(f'{datetime.now().replace(microsecond=0)}: An error while launching the pipeline: {e}\n')    

file_watcher(input_dir, 3)