import argparse
from pathlib import Path

import matplotlib.pyplot as plt

import datasets
import simulation


def write_figures(summary, observed, output_dir: Path) -> None:
    """Genera figuras de casos diarios y acumulados por país."""
    # Todas las figuras quedan bajo report/generated/figures para que el
    # archivo LaTeX pueda incluirlas con rutas estables.
    figures_dir = output_dir / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)

    for country_code, country_summary in summary.groupby("country_code"):
        # summary contiene los resultados simulados; observed conserva los
        # datos reales preparados desde el dataset para compararlos en la misma
        # escala temporal.
        country_observed = observed[observed["CountryCode"].eq(country_code)]

        # Graficamos el promedio Monte Carlo y el rango intercuartil contra los
        # casos diarios observados. El promedio representa el valor esperado
        # estimado, no una predicción exacta día por día.
        plt.figure(figsize=(10, 5))
        plt.plot(
            country_summary["date"],
            country_summary["mean"],
            label="Valor esperado simulado",
        )
        plt.fill_between(
            country_summary["date"],
            country_summary["p25"],
            country_summary["p75"],
            alpha=0.3,
            label="Rango intercuartil 25%-75%",
        )
        plt.scatter(
            country_observed["date"],
            country_observed["observed_new_cases"],
            s=8,
            label="Casos reales observados",
        )
        plt.xlabel("Fecha")
        plt.ylabel("Nuevos casos diarios")
        plt.title(f"Casos reales vs simulaciones Monte Carlo ({country_code})")
        plt.legend()
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig(figures_dir / f"{country_code}_daily_cases.png", dpi=160)
        plt.close()

        # Graficamos la evolución acumulada de las simulaciones para observar
        # cómo se acumula la diferencia entre trayectorias a lo largo del tiempo.
        plt.figure(figsize=(10, 5))
        plt.plot(
            country_summary["date"],
            country_summary["cumulative_mean"],
            label="Valor esperado acumulado",
        )
        plt.fill_between(
            country_summary["date"],
            country_summary["cumulative_p25"],
            country_summary["cumulative_p75"],
            alpha=0.3,
            label="Rango intercuartil 25%-75%",
        )
        plt.xlabel("Fecha")
        plt.ylabel("Casos acumulados simulados")
        plt.title(f"Casos acumulados simulados ({country_code})")
        plt.legend()
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig(figures_dir / f"{country_code}_cumulative_cases.png", dpi=160)
        plt.close()


def main() -> None:
    parser = argparse.ArgumentParser()

    # Estos argumentos permiten cambiar la corrida desde consola sin tocar el
    # código. El reporte usa 1000 simulaciones y 30 días extra por defecto.
    parser.add_argument("--simulations", type=int, default=1000)
    parser.add_argument("--extra-days", type=int, default=30)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=datasets.ROOT_DIR / "report" / "generated",
    )
    args = parser.parse_args()

    config = simulation.Config(
        n_simulations=args.simulations,
        n_extra_days=args.extra_days,
    )

    # run_all_simulations prepara los datos, corre las simulaciones de todos los
    # países y devuelve tanto las observaciones como los resúmenes simulados.
    observed, summary, _ = simulation.run_all_simulations(config=config)

    write_figures(summary, observed, args.output_dir)
    print(f"Figuras generadas en {args.output_dir / 'figures'}")


if __name__ == "__main__":
    main()
