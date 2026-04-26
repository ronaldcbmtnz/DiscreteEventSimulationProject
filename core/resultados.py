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
    quejas_pico = estado["quejas_pico"]
    quejas_normal = estado["quejas_normal"]
    clientes_pico = estado["clientes_pico"]
    clientes_normal = estado["clientes_normal"]

    # Clientes que quedaron en cola al cierre
    en_cola = len(estado["cola"])

    # Clientes siendo atendidos al cierre (contando todos los empleados activos)
    en_servicio = sum(
        1 for k in ["emp1_libre", "emp2_libre", "emp3_libre"]
        if k in estado and not estado[k]
    )

    pct_quejas = (quejas / N_A * 100) if N_A > 0 else 0.0
    pct_quejas_pico = (quejas_pico / clientes_pico * 100) if clientes_pico > 0 else 0.0
    pct_quejas_normal = (quejas_normal / clientes_normal * 100) if clientes_normal > 0 else 0.0
    sep = "─" * 62

    print()
    print("=" * 62)
    print(f"  RESULTADOS — LA COCINA DE KOJO  ({n_empleados} empleados)")
    print("=" * 62)
    # Breve contexto para que el lector entienda qué resume esta corrida.
    print("  Corrida individual de simulación con los parámetros mostrados abajo.")
    print()
    print("  Parámetros:")
    print(f"    λ normal        : {estado['lambda_normal']:.2f} clientes/min")
    print(f"    λ pico          : {estado['lambda_pico']:.2f} clientes/min")
    print(f"    P(sándwich)     : {estado['p_sandwich'] * 100:.0f}%")
    print(f"    Umbral queja    : {UMBRAL_QUEJA} minutos")
    print(sep)
    print("  Flujo de clientes:")
    print(f"    Total llegados  : {N_A}")
    print(f"    Total atendidos : {N_D}")
    print(f"    En cola/cierre  : {en_cola}")
    print(f"    En srv./cierre  : {en_servicio}")
    print(sep)
    print("  Medida de desempeño:")
    # Métricas principales con su significado explícito.
    print(f"    Clientes que esperaron más de {UMBRAL_QUEJA} min en cola : {quejas} clientes")
    print("      (estos generan una queja al administrador)")
    print(f"    Porcentaje de quejas sobre total atendidos                : {pct_quejas:.2f}%")
    print(sep)
    # Desglose por franja para ver si las quejas se concentran en hora pico.
    print("  Desglose por franja horaria — permite ver si las quejas se concentran")
    print("  en hora pico o se distribuyen a lo largo del día.")
    print(f"    Hora pico   : {quejas_pico} quejas / {clientes_pico} clientes")
    print(f"                  = {pct_quejas_pico:.2f}% de queja en pico")
    print(f"    Hora normal : {quejas_normal} quejas / {clientes_normal} clientes")
    print(f"                  = {pct_quejas_normal:.2f}% de queja en horario normal")
    print("=" * 62)
    print()


