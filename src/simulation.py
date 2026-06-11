from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from datasets import DATA_DIR, load_datasets


@dataclass(frozen=True)
class Config:
    """Parámetros modificables para preparar datos y correr simulaciones."""

    n_simulations: int = 100
    n_extra_days: int = 30
    mean_delay: float = 5
    dispersion_delay: float = 2
    rt_window: int = 7
    rt_lag: int = 5
    rt_min: float = 0.0
    rt_max: float = 2.0
    min_daily_cases: int = 100


def infection_delay_probabilities(
    max_delay: int,
    mean_delay: float = 5,
    dispersion: float = 2,
) -> np.ndarray:
    """Probabilidades para retrasos 1..max_delay de la binomial negativa."""
    # Convertimos la media y dispersión en la probabilidad de éxito de la
    # binomial negativa.
    p = dispersion / (dispersion + mean_delay)

    # Guardamos la probabilidad de cada retraso posible. La posición cero
    # representa un retraso de un día, porque los contagios secundarios se
    # agregan desde `day + 1`.
    probs = np.empty(max_delay, dtype=float)
    probs[0] = p**dispersion

    # Calculamos el resto de probabilidades de forma recursiva para evitar
    # factoriales grandes y mantener el cálculo estable.
    for idx in range(1, max_delay):
        failures = idx - 1
        probs[idx] = probs[idx - 1] * (failures + dispersion) / idx * (1 - p)

    return probs


def simulate_epidemic(
    rt_values: np.ndarray,
    initial_cases: int,
    n_extra_days: int = 30,
    mean_delay: float = 5,
    dispersion_delay: float = 2,
    seed: int | None = None,
) -> np.ndarray:
    """Simula casos nuevos diarios con transmisión Poisson y retrasos aleatorios."""
    # Usamos un generador local para poder reproducir simulaciones cuando se
    # pasa una semilla.
    rng = np.random.default_rng(seed)

    # Simulamos los días observados en Rt y agregamos días extra para permitir
    # que aparezcan contagios secundarios con retraso.
    n_days = len(rt_values)
    total_days = n_days + n_extra_days

    # Esta serie contiene los casos nuevos simulados por día. La epidemia se
    # inicia con los casos iniciales en el primer día.
    simulated_new_cases = np.zeros(total_days, dtype=np.int64)
    simulated_new_cases[0] = initial_cases

    # Precalculamos la distribución de retrasos entre infección y observación
    # de casos secundarios.
    delay_probs = infection_delay_probabilities(
        total_days,
        mean_delay=mean_delay,
        dispersion=dispersion_delay,
    )

    for day in range(n_days):
        # Cada persona infectada hoy puede generar contagios secundarios según
        # el Rt estimado para ese día.
        infected_today = simulated_new_cases[day]
        if infected_today <= 0:
            continue

        # El total de casos secundarios se modela con una Poisson centrada en
        # infected_today * Rt.
        total_secondary_cases = rng.poisson(lam=infected_today * rt_values[day])
        if total_secondary_cases <= 0:
            continue

        # Solo distribuimos casos en días futuros que todavía están dentro del
        # arreglo simulado.
        remaining_days = total_days - day - 1
        if remaining_days <= 0:
            continue

        # Como la distribución de retrasos puede extenderse más allá del
        # horizonte simulado, conservamos únicamente la masa de probabilidad
        # que cabe en los días restantes.
        valid_probs = delay_probs[:remaining_days]
        valid_probability = min(1.0, float(valid_probs.sum()))

        # Algunos contagios secundarios pueden caer fuera del horizonte de
        # simulación; esta binomial conserva solo los que sí pueden observarse.
        valid_secondary_cases = rng.binomial(
            n=int(total_secondary_cases),
            p=float(valid_probability),
        )
        if valid_secondary_cases <= 0:
            continue

        # Distribuimos los casos secundarios válidos entre los días futuros
        # usando las probabilidades de retraso normalizadas.
        valid_probs_sum = valid_probs.sum()
        delay_counts = rng.multinomial(
            n=int(valid_secondary_cases),
            pvals=valid_probs / valid_probs_sum,
        )
        simulated_new_cases[day + 1 : day + 1 + remaining_days] += delay_counts

    return simulated_new_cases


def load_all_timeseries(
    data_dir: Path = DATA_DIR,
    config: Config | None = None,
) -> pd.DataFrame:
    """Carga todas las series de tiempo usando los parámetros de configuración."""
    config = config or Config()

    # Delegamos la preparación de cada CSV al módulo de datasets, pero los
    # valores que suelen ajustarse en pruebas salen desde Config.
    return load_datasets(
        data_dir=data_dir,
        rt_window=config.rt_window,
        rt_lag=config.rt_lag,
        rt_min=config.rt_min,
        rt_max=config.rt_max,
        min_daily_cases=config.min_daily_cases,
    )


