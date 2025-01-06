from datetime import datetime
import os
import subprocess
from typing import List, Dict
from logging_config import get_logger

TIMESTAMP = datetime.now().strftime("%Y-%m-%d--%H-%M-%S")

logger = get_logger()

CLEARUP_LST = [
    "tmp*",
    "PREPROCESSOR",
    "output*",
    "workflow_dag.svg",
    "*.yaml",
    ".snakemake",
    "TEMP",
    "__pycache__",
]


def clearup(logs: bool):
    if logs:
        CLEARUP_LST.append("log/*")
    for path in CLEARUP_LST:
        subprocess.run(
            f"rm -rf {path}",
            shell=True,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )


def sort_and_index_bam_files(bam_dir: str):
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


def parse_argv(argv: List[str], argdict: Dict = {}) -> Dict:
    for arg in argv:
        exc_msg = f"Argument not recognized: {arg}"
        # arg: str
        if arg[0] != "-":
            raise Exception(exc_msg)
        i = 0
        n = len(arg)
        while arg[i] == "-":
            i += 1
            if i == 3:
                raise Exception(exc_msg)
        if i < n and not arg[i].isalpha():
            raise Exception(exc_msg)
        if (idx := arg.find("=")) != -1:
            key = arg[i:idx]
            if idx >= n:
                raise Exception(exc_msg)
            argdict[key] = arg[idx + 1 :]
        else:
            argdict[arg[i:]] = True
    return argdict
