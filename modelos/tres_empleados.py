"""
================================================================================
modelos/tres_empleados.py — Simulador con 3 empleados
================================================================================
Extiende la lógica de dos empleados agregando un tercero que solo está
disponible durante las horas pico (franjas con INDICES_PICO en parametros.py).

Eventos adicionales respecto al modelo de 2 empleados:
    - Fin servicio 3   : el empleado 3 termina un pedido (solo en pico)
    - Entrada emp. 3   : el empleado 3 se incorpora al inicio de cada hora pico
    - Salida emp. 3    : el empleado 3 se retira al fin de cada hora pico
        → su salida se maneja dentro del evento_cambio_segmento, que ya
          detecta cuándo se abandona una franja pico.

Comportamiento del empleado 3 al retirarse:
    - Si está atendiendo a alguien: termina ese pedido normalmente (t_D3
      ya está programado, se respeta). Al terminar, simplemente no acepta
      nuevos clientes porque ya no está disponible.
    - Si está libre al momento del cambio: t_D3 = ∞ y emp3_disponible = False.
    - Los clientes en cola quedan para los empleados 1 y 2.
================================================================================
"""

from core.generacion import gen_exponencial, gen_tipo_cliente, gen_tiempo_prep
from core.parametros import (
    T_FIN, FRANJAS, INDICES_PICO, P_SANDWICH,
    PREP_SANDWICH, PREP_SUSHI, UMBRAL_QUEJA,
    LAMBDA_NORMAL, LAMBDA_PICO,
)


# ── Inicialización ────────────────────────────────────────────────────────────

def inicializar(lambda_normal: float, lambda_pico: float) -> dict:
    """
    Crea el estado inicial del sistema en t = 0 (las 10:00 h).
    El empleado 3 empieza inactivo porque la primera franja es horario normal.

    Parámetros:
        lambda_normal : tasa de arribo en franjas normales
        lambda_pico   : tasa de arribo en hora pico

    Retorna:
        dict con el estado completo del sistema listo para simular.
    """
    franjas = _construir_franjas(lambda_normal, lambda_pico)

    estado = {
        # ── Parámetros activos ────────────────────────────────────────────
        "lambda_normal": lambda_normal,
        "lambda_pico":   lambda_pico,
        "p_sandwich":    P_SANDWICH,

        # ── Reloj ─────────────────────────────────────────────────────────
        "t": 0.0,

        # ── Tiempos de próximos eventos ───────────────────────────────────
        "t_A":      gen_exponencial(franjas[0][3]),
        "t_D1":     float("inf"),
        "t_D2":     float("inf"),
        "t_D3":     float("inf"),   # siempre ∞ cuando emp3 no está disponible
        "t_cambio": franjas[1][1],  # t = 90 (inicio primera hora pico)

        # ── Estado de los empleados ───────────────────────────────────────
        "emp1_libre":      True,
        "emp2_libre":      True,
        "emp3_libre":      True,    # libre pero no disponible aún
        "emp3_disponible": False,   # False = no ha entrado al turno

        "cliente_emp1": None,
        "cliente_emp2": None,
        "cliente_emp3": None,

        # ── Cola de espera (FIFO) ─────────────────────────────────────────
        "cola": [],

        # ── Franja horaria activa ─────────────────────────────────────────
        "segmento_idx":  0,
        "lambda_actual": franjas[0][3],
        "franjas":       franjas,

        # ── Contadores ────────────────────────────────────────────────────
        "N_A":    0,
        "N_D":    0,
        "quejas": 0,
        "quejas_pico":   0,
        "quejas_normal": 0,
        "clientes_pico":   0,
        "clientes_normal": 0,

        # ── Control de cierre ──────────────────────────────────────────────
        "t_fin_alcanzado": False,  # True once we cross T_FIN

        # ── Registros por cliente ─────────────────────────────────────────
        "t_llegada":    {},
        "t_inicio_srv": {},
        "franja_llegada": {},  # franja_llegada[id] = segmento_idx at arrival time
    }
    return estado


# ── Eventos ───────────────────────────────────────────────────────────────────

def _hay_empleado_libre(estado: dict) -> bool:
    """Retorna True si al menos un empleado disponible está libre."""
    if estado["emp1_libre"] or estado["emp2_libre"]:
        return True
    if estado["emp3_disponible"] and estado["emp3_libre"]:
        return True
    return False


