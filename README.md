# Nextflow Pipeline Watcher

Python Script that monitors a folder in real time, detects new input files and launches corresponding Nextflow pipeline based on the file prefix.

## Requirements

Python 3 and latest version of Nextflow are required to run the watcher script. Docker or Singularity are needed to run the pipelines.

The script is designed to run with basic installation of Python 3 in virtual environment or directly in the system. `pyyaml` package is used to read .yaml configuration file.

`pyyaml` package can be installed using the following command:

```
pip3 install pyyaml
```

Alternatively, provided `requirement.txt` file can be used to install the necessary dependencies using the following command:

```
pip3 install -r requirements.txt
```


## Configuration

Configuration parameters for the watcher software are set in `config.yaml` file. Those parameters must be set prior to launching the script.

Overview of the parameters:
- nextflow_path: path to the Nextflow installation
- input_dir: path to the watched folder
- output_dir: path to the folder containing results
- log_dir: path to the folder containing logs of the Nextflow runs
- tower_address: IP address of the Nextflow Tower Community deployment.

### Pipelines configuration

Pipeline configuration for each pipeline is set in the same `config.yaml` file in the `pipelines` list parameter. If a parameter is not supplied it will be skipped while forming the Nextflow run command.

Overview of the pipeline-specific parameters:
- name: name of the pipeline
- prefix: prefix
- run_command: path to the pipeline main.nf file or path to the repository containing the pipeline.
- config: path to the pipeline nextflow.config file
- profile: Docker, Singularity of other profile for the pipeline. Example: `- profile: 'docker'`
- version: Nextflow version to use for running the pipeline. Example: `- version: '20.11.0-edge'`
- input_type: specifies type of inputs that pipeline takes. Can be either 'directory' or 'file'. Example: `- input_type: 'directory'`
- input_parameter: name of the input parameter for the pipeline. Example: `- input_parameter: 'input_dir'`
- output_parameter: name of the input parameter for the pipeline. Example: `- output_parameter: 'output_dir'`
- multiple_inputs: if set to `true` the script will process all the inputs with the same prefix at the same time. if set to `false` the script will process all the inputs with independent pipeline runs. `false` by default. Example: `- multiple_inputs: false`
- filetype: will add `--filetype` parameter to the nextflow run command if provided. Can be set to `'find'`, then the Watcher script will attempt to find the filetype automatically based on inputs. Example: `- filetype: 'fastq'`
- with_tower: 'true' if Nextflow Tower Community monitoring is needed for monitoring pipeline runs. Requires 'tower_access_token' and 'tower_address' set in general `config.yaml` parameters. 'false' if Nextflow Tower Community is not needed. Example: `- with_tower: false`
- params: list of pipeline specific parameters. Can be provided here or in `nextflow.config` file supplied in `config` parameter.

## Running the script in Unix (Ubuntu) environment

Script can be run directly in Ubuntu system in background.

If Nextflow Tower Community is used to monitor pipelines' execution, then TOWER_ACCESS_TOKEN environment variable should be set prior to running the script by using the following command:
```
export TOWER_ACCESS_TOKEN=ABCXYZ
```

Then the Watcher script can be run by using the following command:

```
nohup python3 -u watcher.py &
```

### Running the Watcher script as a Systemd service

Alternatively script can be run as a Systemd service using the provided `watcher.service` file as a template. Some system-specific changes are needed in the file prior to running the service:
- WorkingDirectory: path to the folder containing the `watcher.py` script and `config.yaml` file. Example: `/home/ubuntu/pipeline-watcher`
- ExecStart: path to the python3 and `watcher.py` script. Example: `/usr/bin/python3 /home/ubuntu/pipeline-watcher/watcher.py`
- Environment $HOME variable: environment variable set to $HOME. Example: `Environment=HOME=/home/ubuntu`
- Environment $TOWER_ACCESS_TOKEN variable: environment variable with Nextflow Tower access token. Required if Nextflow Tower Community is used to monitor pipelines' execution. Example: `Environment=TOWER_ACCESS_TOKEN=ABCXYZ`

`watcher.service` needs to places in `/etc/systemd/system/` folder, then it can be run with the following command:

```
sudo systemctl start watcher.service
```

## Nextflow Tower Community

The watcher script is designed with Nextflow Tower Community edition that can optionally be used as a way of monitoring Nextflow pipeline runs.

Please visit the [NF Tower Community GitHub page](https://github.com/seqeralabs/nf-tower) for more details and installation instructions.

In order to use the Nextflow Tower Community, you need to obtain TOWER_ACCESS_TOKEN from the successful installation of the software. Prior to running the watcher script, this token needs to be added as an environment variable in the system using the following command:

```
export TOWER_ACCESS_TOKEN=<token>
```

Additionally, the token and Nextflow Tower Community installation IP address needs to be added in the `config.yaml` file (please refer to the instructions above).

Finally, each pipeline that requires Nextflow Tower Community monitoring enabled needs to have `with_tower` parameter set to 'true' in corresponding pipeline configuration in `config.yaml` (please refer to the instruction above). 