"""
================================================================================
core/resultados.py — Reporte de resultados y análisis de sensibilidad
================================================================================
Recibe el estado final de cualquier variante del simulador (2 o 3 empleados)
y produce los reportes. Es agnóstico al número de empleados — solo lee las
claves del estado que son comunes a ambas variantes.
================================================================================
"""

from core.parametros import UMBRAL_QUEJA, LAMBDA_NORMAL, SEMILLA


def imprimir_resultados(estado: dict, n_empleados: int) -> None:
    """
    Imprime el reporte de desempeño al finalizar una corrida.

    Parámetros:
        estado       : estado final retornado por simular()
        n_empleados  : 2 o 3, solo para el encabezado
    """
    N_A    = estado["N_A"]
    N_D    = estado["N_D"]
    quejas = estado["quejas"]

    # Clientes que quedaron en cola al cierre
    en_cola = len(estado["cola"])

    # Clientes siendo atendidos al cierre (contando todos los empleados activos)
    en_servicio = sum(
        1 for k in ["emp1_libre", "emp2_libre", "emp3_libre"]
        if k in estado and not estado[k]
    )

    pct_quejas = (quejas / N_A * 100) if N_A > 0 else 0.0
    sep = "─" * 62

    print()
    print("=" * 62)
    print(f"  RESULTADOS — LA COCINA DE KOJO  ({n_empleados} empleados)")
    print("=" * 62)
    print(f"  Parámetros:")
    print(f"    λ normal        : {estado['lambda_normal']:.2f} clientes/min")
    print(f"    λ pico          : {estado['lambda_pico']:.2f} clientes/min")
    print(f"    P(sándwich)     : {estado['p_sandwich'] * 100:.0f}%")
    print(f"    Umbral queja    : {UMBRAL_QUEJA} minutos")
    print(sep)
    print(f"  Flujo de clientes:")
    print(f"    Total arriados  : {N_A}")
    print(f"    Total atendidos : {N_D}")
    print(f"    En cola/cierre  : {en_cola}")
    print(f"    En srv./cierre  : {en_servicio}")
    print(sep)
    print(f"  Medida de desempeño:")
    print(f"    Espera > {UMBRAL_QUEJA} min  : {quejas} clientes")
    print(f"    % de quejas     : {pct_quejas:.2f}%")
    print("=" * 62)
    print()


def analisis_sensibilidad(
    fn_simular,
    n_empleados: int,
    lambdas_pico: list,
) -> list:
    """
    Corre el simulador múltiples veces variando λ_pico y retorna los resultados.

    Parámetros:
        fn_simular   : función simular() de la variante a analizar
        n_empleados  : 2 o 3, solo para el encabezado
        lambdas_pico : lista de valores de λ_pico a probar

    Retorna:
        Lista de dicts con {lambda_pico, N_A, quejas, pct_quejas} por corrida.
    """
    import random

    resultados = []

    print()
    print("=" * 62)
    print(f"  SENSIBILIDAD λ_pico — {n_empleados} empleados")
    print("=" * 62)
    print(f"  {'λ_pico':>8}  {'Clientes':>10}  {'Quejas':>8}  {'% Quejas':>10}")
    print("  " + "─" * 44)

    for lam in lambdas_pico:
        random.seed(SEMILLA)
        estado = fn_simular(
            lambda_normal=LAMBDA_NORMAL,
            lambda_pico=lam,
        )
        N_A    = estado["N_A"]
        quejas = estado["quejas"]
        pct    = (quejas / N_A * 100) if N_A > 0 else 0.0

        print(f"  {lam:>8.2f}  {N_A:>10}  {quejas:>8}  {pct:>9.2f}%")
        resultados.append({
            "lambda_pico": lam,
            "N_A":         N_A,
            "quejas":      quejas,
            "pct_quejas":  pct,
        })

    print("=" * 62)
    print()
    return resultados


def comparar_variantes(resultados_2: list, resultados_3: list) -> None:
    """
    Imprime una tabla comparativa entre la variante de 2 y 3 empleados,
    mostrando la reducción en el porcentaje de quejas al agregar el tercero.

    Parámetros:
        resultados_2 : lista retornada por analisis_sensibilidad (2 emp.)
        resultados_3 : lista retornada por analisis_sensibilidad (3 emp.)
    """
    print()
    print("=" * 72)
    print("  COMPARACIÓN: 2 empleados vs 3 empleados (3ro solo en hora pico)")
    print("=" * 72)
    print(f"  {'λ_pico':>8}  {'% (2 emp)':>10}  {'% (3 emp)':>10}  {'Reducción':>12}")
    print("  " + "─" * 52)

    for r2, r3 in zip(resultados_2, resultados_3):
        reduccion = r2["pct_quejas"] - r3["pct_quejas"]
        print(
            f"  {r2['lambda_pico']:>8.2f}"
            f"  {r2['pct_quejas']:>9.2f}%"
            f"  {r3['pct_quejas']:>9.2f}%"
            f"  {reduccion:>+10.2f} pp"
        )

    print("=" * 72)
    print()