def run_country_simulations(
    country_df: pd.DataFrame,
    config: Config,
    seed_offset: int = 0,
) -> tuple[pd.DataFrame, dict[str, object]]:
    """Corre simulaciones Monte Carlo para un país y resume sus resultados."""
    # Ordenamos por fecha para que Rt y los casos iniciales sigan la secuencia
    # temporal correcta.
    country_df = country_df.sort_values("date").reset_index(drop=True)
    rt_values = country_df["Rt"].to_numpy(dtype=float)
    initial_cases = max(1, int(country_df.loc[0, "observed_new_cases"]))

    # Ejecutamos varias simulaciones independientes. El seed_offset evita que
    # dos países usen las mismas semillas cuando se corre todo el conjunto.
    simulations = np.array(
        [
            simulate_epidemic(
                rt_values=rt_values,
                initial_cases=initial_cases,
                n_extra_days=config.n_extra_days,
                mean_delay=config.mean_delay,
                dispersion_delay=config.dispersion_delay,
                seed=seed_offset + i,
            )
            for i in range(config.n_simulations)
        ]
    )

    # La simulación puede extenderse más allá del periodo observado, por eso
    # construimos fechas para todos los días simulados.
    dates = pd.date_range(
        start=country_df["date"].iloc[0],
        periods=simulations.shape[1],
        freq="D",
    )
    cumulative = np.cumsum(simulations, axis=1)

    # Resumimos la distribución diaria de casos y de acumulados con promedios
    # y percentiles.
    summary = pd.DataFrame(
        {
            "country_code": country_df["CountryCode"].iloc[0],
            "country_name": country_df["CountryName"].iloc[0],
            "date": dates,
            "mean": np.mean(simulations, axis=0),
            "p05": np.percentile(simulations, 5, axis=0),
            "p25": np.percentile(simulations, 25, axis=0),
            "median": np.percentile(simulations, 50, axis=0),
            "p75": np.percentile(simulations, 75, axis=0),
            "p95": np.percentile(simulations, 95, axis=0),
            "cumulative_p25": np.percentile(cumulative, 25, axis=0),
            "cumulative_mean": np.mean(cumulative, axis=0),
            "cumulative_median": np.percentile(cumulative, 50, axis=0),
            "cumulative_p75": np.percentile(cumulative, 75, axis=0),
        }
    )

    # Calculamos métricas agregadas por simulación para comparar países.
    peak_indices = np.argmax(simulations, axis=1)
    peak_dates = pd.Series(dates[peak_indices])
    peak_sizes = np.max(simulations, axis=1)
    final_cumulative = cumulative[:, -1]
    metrics = {
        "country_code": country_df["CountryCode"].iloc[0],
        "country_name": country_df["CountryName"].iloc[0],
        "start_date": country_df["date"].iloc[0].date().isoformat(),
        "end_date": country_df["date"].iloc[-1].date().isoformat(),
        "n_observed_days": int(len(country_df)),
        "initial_cases": initial_cases,
        "observed_total_cases": int(country_df["observed_new_cases"].sum()),
        "mean_rt": float(country_df["Rt"].mean()),
        "median_peak_size": float(np.median(peak_sizes)),
        "p25_peak_size": float(np.percentile(peak_sizes, 25)),
        "p75_peak_size": float(np.percentile(peak_sizes, 75)),
        "most_common_peak_date": peak_dates.mode().iloc[0].date().isoformat(),
        "median_final_cumulative": float(np.median(final_cumulative)),
        "p25_final_cumulative": float(np.percentile(final_cumulative, 25)),
        "p75_final_cumulative": float(np.percentile(final_cumulative, 75)),
    }
    return summary, metrics


def run_all_simulations(
    data_dir: Path = DATA_DIR,
    config: Config | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Prepara los datos y corre simulaciones para todos los países."""
    config = config or Config()
    prepared = load_all_timeseries(data_dir, config)
    summaries: list[pd.DataFrame] = []
    metrics: list[dict[str, object]] = []

    # Cada país se simula por separado porque tiene su propia serie de Rt y su
    # propio punto inicial de casos.
    for seed_offset, (_, country_df) in enumerate(prepared.groupby("CountryCode")):
        summary, country_metrics = run_country_simulations(
            country_df,
            config,
            seed_offset=seed_offset * config.n_simulations,
        )
        summaries.append(summary)
        metrics.append(country_metrics)

    return prepared, pd.concat(summaries, ignore_index=True), pd.DataFrame(metrics)
