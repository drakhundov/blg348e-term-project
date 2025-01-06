try:
    from cosap import (
        MDUP,
        BamReader,
        Pipeline,
        PipelineRunner,
        Recalibrator,
        VariantCaller,
    )
except Exception as e:
    # Some functionality like clearup
    # Does not require CoSAP.
    pass
import os, sys
from datetime import datetime
import subprocess
import time
from logging_config import init_log, get_logger
from utils import sort_and_index_bam_files, clearup, parse_argv

TIMESTAMP = datetime.now().strftime("%Y-%m-%d--%H-%M-%S")
# ! Must be created if all pipelines are
# ! run in a single session.
BACKUP_DIR_PATH = f"/backup/{TIMESTAMP}"

MAPPERS = ["bwa", "bowtie"]
CALLERS = ["somaticsniper", "mutect", "strelka"]
RECALIBRATION_OPTIONS = [True, False]

# Supposed to be initialized via init_log().
logger = get_logger()

# GENOME
# ! Reference genome although not
# ! specified in the script must
# ! be put into /cosap_data under
# ! Docker environment.
BAM_FILENAMES = {
    "bowtie": {"tumor": "tumor_bowtie.bam", "germline": "normal_bowtie.bam"},
    "bwa": {"tumor": "tumor_bwa.bam", "germline": "normal_bwa.bam"},
}
BED_FILENAME = "/cosap_data/High-Confidence_Regions_v1.2.bed"

# VCF
VCF_DIR = "variants"
if not os.path.exists(VCF_DIR):
    os.makedirs(VCF_DIR)

# Used to designate BAM files.
GERMLINE = 0
TUMOR = 1

# Used to deisgnate pipelines.
FINISHED = True
PENDING = False


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
        basecal_normal = Recalibrator(input_step=germline_bam)
        basecal_tumor = Recalibrator(input_step=tumor_bam)
        germline_input = basecal_normal
        tumor_input = basecal_tumor
    else:
        germline_input = germline_bam
        tumor_input = tumor_bam

    # Add variant caller.
    logger.info("Adding variant caller to pipeline")
    caller = VariantCaller(library=caller, germline=germline_input, tumor=tumor_input)
    pipeline = (
        Pipeline()
        .add(germline_bam)
        .add(tumor_bam)
        .add(mdup_normal)
        .add(mdup_tumor)
        .add(germline_input)
        .add(tumor_input)
        .add(caller)
    )
    return pipeline


# Used to start a new environment for each pipeline
# so that in case some of them fail, we can know
# which ones work and they don't interrupt each other.
def start_pipeline_subprocess(mapper: str, caller: str, use_recal: bool):
    command = [
        sys.executable,  # Path to the Python interpreter
        __file__,  # Path to the current script
        "--run-pipeline",
        f"--mapper={mapper}",
        f"--caller={caller}",
        f"--use-recal={1 if use_recal else 0}",
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        logger.error(f"Pipeline failed: {result.stderr}")
    else:
        logger.info(f"Pipeline succeeded: {result.stdout}")


# Pipelines should be run individually
# with a new runtime started for each one.
def run_pipeline(mapper: str, caller: str, use_recal: bool):
    STATE = {
        "bwa": {
            "somaticsniper": {True: FINISHED, False: FINISHED},
            "mutect": {True: FINISHED, False: PENDING},
            "strelka": {True: PENDING, False: PENDING},
        },
        "bowtie": {
            "somaticsniper": {True: PENDING, False: PENDING},
            "mutect": {True: PENDING, False: PENDING},
            "strelka": {True: PENDING, False: PENDING},
        },
    }
    if STATE[mapper][caller][use_recal] == PENDING:
        init_log(logfile=f"{mapper}_{caller}_{'recal' if use_recal else 'norecal'}")
    else:
        return
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
        #  Backup VCF files.
        subprocess.run(
            [
                "mv",
                "-rn",
                "VCF",
                f"{BACKUP_DIR_PATH}/{mapper}_{caller}_{'recal' if use_recal else 'norecal'}",
            ]
        )
        # Since all produced VCF data is put into the same folder,
        # must ensure different pipelines don't override each other.
        subprocess.run(["rm", "-rf", "VCF"])
    except Exception as e:
        logger.error(f"Execution failed: {e}")
        raise e


if __name__ == "__main__":
    # os.environ["COSAP_LIBRARY_PATH"] = "/cosap_data"
    options = {
        "process-bam": False,
        "clearup": False,
        "run-pipeline": False,
        "use-snake": False,
        "all-pipelines": False,
    }
    parse_argv(sys.argv[1:], options)  # skip file name.
    print(f"Options: {options}")
    if options["process-bam"]:
        init_log(logfile=f"process_bam_{TIMESTAMP}")
        sort_and_index_bam_files("/cosap_data")
    elif options["clearup"]:
        clearup(logs=True if options.get("logs") is not None else False)
    elif options["run-pipeline"]:
        USG = "Usage: --run-pipeline --mapper=<mapper> --caller=<caller> --use-recal=<1|0>."
        if (mapper := options.get("mapper")) is None:
            raise Exception(f"Mapper not specified.\n{USG}")
        elif (caller := options.get("caller")) is None:
            raise Exception(f"Caller not specified.\n{USG}")
        elif (use_recal := options.get("use-recal")) is None:
            raise Exception(f"Recalibration option not specified.\n{USG}")
        use_recal = bool(int(use_recal))
        if options["use-snake"]:
            subprocess.run(["snakemake", "--cores", "all", "--latency-wait", "60"])
        run_pipeline(mapper, caller, use_recal)
    elif options["all-pipelines"]:
        init_log(logfile=f"all_pipelines_{TIMESTAMP}")
        # Create backup folder.
        os.makedirs(BACKUP_DIR_PATH, exist_ok=True)
        for mapper in MAPPERS:
            for caller in CALLERS:
                for use_recal in RECALIBRATION_OPTIONS:
                    start_pipeline_subprocess(mapper, caller, use_recal)
                    clearup(logs=False)
