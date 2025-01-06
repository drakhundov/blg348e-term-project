# Abdul Akhundzada & Clara Choukroun

## 1. Download CoSAP

To download and install `cosap`, you can use the following commands:

```sh
git clone https://github.com/MBaysanLab/cosap.git
```

## 2. Pull the Docker environment

```sh
docker pull itubioinformatics/cosap
```

## 3. Activate the Docker environment

```sh
# Supposed to be in the project directory.
docker run -it -v $PWD/cosap_data:/cosap_data -v $PWD:/app itubioinformatics/cosap

cd /app
```

## Usage

```
--run-pipeline --mapper=[somaticsniper, mutect, strelka]
               --caller=[bwa, bowtie]
               --use-recal=[0, 1]
               [--use-snake]

        Runs specified pipeline.

    --use-snake
        Use snakemake to increase latency and involve more cores.


--all-pipelines
        Try out all possible configurations separately.


--clearup [--logs]
        Clear all the temporary data (e.g., PREPROCESSOR, config files, etc.).

    --logs
        Delete all logs.


--process-bam
        Sort and index the bam files in the /cosap_data directory.
```
