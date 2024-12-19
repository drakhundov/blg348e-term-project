from cosap import (
    MDUP,
    BamReader,
    Pipeline,
    PipelineRunner,
    Recalibrator,
    VariantCaller,
)
import os

BAM_FILENAMES = {
    "bowtie": {"tumor": "tumor_bowtie.bam", "normal": "normal_bowtie.bam"},
    "bwa": {"tumor": "tumor_bwa.bam", "normal": "normal_bwa.bam"},
}


REF_GENOME = "path/to/Homo_sapiens_assembly38.fasta"
KNOWN_SITES = [
    "path/to/1000G_phase1.snps.high_confidence.hg38.vcf.gz",
    "path/to/Mills_and_1000G_gold_standard.indels.hg38.vcf.gz",
]

# Used by "get_bam_reader."
NORMAL = 0
TUMOR = 1


def get_bam_reader(mapper: str, state: int):
    if state == NORMAL:
        state = "normal"
    elif state == TUMOR:
        state = "tumor"
    else:
        raise Exception("File state not recognized.")
    return BamReader(os.path.join("data", BAM_FILENAMES[mapper][state]))


def create_pipeline(mapper_type: str, caller_type, use_recalibration: bool):
    # Read BAM files.
    normal_bam = get_bam_reader(mapper=mapper_type, state=NORMAL)
    tumor_bam = get_bam_reader(mapper=mapper_type, state=TUMOR)

    # Add duplicate removal.
    mdup_normal = MDUP(input_step=normal_bam)
    mdup_tumor = MDUP(input_step=tumor_bam)

    pipeline = Pipeline()
    pipeline.add(mdup_normal)
    pipeline.add(mdup_tumor)

    if use_recalibration:
        # Add base recalibration.
        basecal_normal = Recalibrator(
            input_step=mdup_normal, reference=REF_GENOME, known_sites=KNOWN_SITES
        )
        basecal_tumor = Recalibrator(
            input_step=mdup_tumor, reference=REF_GENOME, known_sites=KNOWN_SITES
        )
        pipeline.add(basecal_normal)
        pipeline.add(basecal_tumor)
        normal_input = basecal_normal
        tumor_input = basecal_tumor
    else:
        normal_input = mdup_normal
        tumor_input = mdup_tumor

    # Add variant caller
    caller = VariantCaller(
        library=caller_type,
        normal=normal_input,
        tumor=tumor_input,
        reference=REF_GENOME,
    )
    pipeline.add(caller)
    return pipeline


def run_all_pipelines():
    mappers = ["bwa", "bowtie"]
    callers = ["somaticsniper", "mutect", "strelka"]
    recalibration_options = [True, False]

    for mapper in mappers:
        for caller in callers:
            for use_recal in recalibration_options:
                print(
                    f"\nRunning pipeline: Mapper={mapper}, Caller={caller}, Recalibration={'Yes' if use_recal else 'No'}"
                )
                pipeline = create_pipeline(mapper, caller, use_recal)
                config = pipeline.build()
                output_dir = (
                    f"output_{mapper}_{caller}_{'recal' if use_recal else 'norecal'}"
                )
                os.makedirs(output_dir, exist_ok=True)
                pipeline_runner = PipelineRunner(output_dir=output_dir)
                pipeline_runner.run_pipeline(config)


if __name__ == "__main__":
    run_all_pipelines()
