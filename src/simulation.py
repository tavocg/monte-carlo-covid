import numpy as np


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
