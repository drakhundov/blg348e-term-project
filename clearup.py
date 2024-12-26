from datetime import datetime
import os
import sys
import subprocess

TIMESTAMP = datetime.now().strftime("%Y-%m-%d--%H-%M-%S")

CLEARUP_LST = [
    "tmp*",
    "PREPROCESSOR",
    "output*",
    "workflow_dag.svg",
    "*.yaml",
    ".snakemake",
    "TEMP",
]
if "--logs" in sys.argv:
    CLEARUP_LST.extend(
        [
            os.path.join("log", path)
            for path in os.listdir("log")
            if path != f"{TIMESTAMP}.log"
        ]
    )


def clearup():
    for path in CLEARUP_LST:
        subprocess.run(
            f"rm -rf {path}",
            shell=True,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )


if __name__ == "__main__":
    clearup()
