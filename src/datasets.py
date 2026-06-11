from pathlib import Path
from ssl import create_default_context
from urllib.request import urlopen

import certifi
import numpy as np
import pandas as pd

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


def download_datasets():
    """Descarga los datasets configurados en DATASETS dentro de DATA_DIR."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    context = create_default_context(cafile=certifi.where())

    for dataset in DATASETS:
        with urlopen(f"{BASE_URL}/{dataset}", context=context) as response:
            (DATA_DIR / dataset).write_bytes(response.read())


def load_datasets(
    data_dir: Path = DATA_DIR,
    rt_window: int = 30,
    rt_lag: int = 5,
    rt_min: float = 0.0,
    rt_max: float = 2.0,
    min_daily_cases: int = 100,
) -> pd.DataFrame:
    """Carga todos los datasets locales y los concatena en un solo dataframe."""
    dataset_paths = [data_dir / dataset for dataset in DATASETS]
    dataframes = [
        load_csv(
            path,
            rt_window=rt_window,
            rt_lag=rt_lag,
            rt_min=rt_min,
            rt_max=rt_max,
            min_daily_cases=min_daily_cases,
        )
        for path in dataset_paths
    ]
    return pd.concat(dataframes, ignore_index=True)


def load_csv(
    path: Path,
    rt_window: int = 30,
    rt_lag: int = 5,
    rt_min: float = 0.0,
    rt_max: float = 2.0,
    min_daily_cases: int = 100,
) -> pd.DataFrame:
    """Carga un CSV de OxCGRT y calcula casos nuevos diarios y Rt."""
    cols = ["CountryName", "CountryCode", "Jurisdiction", "Date", "ConfirmedCases"]
    df = pd.read_csv(path, usecols=cols)

    # Se cargan únicamente las filas donde se mide el total nacional del país.
    df = df[df["Jurisdiction"].eq("NAT_TOTAL")].copy()

    # La columna 'Date' es una string con la fecha en formato `%Y%m%d`.
    df["date"] = pd.to_datetime(df["Date"].astype(str), format="%Y%m%d")

    # Como estamos cargando un CSV, los casos confirmados se cargan como string.
    # Los convertimos a numeric para poder operar con ellos.
    df["confirmed_cases"] = pd.to_numeric(df["ConfirmedCases"], errors="coerce")

    # Depuramos el dataframe, ordenamos por fecha y eliminamos los días
    # repetidos.
    df = (
        df.sort_values("date")
        .drop_duplicates(subset=["CountryCode", "date"], keep="last")
        .reset_index(drop=True)
    )

    # Los datasets no tienen los casos nuevos por día, únicamente el total
    # acumulado. Calculamos el incremento diario a partir de esa serie acumulada.
    df["observed_new_cases"] = (
        df["confirmed_cases"]
        .diff()  # Obtenemos el delta de la fila anterior.
        .fillna(df["confirmed_cases"])  # Si el delta es NaN, asignamos casos.
        .clip(lower=0)  # No puede ser menor a cero.
        .round()  # Tiene que ser un número entero.
    )

    # Estimamos Rt como una razón entre el promedio móvil reciente de casos
    # nuevos y el promedio móvil de cinco días antes. El suavizado reduce ruido
    # de reportes atrasados, correcciones y saltos puntuales del dataset.
    smoothed = (
        df["observed_new_cases"]
        .rolling(rt_window, min_periods=1, center=False)
        .mean()
    )
    previous = smoothed.shift(rt_lag)
    rt = (smoothed / previous).replace([np.inf, -np.inf], np.nan)
    df["Rt"] = rt.fillna(1.0).clip(lower=rt_min, upper=rt_max)

    # Recortamos la serie para empezar cuando la epidemia ya tiene una señal
    # mínima observable. Si nunca llega a 100 casos diarios, usamos el primer
    # día con casos; si tampoco hay casos, devolvemos un dataframe vacío.
    first_case = df.index[df["observed_new_cases"].ge(min_daily_cases)]
    if len(first_case) == 0:
        first_case = df.index[df["observed_new_cases"].gt(0)]
    if len(first_case) == 0:
        return df.iloc[0:0].copy()
    return df.loc[first_case[0] :].reset_index(drop=True)


if __name__ == "__main__":
    download_datasets()
