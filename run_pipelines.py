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
import logging
import subprocess
import time

TIMESTAMP = datetime.now().strftime("%Y-%m-%d--%H-%M-%S")

# !LOGGING
if not os.path.exists("log"):
    os.makedirs("log")
logging.basicConfig(
    filename=f"log/{TIMESTAMP}.log",
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
BED_FILE = "/cosap_data/High-Confidence_Regions_v1.2.bed"

# !VCF
VCF_DIR = "variants"
if not os.path.exists(VCF_DIR):
    os.makedirs(VCF_DIR)
logger.info(f"Variants directory set to: {VCF_DIR}")

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

    pipeline = Pipeline()

    # Add duplicate removal.
    logger.info("Adding duplicate removal to pipeline")
    mdup_normal = MDUP(input_step=germline_bam)
    mdup_tumor = MDUP(input_step=tumor_bam)
    pipeline.add(mdup_normal)
    pipeline.add(mdup_tumor)

    if use_recalibration:
        # Add base recalibration.
        logger.info("Adding base recalibration to pipeline")
        basecal_germline = Recalibrator(input_step=germline_bam, bed_file=BED_FILE)
        basecal_tumor = Recalibrator(input_step=tumor_bam, bed_file=BED_FILE)
        pipeline.add(basecal_germline)
        pipeline.add(basecal_tumor)
        germline_input = basecal_germline
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
    pipeline.add(caller)
    return pipeline


def sort_and_index_bam_files():
    bam_dir = "/cosap_data"
    for bam_file in os.listdir(bam_dir):
        if bam_file.endswith(".bam"):
            bam_path = os.path.join(bam_dir, bam_file)
            sorted_bam_path = os.path.join(bam_dir, f"sorted_{bam_file}")
            logger.info(f"Sorting {bam_path}")
            subprocess.run(["samtools", "sort", bam_path, "-o", sorted_bam_path])
            logger.info(f"Indexing {sorted_bam_path}")
            subprocess.run(["samtools", "index", sorted_bam_path])
            os.rename(sorted_bam_path, bam_path)
            os.rename(f"{sorted_bam_path}.bai", f"{bam_path}.bai")
            logger.info(f"Processed {bam_file}")


def run_all_pipelines():
    mappers = ["bwa", "bowtie"]
    callers = ["somaticsniper", "mutect", "strelka"]
    recalibration_options = [True, False]

    total_pipelines = len(mappers) * len(callers) * len(recalibration_options)
    current_pipeline = 0

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

    for use_recal in recalibration_options:
        for caller in callers:
            for mapper in mappers:
                current_pipeline += 1
                if FINISHED[use_recal][caller][mapper]:
                    logger.info(
                        f"Already Processed: ({current_pipeline}) mapper={mapper}, caller={caller}, use_recal={use_recal}"
                    )
                    continue
                logger.debug(f"PIPELINE {current_pipeline}/{total_pipelines}")
                logger.info(
                    f"Configuration: Mapper={mapper}, Caller={caller}, Recalibration={use_recal}"
                )
                try:
                    pipeline = create_pipeline(mapper, caller, use_recal)
                    config = pipeline.build()
                    logger.debug("Running pipeline.")
                    pipeline_runner = PipelineRunner()
                    START_TIME = time.time()
                    logger.info("Started the clock")
                    pipeline_runner.run_pipeline(config)
                    END_TIME = time.time()
                    logger.debug(
                        f"Successfully completed pipeline {current_pipeline}/{total_pipelines}"
                    )
                    logger.debug(f"Time complexity: {END_TIME - START_TIME}")
                except Exception as e:
                    logger.error(
                        f"Pipeline {current_pipeline}/{total_pipelines} failed: {e}"
                    )
                    continue


if __name__ == "__main__":
    if "--process-bam" in sys.argv:
        sort_and_index_bam_files()
    subprocess.run(["snakemake", "--cores", "all", "--latency-wait", "60"])
    run_all_pipelines()
