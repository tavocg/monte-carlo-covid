from pathlib import Path
from ssl import create_default_context
from urllib.request import urlopen
import certifi

ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT_DIR / "data"

BASE_URL = (
    "https://raw.githubusercontent.com/OxCGRT/covid-policy-dataset"
    "/main/data/subnat_fullwithnotes"
)

DATASETS = [
    "OxCGRT_fullwithnotes_AUS_v1.csv",
    "OxCGRT_fullwithnotes_BRA_v1.csv",
    "OxCGRT_fullwithnotes_CAN_v1.csv",
    "OxCGRT_fullwithnotes_CHN_v1.csv",
    "OxCGRT_fullwithnotes_GBR_v1.csv",
    "OxCGRT_fullwithnotes_IND_v1.csv",
    "OxCGRT_fullwithnotes_USA_v1.csv",
]


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    context = create_default_context(cafile=certifi.where())

    for dataset in DATASETS:
        with urlopen(f"{BASE_URL}/{dataset}", context=context) as response:
            (DATA_DIR / dataset).write_bytes(response.read())


if __name__ == "__main__":
    main()
