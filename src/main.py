from pathlib import Path

import numpy as np
import pandas as pd

from datasets import DATA_DIR, DATASETS


def main():
    dataset_paths = [DATA_DIR / dataset for dataset in DATASETS]
    dataframes = [load_csv(path) for path in dataset_paths]
    df = pd.concat(dataframes, ignore_index=True)

    print(df[["CountryCode", "date", "observed_new_cases", "Rt"]])


def load_csv(path: Path) -> pd.DataFrame:
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
    smoothed = df["observed_new_cases"].rolling(30, min_periods=1, center=False).mean()
    previous = smoothed.shift(5)
    rt = (smoothed / previous).replace([np.inf, -np.inf], np.nan)
    df["Rt"] = rt.fillna(1.0).clip(lower=0.0, upper=2.0)

    # Recortamos la serie para empezar cuando la epidemia ya tiene una señal
    # mínima observable. Si nunca llega a 100 casos diarios, usamos el primer
    # día con casos; si tampoco hay casos, devolvemos un dataframe vacío.
    first_case = df.index[df["observed_new_cases"].ge(100)]
    if len(first_case) == 0:
        first_case = df.index[df["observed_new_cases"].gt(0)]
    if len(first_case) == 0:
        return df.iloc[0:0].copy()
    return df.loc[first_case[0] :].reset_index(drop=True)


if __name__ == "__main__":
    main()
