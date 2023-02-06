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
error_files_location = os.path.join(processed_files_location, 'error')
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
def get_nextflow_run_command(pipeline, input_path, output_path):
    try:
        cmd = ''
        # check if there is a version supplied
        if 'version' in pipeline:
            if pipeline['version']:
                cmd = f"NXF_VER={pipeline['version']} {nextflow_path} run"
            else:
                cmd = f"{nextflow_path} run"
        # add main pipeline command
        cmd += f" {pipeline['run_command']}"
        # add name if supplied
        if 'name' in pipeline:
            if pipeline['name']:
                cmd += f" -name {pipeline['name']}"
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
            input_parameter_added = False

            ## first check if multiple inputs is True, then it is definitely directory as input
            if 'multiple_inputs' in pipeline:
                if pipeline['multiple_inputs'] == True:
                    cmd += f" --{pipeline['input_parameter']} {input_path}"
                    input_parameter_added = True

            # if input parameter is not added yet check input type
            if not input_parameter_added:
                # if 'input_type' parameter is provided
                if 'input_type' in pipeline:
                    # input parameter is a directory, use the provided input path
                    if pipeline['input_type'] == 'directory':
                        # pipeline_input_dir = os.path.abspath(os.path.join(input_path, os.pardir))
                        cmd += f" --{pipeline['input_parameter']} {input_path}"
                        input_parameter_added = True
                    # input parameter is a single file, use the first file from the provided input path children
                    else:
                        # get the first file in the input path directory
                        input_file_path = os.path.join(input_path, os.listdir(input_path)[0])
                        cmd += f" --{pipeline['input_parameter']} {input_file_path}"
                        input_parameter_added = True
            
            # if input_parameter is still not added yet then add it with input_path directly
            if not input_parameter_added:
                cmd += f" --{pipeline['input_parameter']} {input_path}"
                input_parameter_added = True
                
        # check for output parameter name and append it
        if 'output_parameter' in pipeline:
            if pipeline['output_parameter']:
                cmd += f" --{pipeline['output_parameter']} {output_path}"

        ## filetype unique parameter if provided
        if 'filetype' in pipeline:
            if pipeline['filetype']:
                if pipeline['filetype'] == 'find':
                    input_file_path = os.listdir(input_path)[0]
                    ftype = os.path.basename(input_file_path).split('.')[::-1][0]
                    if ftype == 'gz':
                        ftype = os.path.basename(input_file_path).split('.')[::-1][1]
                    cmd += f" --filetype {ftype}"
                else:
                    cmd += f" --filetype {pipeline['filetype']}"
        
        # add background parameter for nextflow run
        cmd += " -bg"
        return cmd
    except Exception as e:
        return 'error'

