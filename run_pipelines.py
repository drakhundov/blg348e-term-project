from cosap import (
    MDUP,
    BamReader,
    Pipeline,
    PipelineRunner,
    PipelineKeys,
    Recalibrator,
    VariantCaller,
)
import os, sys
import yaml
from datetime import datetime
from typing import Dict
import logging
import subprocess

TIMESTAMP = datetime.now().strftime("%Y-%m-%d--%H-%M-%S")

# !LOGGING
if not os.path.exists("logs"):
    os.makedirs("logs")
logging.basicConfig(
    filename=f"logs/{TIMESTAMP}.log",
    filemode="w",
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%H:%M:%S",
    level=logging.DEBUG,
)
logger = logging.getLogger(__name__)

# !GENOME
BAM_FILENAMES = {
    "bowtie": {"tumor": "tumor_bowtie.bam", "germline": "normal_bowtie.bam"},
    "bwa": {"tumor": "tumor_bwa.bam", "germline": "normal_bwa.bam"},
}
REF_GENOME = "data/Homo_sapiens_assembly38.fasta"
KNOWN_SITES = [
    "data/1000G_phase1.snps.high_confidence.hg38.vcf.gz",
    "data/Mills_and_1000G_gold_standard.indels.hg38.vcf.gz",
]

# !VCF
VCF_DIR = "variants"

# !CONFIGURATIONS
CONF_DIR = "configurations"
if not os.path.exists(CONF_DIR):
    os.makedirs(CONF_DIR)
logger.info(f"Configuration directory set to: {CONF_DIR}")

# !CLEARUP
# Directories and files to be cleared up (e.g., temp files, configurations).
CLEARUP_LST = [
    "tmp*",
    "PREPROCESSOR",
    "output*",
    "workflow_dag.svg",
    "*.yaml",
    ".snakemake",
]
if "--clearup-logs" in sys.argv:
    CLEARUP_LST.extend(
        [
            os.path.join("logs", path)
            for path in os.listdir("logs")
            if path != f"{TIMESTAMP}.log"
        ]
    )


def clearup():
    for path in CLEARUP_LST:
        logger.info(f"Deleting {path}")
        subprocess.run(
            f"rm -rf {path}",
            shell=True,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )


# !
# Kind of like C++ enum.
GERMLINE = 0
TUMOR = 1


def get_bam_reader(mapper: str, state: int):
    if state == GERMLINE:
        state = "germline"
    elif state == TUMOR:
        state = "tumor"
    else:
        raise Exception('File state not recognized. Use "GERMLINE" or "TUMOR"')
    logger.info(f"Getting BAM reader for {mapper} - {state}")
    return BamReader(os.path.join("data", BAM_FILENAMES[mapper][state]))


def create_config_file(conf_dir: str, config_data: Dict):
    path = os.path.join(CONF_DIR, conf_dir, f"{TIMESTAMP}_config.yaml")
    logger.info(f"Creating config file at {path}")
    with open(path, "w") as config_file:
        yaml.dump(config_data, config_file)
    return path


def create_pipeline(mapper: str, caller: str, use_recalibration: bool):
    logger.info(
        f"Creating pipeline: Mapper={mapper}, Caller={caller}, Recalibration={use_recalibration}"
    )
    # Read BAM files.
    germline_bam = get_bam_reader(mapper=mapper, state=GERMLINE)
    tumor_bam = get_bam_reader(mapper=mapper, state=TUMOR)

    pipeline = Pipeline()

    # Add duplicate removal.
    logger.info("Adding duplicate removal to pipeline")
    mdup_normal = MDUP(input_step=germline_bam, spark=False)
    mdup_tumor = MDUP(input_step=tumor_bam, spark=False)
    pipeline.add(mdup_normal)
    pipeline.add(mdup_tumor)

    if use_recalibration:
        # Add base recalibration.
        logger.info("Adding base recalibration to pipeline")
        basecal_germline = Recalibrator(input_step=mdup_normal)
        basecal_tumor = Recalibrator(input_step=mdup_tumor)
        pipeline.add(basecal_germline)
        pipeline.add(basecal_tumor)
        germline_input = basecal_germline
        tumor_input = basecal_tumor
    else:
        germline_input = mdup_normal
        tumor_input = mdup_tumor
    # Add variant caller
    logger.info("Adding variant caller to pipeline")
    caller = VariantCaller(
        library=caller,
        germline=germline_input,
        tumor=tumor_input,
        params={
            "reference": REF_GENOME,
            "output_vcf": os.path.join(
                VCF_DIR, "{mapper}_{caller}_{'recal' if use_recalibration else ''}.vcf"
            ),
            "threads": 1,  # Limit to single thread for stability
        },
    )

    pipeline.add(caller)
    return pipeline


def run_all_pipelines():
    mappers = ["bwa", "bowtie"]
    callers = ["somaticsniper", "mutect", "strelka"]
    recalibration_options = [True, False]

    total_pipelines = len(mappers) * len(callers) * len(recalibration_options)
    current_pipeline = 0

    for mapper in mappers:
        for caller in callers:
            for use_recal in recalibration_options:
                current_pipeline += 1
                logger.debug(f"PIPELINE {current_pipeline}/{total_pipelines}")
                logger.debug(
                    f"Configuration: Mapper={mapper}, Caller={caller}, Recalibration={use_recal}"
                )
                try:
                    pipeline = create_pipeline(mapper, caller, use_recal)
                    config = pipeline.build()
                    # conf_dir = f"output_{mapper}_{caller}_{'recal' if use_recal else 'norecal'}"
                    # os.makedirs(conf_dir, exist_ok=True)
                    # config_file_path = create_config_file(conf_dir, config)
                    # if not os.path.exists(config_file_path):
                    #     logger.error(
                    #         f"Could not create configuration file: {config_file_path}"
                    #     )
                    #     continue
                    # config[PipelineKeys.WORKDIR] = os.path.dirname(config_file_path)
                    pipeline_runner = PipelineRunner()
                    pipeline_runner.run_pipeline(config)
                    logger.debug(
                        f"Successfully completed pipeline {current_pipeline}/{total_pipelines}"
                    )
                except Exception as e:
                    raise e
                    logger.error(
                        f"Pipeline {current_pipeline}/{total_pipelines} failed: {str(e)}"
                    )
                    continue


if __name__ == "__main__":
    clearup()
    run_all_pipelines()
