# Simulación Monte Carlo de casos nuevos de COVID-19

Este repositorio contiene un proyecto de simulación Monte Carlo para estimar
casos nuevos diarios de COVID-19 por zona geográfica. El modelo toma como punto
de partida el procedimiento de Xie (2020), usa series nacionales del Oxford
COVID-19 Government Response Tracker y genera trayectorias simuladas a partir de
una tasa efectiva \(R_t\) estimada desde casos observados.

El desarrollo completo, la justificación metodológica, los resultados y las
referencias bibliográficas están documentados en `report/report.tex`. La
presentación resumida está en `slides/slides.tex`.

## Estructura

- `src/datasets.py`: descarga y prepara los datasets locales.
- `src/simulation.py`: define la configuración y ejecuta las simulaciones Monte
  Carlo.
- `src/main.py`: genera las figuras usadas por el reporte.
- `report/`: contiene el reporte en LaTeX y la bibliografía.
- `slides/`: contiene la presentación en Beamer.
- `data/`: contiene los CSV usados por el procesamiento local.

## Requisitos

Las dependencias de Python están en `requirements.txt`. Para compilar los
documentos se requiere Tectonic.

```bash
make requirements
```

## Uso

Descargar o actualizar los datos:

```bash
make data
```

Generar las figuras, compilar el reporte y compilar la presentación:

```bash
make
```

Para una verificación rápida con pocas simulaciones:

```bash
python src/main.py --simulations 2 --extra-days 3
```

## Salidas

El flujo de compilación produce:

- `report/report.pdf`
- `slides/slides.pdf`
- figuras en `report/generated/figures/`

En GitHub Pages, el workflow publica los PDFs como:

- `https://tavocg.github.io/monte-carlo-covid/report.pdf`
- `https://tavocg.github.io/monte-carlo-covid/slides.pdf`