def _asignar_empleado(estado: dict, id_cliente: int, tipo: str) -> None:
    """
    Auxiliar: asigna el cliente al primer empleado libre disponible.
    Prioridad: emp1 → emp2 → emp3 (solo si emp3 está disponible).
    Precondición: _hay_empleado_libre() es True.
    """
    t    = estado["t"]
    prep = gen_tiempo_prep(tipo, PREP_SANDWICH, PREP_SUSHI)
    estado["t_inicio_srv"][id_cliente] = t

    if estado["emp1_libre"]:
        estado["emp1_libre"]   = False
        estado["cliente_emp1"] = id_cliente
        estado["t_D1"]         = t + prep
    elif estado["emp2_libre"]:
        estado["emp2_libre"]   = False
        estado["cliente_emp2"] = id_cliente
        estado["t_D2"]         = t + prep
    else:
        # Solo se llega aquí si emp3 está disponible y libre
        estado["emp3_libre"]   = False
        estado["cliente_emp3"] = id_cliente
        estado["t_D3"]         = t + prep


def evento_arribo(estado: dict) -> None:
    """
    Procesa la llegada de un nuevo cliente.
    Idéntico al de 2 empleados, pero el chequeo de disponibilidad
    ahora incluye al empleado 3.
    """
    # Skip arrivals if T_FIN has been crossed (Rule 1)
    if estado["t_fin_alcanzado"]:
        estado["t_A"] = float("inf")
        return

    t = estado["t_A"]
    estado["t"] = t

    estado["N_A"] += 1
    id_cliente = estado["N_A"]
    estado["t_llegada"][id_cliente] = t
    estado["franja_llegada"][id_cliente] = estado["segmento_idx"]

    # Contabilizar el cliente según la franja en la que llegó.
    if estado["segmento_idx"] in INDICES_PICO:
        estado["clientes_pico"] += 1
    else:
        estado["clientes_normal"] += 1

    tipo = gen_tipo_cliente(P_SANDWICH)

    if _hay_empleado_libre(estado):
        _asignar_empleado(estado, id_cliente, tipo)
    else:
        estado["cola"].append({"id": id_cliente, "tipo": tipo})

    estado["t_A"] = t + gen_exponencial(estado["lambda_actual"])


def _liberar_empleado(estado: dict, empleado: int) -> None:
    """
    Auxiliar: libera al empleado indicado.
    Si hay cola y el empleado sigue disponible, atiende al siguiente.
    Si el empleado 3 ya no está disponible, no acepta nuevos clientes.

    Parámetros:
        empleado : 1, 2 o 3
    """
    t = estado["t"]

    id_cliente = estado[f"cliente_emp{empleado}"]

    # Calcular espera y registrar queja
    espera = estado["t_inicio_srv"][id_cliente] - estado["t_llegada"][id_cliente]
    franja = estado["franja_llegada"][id_cliente]
    if franja in INDICES_PICO:
        if espera > UMBRAL_QUEJA:
            estado["quejas_pico"] += 1
    else:
        if espera > UMBRAL_QUEJA:
            estado["quejas_normal"] += 1

    estado["quejas"] = estado["quejas_pico"] + estado["quejas_normal"]

    estado["N_D"] += 1

    # If T_FIN has been crossed, drop remaining queue (Rule 3)
    if estado["t_fin_alcanzado"]:
        # La cocina cerró: la cola se descarta sin servir más clientes.
        estado["cola"].clear()
        estado[f"emp{empleado}_libre"] = True
        estado[f"cliente_emp{empleado}"] = None
        estado[f"t_D{empleado}"] = float("inf")
        return

    # El empleado 3 no acepta nuevos clientes si ya salió de turno
    emp3_puede_atender = (empleado != 3 or estado["emp3_disponible"])

    if estado["cola"] and emp3_puede_atender:
        siguiente = estado["cola"].pop(0)
        prep = gen_tiempo_prep(siguiente["tipo"], PREP_SANDWICH, PREP_SUSHI)
        estado["t_inicio_srv"][siguiente["id"]] = t
        estado[f"cliente_emp{empleado}"]        = siguiente["id"]
        estado[f"t_D{empleado}"]                = t + prep
    else:
        estado[f"emp{empleado}_libre"]   = True
        estado[f"cliente_emp{empleado}"] = None
        estado[f"t_D{empleado}"]         = float("inf")