def analisis_sensibilidad(
    fn_simular,
    n_empleados: int,
    lambdas_pico: list,
    n_rep=30,
) -> list:
    """
    Corre el simulador múltiples veces variando λ_pico y retorna los resultados.

    Parámetros:
        fn_simular   : función simular() de la variante a analizar
        n_empleados  : 2 o 3, solo para el encabezado
        lambdas_pico : lista de valores de λ_pico a probar
        n_rep        : número de repeticiones independientes por cada λ_pico

    Retorna:
        Lista de dicts con {lambda_pico, N_A, quejas, pct_quejas, pct_quejas_pico, pct_quejas_normal} por corrida.
    """
    import random
    from statistics import mean

    resultados = []

    print()
    print("=" * 64)
    print(f"  SENSIBILIDAD λ_pico — {n_empleados} empleados  ({n_rep} repeticiones)")
    print("=" * 64)
    print("  λ_pico : tasa de arribo en hora pico (clientes/min)")
    print("  % Pico : quejas en hora pico / clientes en hora pico")
    print("  % Normal: quejas fuera de pico / clientes fuera de pico")
    print(f"  Valores promediados sobre {n_rep} corridas independientes.")
    print("=" * 64)
    print(f"  {'λ_pico':>7} | {'Cli. (avg)':>10} | {'Quejas (avg)':>12} | {'% Global':>8} | {'% Pico':>7} | {'% Normal':>9}")
    print("  " + "─" * 69)

    for lam in lambdas_pico:
        collected = []

        for rep in range(n_rep):
            # Si no hay semilla base, usar aleatoriedad del sistema en cada repetición.
            if SEMILLA is None:
                random.seed(None)
            else:
                random.seed(SEMILLA + rep)
            estado = fn_simular(
                lambda_normal=LAMBDA_NORMAL,
                lambda_pico=lam,
            )
            collected.append(estado)

        avg_N_A = mean(estado["N_A"] for estado in collected)
        avg_quejas = mean(estado["quejas"] for estado in collected)
        avg_pct_quejas = mean(
            (estado["quejas"] / estado["N_A"] * 100) if estado["N_A"] > 0 else 0.0
            for estado in collected
        )
        avg_pct_pico = mean(
            (
                estado["quejas_pico"] / estado["clientes_pico"] * 100
                if estado["clientes_pico"] > 0
                else 0.0
            )
            for estado in collected
        )
        avg_pct_normal = mean(
            (
                estado["quejas_normal"] / estado["clientes_normal"] * 100
                if estado["clientes_normal"] > 0
                else 0.0
            )
            for estado in collected
        )

        print(
            f"  {lam:>7.2f} | {avg_N_A:>10.1f} | {avg_quejas:>12.1f} | {avg_pct_quejas:>8.2f}% | {avg_pct_pico:>7.2f}% | {avg_pct_normal:>9.2f}%"
        )
        resultados.append({
            "lambda_pico": lam,
            "N_A":         avg_N_A,
            "quejas":      avg_quejas,
            "pct_quejas":  avg_pct_quejas,
            "pct_quejas_pico": avg_pct_pico,
            "pct_quejas_normal": avg_pct_normal,
        })

    print("=" * 64)
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
    print("=" * 64)
    print("  COMPARACIÓN EN HORA PICO: 2 emp vs 3 emp (3ro solo en pico)")
    print("  Métrica de comparación: % de quejas en hora pico")
    print("=" * 64)
    print(f"  {'λ_pico':>7} | {'% Pico (2 emp)':>14} | {'% Pico (3 emp)':>14} | {'Reducción (pp)':>14}")
    print("  " + "─" * 59)

    for r2, r3 in zip(resultados_2, resultados_3):
        reduccion = r2["pct_quejas_pico"] - r3["pct_quejas_pico"]
        print(
            f"  {r2['lambda_pico']:>7.2f} | {r2['pct_quejas_pico']:>13.2f}% | {r3['pct_quejas_pico']:>13.2f}% | {reduccion:>+13.2f}"
        )

    print("=" * 64)
    print()
    print("=" * 64)
    print("  COMPARACIÓN GLOBAL: 2 emp vs 3 emp (3ro solo en hora pico)")
    print("  Responde: ¿cuántos clientes esperaron más de 5 min en el día?")
    print("=" * 64)
    print(f"  {'λ_pico':>7} | {'% Global (2 emp)':>17} | {'% Global (3 emp)':>17} | {'Reducción (pp)':>14}")
    print("  " + "─" * 64)

    for r2, r3 in zip(resultados_2, resultados_3):
        reduccion = r2["pct_quejas"] - r3["pct_quejas"]
        print(
            f"  {r2['lambda_pico']:>7.2f} | {r2['pct_quejas']:>16.2f}% | {r3['pct_quejas']:>16.2f}% | {reduccion:>+13.2f}"
        )

    print("=" * 64)
    print()
