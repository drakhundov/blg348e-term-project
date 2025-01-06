# Abdul Akhundzada & Clara Choukroun

## 1. Download CoSAP

To download and install `cosap`, you can use the following commands:

```sh
git clone https://github.com/MBaysanLab/cosap.git
```

## 2. Download Reference Genome

```sh
gsutil -m cp \
  "gs://genomics-public-data/resources/broad/hg38/v0/1000G_phase1.snps.high_confidence.hg38.vcf.gz" \
  "gs://genomics-public-data/resources/broad/hg38/v0/1000G_phase1.snps.high_confidence.hg38.vcf.gz.tbi" \
  "gs://genomics-public-data/resources/broad/hg38/v0/Homo_sapiens_assembly38.dbsnp138.vcf" \
  "gs://genomics-public-data/resources/broad/hg38/v0/Homo_sapiens_assembly38.dbsnp138.vcf.idx" \
  "gs://genomics-public-data/resources/broad/hg38/v0/Homo_sapiens_assembly38.dict" \
  "gs://genomics-public-data/resources/broad/hg38/v0/Homo_sapiens_assembly38.fasta" \
  "gs://genomics-public-data/resources/broad/hg38/v0/Homo_sapiens_assembly38.fasta.64.alt" \
  "gs://genomics-public-data/resources/broad/hg38/v0/Homo_sapiens_assembly38.fasta.64.amb" \
  "gs://genomics-public-data/resources/broad/hg38/v0/Homo_sapiens_assembly38.fasta.64.ann" \
  "gs://genomics-public-data/resources/broad/hg38/v0/Homo_sapiens_assembly38.fasta.64.bwt" \
  "gs://genomics-public-data/resources/broad/hg38/v0/Homo_sapiens_assembly38.fasta.64.pac" \
  "gs://genomics-public-data/resources/broad/hg38/v0/Homo_sapiens_assembly38.fasta.64.sa" \
  "gs://genomics-public-data/resources/broad/hg38/v0/Homo_sapiens_assembly38.fasta.fai" \
  "gs://genomics-public-data/resources/broad/hg38/v0/Mills_and_1000G_gold_standard.indels.hg38.vcf.gz" \
  "gs://genomics-public-data/resources/broad/hg38/v0/Mills_and_1000G_gold_standard.indels.hg38.vcf.gz.tbi" \
  .
```

## 3. Download BAM files

https://drive.google.com/drive/folders/1EiPgZZ7nhHNKmf1_KlSOOsiIgsJAgv8s

## 4. Pull the Docker environment

```sh
docker pull itubioinformatics/cosap
```

## 5. Activate the Docker environment in the project folder

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