# function to launch pipelines
def launch_pipeline(input_path: str, output_path: str, prefix: str):
    original_location = os.getcwd()
    # get basename of the input path
    input_path_basename = os.path.basename(input_path)
    # log filename
    log_filename_basename = f"{os.path.splitext(input_path_basename)[0]}"
    # get log and err file names
    log_file = os.path.join(log_dir, log_filename_basename + '.log')
    err_file = os.path.join(log_dir, log_filename_basename + '.err')

    with open(service_log_file, 'a') as sf:
        sf.write(f"{datetime.now().replace(microsecond=0)}: Processing input path: {input_path}\n")

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
            cmd = get_nextflow_run_command(pipeline, input_path, output_path)
            with open(service_log_file, 'a') as sf:
                sf.write(f"{datetime.now().replace(microsecond=0)}: Launching pipeline based on prefix: {prefix}. Command: {cmd}\n")
                sf.write(f"{datetime.now().replace(microsecond=0)}: See {log_file} for details.\n")
            with open(log_file, 'w+') as log_f:
                # with open(err_file, 'w+') as err_f:
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
    
    ## find out if file is ending with "*_R{1,2}.fastq.gz"
    fastq_index = file.find('fastq')
    if fastq_index != -1:
        # file basename without the ending
        file_basename = file[0:fastq_index - 4]
        pair_file_1 = re.findall(r"_R(1|2).fastq.gz$", file)
        # if match found
        if len(pair_file_1) > 0:
            pair_file.append(file)
            # get the pair file name based on the original file basename without the ending
            pair_file_name = ''
            if pair_file_1[0] == '1':
                pair_file_name = f"{file_basename}_R2.fastq.gz"
            elif pair_file_1[0] == '2':
                pair_file_name = f"{file_basename}_R1.fastq.gz"
            for file2 in dif_list:
                # find a pair file
                if file2 == pair_file_name:
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
        # check if error files directory and create it if not
        os.makedirs(error_files_location, exist_ok=True)

        # if no difference just continue
        if len(dif_list) == 0:
            continue
        else:
            with open(service_log_file, 'a') as sf:
                sf.write(f'{datetime.now().replace(microsecond=0)}: New files detected: {dif_list}\n')

            # cycle through all the new files
            for f in dif_list:
                ### get prefix of that file
                prefix = get_prefix(f)

                ## check if prefix is error and process it accordingly first
                if prefix == 'error':
                    # generate path to the file in the error files directory
                    error_file_path = os.path.join(error_files_location, f)
                    # move the file to that new location
                    os.replace(os.path.join(input_dir, f), error_file_path)
                    # print in service log that a file did not have correct prefix
                    with open(service_log_file, 'a') as sf:
                        sf.write(f'{datetime.now().replace(microsecond=0)}: Error while acquiring prefix for: {f}. File moved to the error directory.\n')
                    # move on to the next file
                    continue

                ## prefix is correct

                ### check if the file needs a pair
                pair_file = check_and_detect_pair(f, dif_list)
                ## if file needs a pair but for some reason it was n ot found yet (possibly directory read after 1st file was uploaded but 2nd file was not)
                if len(pair_file) == 1:
                    # deduct the file from previous list (so that it is detected once again until we get a pair)
                    previous_list.remove(pair_file[0])
                    # print in service log that a file needs a pair but nothing was detected yet
                    with open(service_log_file, 'a') as sf:
                        sf.write(f'{datetime.now().replace(microsecond=0)}: Missing pair for: {f}. File skipped.\n')
                    # move on to the next file
                    continue

                ## file does not need pairs according to possible pair extensions or a pair is already found

                ### check if a single input is processed per run or all the files with the same prefix are sent to the pipeline at the same time according to configuration
                multiple_inputs = False
                ## find the prefix first in the configurations
                for pipeline in pipelines:
                    if prefix.lower() == pipeline['prefix']:
                        # prefix found, check if a run per file is required
                        if 'multiple_inputs' in pipeline:
                            # if a pipeline is running per single input
                            if pipeline['multiple_inputs'] == True:
                                multiple_inputs = True
                            else:
                                multiple_inputs = False
                        break

                ## get current time and date
                current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                ## get output path with output_dir parameter + time
                output_path = os.path.join(output_dir, f"{prefix}_{current_time}")
                ## copy the current file into processed directory
                # get filename without extension
                f_no_extension = os.path.splitext(f)[0]
                # create directory in 'processed_files_location' to move the processed file(s) into
                # directory name is the prefix itself + filename without extension + datetime for single input
                if not multiple_inputs:
                    processed_dir_path = os.path.join(processed_files_location, f"{prefix}_{current_time}")
                # directory name is the prefix itself + datetime for multiple inputs
                else:
                    processed_dir_path = os.path.join(processed_files_location, f"{prefix}_{current_time}")
                    # check if that directory exists and add a number if needed
                    if os.path.exists(processed_dir_path):
                        i = 1
                        while i <= 100: # to avoid infinite loop
                            processed_dir_path = os.path.join(processed_files_location, f"{prefix}_{current_time}_{i}")
                            if os.path.exists(processed_dir_path):
                                i += 1
                            else:
                                break

                # create that directory if not exists
                os.makedirs(processed_dir_path, exist_ok=True)                          
                # move the file with no prefix to that new location
                os.replace(os.path.join(input_dir, f), os.path.join(processed_dir_path, f[f.index('_') + 1:]))
                
                # move paired file if it is a pair of files
                if len(pair_file) == 2:
                    # remove 2nd file from the pair from dif_list so that it is not processed again
                    dif_list.remove(pair_file[1])
                    # move the fair file to that new location
                    os.replace(os.path.join(input_dir, pair_file[1]), os.path.join(processed_dir_path, pair_file[1][pair_file[1].index('_') + 1:]))
                
                ## if multiple inputs with the same prefix are processed with a single pipeline run
                # copy all those inputs into the processed directory
                if multiple_inputs:
                    ## find all other files with the same prefix in the directory
                    for f2 in dif_list:
                        if f != f2: # ignore file itself
                            prefix_2 = get_prefix(f2)
                            # compare it with prefix in question
                            if prefix == prefix_2:
                                ## if prefix is the same
                                # find pair files for the new file
                                pair_file_2 = check_and_detect_pair(f2, dif_list)
                                # if both files do not need pair just copying over the new file into the processed folder is enough
                                if len(pair_file) == 0 and len(pair_file_2) == 0:
                                    # move the file without prefix to that new location
                                    os.replace(os.path.join(input_dir, f2), os.path.join(processed_dir_path, f2[f2.index('_') + 1:]))
                                    # remove that file from dif_list to avoid double processing
                                    dif_list.remove(f2)

                                # if both files have a pair then copy both the new file and its pair
                                elif len(pair_file) == 2 and len(pair_file_2) == 2:
                                        # move the file without prefix to that new location
                                        os.replace(os.path.join(input_dir, f2), os.path.join(processed_dir_path, f2[f2.index('_') + 1:]))
                                        # remove that file from dif_list to avoid double processing
                                        dif_list.remove(f2)
                                        # move the fair file to that new location
                                        os.replace(os.path.join(input_dir, pair_file_2[1]), os.path.join(processed_dir_path, pair_file_2[1][pair_file_2[1].index('_') + 1:]))
                                        # remove 2nd file from the pair from dif_list so that it is not processed again
                                        dif_list.remove(pair_file_2[1])



                ## launch the pipeline based on the input path
                try:
                    launch_pipeline(processed_dir_path, output_path, prefix)
                except Exception as e:
                    with open(service_log_file, 'a') as sf:
                        sf.write(f'{datetime.now().replace(microsecond=0)}: An error while launching the pipeline for {processed_dir_path}: {e}\n')

if __name__ == "__main__":
    file_watcher(input_dir, 5)