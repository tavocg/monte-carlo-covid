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

COUNTRIES = (
    "AUS",
    "BRA",
    "CAN",
    "CHN",
    "GBR",
    "IND",
    "USA",
)


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    context = create_default_context(cafile=certifi.where())

    for country in COUNTRIES:
        filename = f"OxCGRT_fullwithnotes_{country}_v1.csv"
        with urlopen(f"{BASE_URL}/{filename}", context=context) as response:
            (DATA_DIR / filename).write_bytes(response.read())


if __name__ == "__main__":
    main()