def evento_fin_servicio(estado: dict, empleado: int) -> None:
    """
    Procesa el fin de servicio del empleado indicado (1, 2 o 3).
    """
    estado["t"] = estado[f"t_D{empleado}"]
    _liberar_empleado(estado, empleado)


def evento_cambio_segmento(estado: dict) -> None:
    """
    Procesa la transición entre franjas horarias.
    Además de actualizar λ, maneja la entrada y salida del empleado 3:
        - Si el nuevo segmento es pico  → emp3 entra (disponible).
        - Si el nuevo segmento es normal → emp3 sale (no disponible).
          Si estaba libre, se inactiva. Si estaba atendiendo, termina
          ese pedido y luego se inactiva (ver _liberar_empleado).
    """
    estado["t"] = estado["t_cambio"]
    estado["segmento_idx"] += 1
    idx = estado["segmento_idx"]
    franjas = estado["franjas"]

    if idx < len(franjas):
        _, _, fin_seg, lam = franjas[idx]
        estado["lambda_actual"] = lam
        estado["t_cambio"]      = fin_seg

        if idx in INDICES_PICO:
            # ── El empleado 3 entra al turno ─────────────────────────────
            estado["emp3_disponible"] = True
            # Si hay clientes esperando, los atiende de inmediato
            if estado["cola"] and estado["emp3_libre"]:
                siguiente = estado["cola"].pop(0)
                prep = gen_tiempo_prep(
                    siguiente["tipo"], PREP_SANDWICH, PREP_SUSHI
                )
                t = estado["t"]
                estado["t_inicio_srv"][siguiente["id"]] = t
                estado["emp3_libre"]   = False
                estado["cliente_emp3"] = siguiente["id"]
                estado["t_D3"]         = t + prep
        else:
            # ── El empleado 3 sale del turno ──────────────────────────────
            estado["emp3_disponible"] = False
            # Si estaba libre, simplemente se inactiva
            if estado["emp3_libre"]:
                estado["t_D3"] = float("inf")
            # Si estaba ocupado: t_D3 ya está programado, lo respeta.
            # _liberar_empleado detectará que emp3_disponible=False
            # y no le asignará más clientes al terminar ese pedido.
    else:
        estado["t_cambio"]       = float("inf")
        estado["emp3_disponible"] = False


# ── Loop principal ────────────────────────────────────────────────────────────

def simular(
    lambda_normal: float = LAMBDA_NORMAL,
    lambda_pico:   float = LAMBDA_PICO,
) -> dict:
    """
    Ejecuta la simulación completa con 3 empleados (el 3ro solo en hora pico).

    Parámetros:
        lambda_normal : tasa de arribo en franjas normales
        lambda_pico   : tasa de arribo en hora pico

    Retorna:
        Estado final con todas las estadísticas acumuladas.
    """
    estado = inicializar(lambda_normal, lambda_pico)

    while True:

        candidatos = {
            "arribo":    estado["t_A"],
            "fin_srv_1": estado["t_D1"],
            "fin_srv_2": estado["t_D2"],
            "fin_srv_3": estado["t_D3"],
            "cambio":    estado["t_cambio"],
        }
        tipo_ev = min(candidatos, key=candidatos.get)
        t_ev    = candidatos[tipo_ev]

        # Set flag when crossing T_FIN (Rule 1: stop accepting arrivals)
        if t_ev >= T_FIN:
            estado["t_fin_alcanzado"] = True

        # Termination: all event times are at infinity (Rules 2-4)
        if all(t == float("inf") for t in candidatos.values()):
            break

        if tipo_ev == "arribo":
            evento_arribo(estado)
        elif tipo_ev == "fin_srv_1":
            evento_fin_servicio(estado, empleado=1)
        elif tipo_ev == "fin_srv_2":
            evento_fin_servicio(estado, empleado=2)
        elif tipo_ev == "fin_srv_3":
            evento_fin_servicio(estado, empleado=3)
        elif tipo_ev == "cambio":
            evento_cambio_segmento(estado)

    return estado


# ── Auxiliar interno ──────────────────────────────────────────────────────────

def _construir_franjas(lambda_normal: float, lambda_pico: float) -> list:
    """Reconstruye la tabla de franjas con los lambdas recibidos."""
    return [
        (nombre, inicio, fin, lambda_pico if "pico" in nombre else lambda_normal)
        for nombre, inicio, fin, _ in FRANJAS
    ]
