from datasets import DATA_DIR, DATASETS
import pandas as pd
import numpy as np
from pathlib import Path


def main():
    dataset_paths = [DATA_DIR / dataset for dataset in DATASETS]
    print(dataset_paths)


def load_csv(path: Path) -> pd.DataFrame:
    cols = ["CountryName", "CountryCode", "Jurisdiction", "Date", "ConfirmedCases"]
    df = pd.read_csv(path, usecols=cols)

    # Se cargan únicamente las filas donde se mide el total nacional del país.
    df = df[df["Jurisdiction"].eq("NAT_TOTAL")].copy()

    # La columna 'Date' es una string con la fecha en formato `%Y%m%d`.
    df["date"] = pd.to_datetime(df["Date"].astype(str), format="%Y%m%d")

    # Como estamos cargando un CSV, los casos confirmados se cargan como string,
    # los convertimos a numeric.
    df["confirmed_cases"] = pd.to_numeric(df["ConfirmedCases"], errors="coerce")

    # Depuramos el dataframe, ordenamos por fecha y eliminamos los días
    # repetidos.
    df = (
        df.sort_values("date")
        .drop_duplicates(subset=["CountryCode", "date"], keep="last")
        .reset_index(drop=True)
    )

    # Los dataset no tienen los casos nuevos por día, únicamente el total,
    # entonces:
    df["observed_new_cases"] = (
        df["confirmed_cases"]
        .diff()  # Obtenemos el delta de la file anterior.
        .fillna(df["confirmed_cases"])  # Si el delta es NaN, asignamos casos.
        .clip(lower=0)  # No puede ser menor a cero.
        .round()  # Tiene que ser un número entero.
    )

    # Producimos mejores resultados si suavizamos al tomar...
    smoothed = df["observed_new_cases"].rolling(30, min_periods=1, center=False).mean()
    previous = smoothed.shift(5)
    rt = (smoothed / previous).replace([np.inf, -np.inf], np.nan)
    df["Rt"] = rt.fillna(1.0).clip(lower=0.0, upper=2.0)

    first_case = df.index[df["observed_new_cases"].ge(100)]
    if len(first_case) == 0:
        first_case = df.index[df["observed_new_cases"].gt(0)]
    if len(first_case) == 0:
        return df.iloc[0:0].copy()
    return df.loc[first_case[0] :].reset_index(drop=True)


if __name__ == "__main__":
    main()
