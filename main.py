from cosap import (
    MDUP,
    BamReader,
    Pipeline,
    PipelineRunner,
    Recalibrator,
    VariantCaller,
)
import os, sys
from datetime import datetime
import subprocess
import time
from logging_config import init_log, get_logger
from utils import sort_and_index_bam_files, clearup

TIMESTAMP = datetime.now().strftime("%Y-%m-%d--%H-%M-%S")

# ! Supposed to be initialized.
logger = None

# !GENOME
BAM_FILENAMES = {
    "bowtie": {"tumor": "tumor_bowtie.bam", "germline": "normal_bowtie.bam"},
    "bwa": {"tumor": "tumor_bwa.bam", "germline": "normal_bwa.bam"},
}
BED_FILE = "/cosap_data/High-Confidence_Regions_v1.2.bed"

# !VCF
VCF_DIR = "variants"
if not os.path.exists(VCF_DIR):
    os.makedirs(VCF_DIR)

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
    return BamReader(os.path.join("/cosap_data", BAM_FILENAMES[mapper][state]))


def create_pipeline(mapper: str, caller: str, use_recalibration: bool):
    logger.info("Creating pipeline")
    # Read BAM files.
    germline_bam = get_bam_reader(mapper=mapper, state=GERMLINE)
    tumor_bam = get_bam_reader(mapper=mapper, state=TUMOR)

    # Add duplicate removal.
    logger.info("Adding duplicate removal to pipeline")
    mdup_normal = MDUP(input_step=germline_bam)
    mdup_tumor = MDUP(input_step=tumor_bam)

    if use_recalibration:
        # Add base recalibration.
        logger.info("Adding base recalibration to pipeline")
        basecal_normal = Recalibrator(input_step=germline_bam, bed_file=BED_FILE)
        basecal_tumor = Recalibrator(input_step=tumor_bam, bed_file=BED_FILE)
        germline_input = basecal_normal
        tumor_input = basecal_tumor
    else:
        germline_input = germline_bam
        tumor_input = tumor_bam
    # Add variant caller.
    logger.info("Adding variant caller to pipeline")
    caller = VariantCaller(
        library=caller,
        germline=germline_input,
        tumor=tumor_input,
        bed_file=BED_FILE,
        params={
            "output_vcf": os.path.join(
                VCF_DIR, f"{mapper}_{caller}_{'recal' if use_recalibration else ''}.vcf"
            ),
            "threads": 1,  # Limit to single thread for stability
        },
    )
    pipeline = (
        Pipeline()
        .add(mdup_normal)
        .add(mdup_tumor)
        .add(basecal_normal)
        .add(basecal_tumor)
        .add(caller)
    )
    return pipeline


# ! Pipelines should be run individually
# ! with a new runtime started for each one.
def run_pipeline(mapper: str, caller: str, use_recal: bool):
    FINISHED = {
        True: {
            "somaticsniper": {"bwa": True, "bowtie": False},
            "mutect": {"bwa": False, "bowtie": False},
            "strelka": {"bwa": False, "bowtie": False},
        },
        False: {
            "somaticsniper": {"bwa": False, "bowtie": False},
            "mutect": {"bwa": False, "bowtie": False},
            "strelka": {"bwa": False, "bowtie": False},
        },
    }
    if FINISHED[use_recal][caller][mapper]:
        logger.info(
            f"Already Processed: mapper={mapper}, caller={caller}, use_recal={use_recal}"
        )
        exit(0)
    logger.info(
        f"Configuration: Mapper={mapper}, Caller={caller}, Recalibration={use_recal}"
    )
    try:
        pipeline = create_pipeline(mapper, caller, use_recal)
        config = pipeline.build()
        logger.debug("Running pipeline...")
        pipeline_runner = PipelineRunner()
        START_TIME = time.time()
        logger.info("Started the clock")
        pipeline_runner.run_pipeline(config)
        END_TIME = time.time()
        logger.debug(f"Successfully completed pipeline")
        logger.debug(f"Time complexity: {END_TIME - START_TIME}")
    except Exception as e:
        logger.error(f"Execution failed: {e}")


if __name__ == "__main__":
    init_log(TIMESTAMP)
    logger = get_logger()
    if "--process-bam" in sys.argv:
        sort_and_index_bam_files()
    elif "--clearup" in sys.argv:
        clearup(logs="--logs" in sys.argv)
    elif "--run-pipelines" in sys.argv:
        mappers = ["bwa", "bowtie"]
        callers = ["somaticsniper", "mutect", "strelka"]
        recalibration_options = [True, False]
        subprocess.run(["snakemake", "--cores", "all", "--latency-wait", "60"])
        mapper = input(f"Mapper ({', '.join(mappers)})  ")
        caller = input(f"Caller ({', '.join(callers)})  ")
        use_recal = input(f"Base recalibration? ({', '.join(mappers)}) ")
        run_pipeline(mapper, caller, use_recal)
