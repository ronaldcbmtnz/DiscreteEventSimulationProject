"""
================================================================================
main.py — Punto de entrada del simulador de Kojo
================================================================================
Corre ambas variantes del simulador (2 y 3 empleados) y produce:
    1. Reporte de la corrida base para cada variante.
    2. Análisis de sensibilidad variando λ_pico para cada variante.
    3. Tabla comparativa entre ambas variantes.

Para modificar los parámetros del modelo, editar core/parametros.py.
Para correr solo una variante, comentar la sección de la otra.
================================================================================
"""

import random
import sys
import os

# Permitir imports desde la raíz del proyecto
sys.path.insert(0, os.path.dirname(__file__))

from core.parametros  import SEMILLA, LAMBDA_NORMAL, LAMBDA_PICO
from core.resultados  import imprimir_resultados, analisis_sensibilidad, comparar_variantes
from modelos          import simulador


# ── Lambdas a explorar en el análisis de sensibilidad ────────────────────────
LAMBDAS_PICO = [0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.45]


def main():

    # ── Corrida base: 2 empleados ─────────────────────────────────────────────
    print("\n" + "━" * 62)
    print("  VARIANTE: 2 EMPLEADOS")
    print("━" * 62)
    random.seed(SEMILLA)
    estado_2 = simulador.simular(
        lambda_normal=LAMBDA_NORMAL,
        lambda_pico=LAMBDA_PICO,
        n_empleados_base=2,
        tercer_empleado_en_pico=False,
    )
    imprimir_resultados(estado_2, n_empleados=2)

    # ── Corrida base: 3 empleados ─────────────────────────────────────────────
    print("━" * 62)
    print("  VARIANTE: 3 EMPLEADOS (3ro solo en hora pico)")
    print("━" * 62)
    random.seed(SEMILLA)
    estado_3 = simulador.simular(
        lambda_normal=LAMBDA_NORMAL,
        lambda_pico=LAMBDA_PICO,
        n_empleados_base=2,
        tercer_empleado_en_pico=True,
    )
    imprimir_resultados(estado_3, n_empleados=3)

    # ── Análisis de sensibilidad ──────────────────────────────────────────────
    res_2 = analisis_sensibilidad(
        fn_simular=lambda lambda_normal, lambda_pico: simulador.simular(
            lambda_normal=lambda_normal,
            lambda_pico=lambda_pico,
            n_empleados_base=2,
            tercer_empleado_en_pico=False,
        ),
        n_empleados=2,
        lambdas_pico=LAMBDAS_PICO,
        n_rep=30,
    )
    res_3 = analisis_sensibilidad(
        fn_simular=lambda lambda_normal, lambda_pico: simulador.simular(
            lambda_normal=lambda_normal,
            lambda_pico=lambda_pico,
            n_empleados_base=2,
            tercer_empleado_en_pico=True,
        ),
        n_empleados=3,
        lambdas_pico=LAMBDAS_PICO,
        n_rep=30,
    )

    # ── Comparación final ─────────────────────────────────────────────────────
    comparar_variantes(res_2, res_3)


if __name__ == "__main__":
    main()
