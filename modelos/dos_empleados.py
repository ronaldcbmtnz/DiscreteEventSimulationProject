"""
================================================================================
modelos/dos_empleados.py — Simulador con 2 empleados
================================================================================
Contiene la inicialización, los manejadores de evento y el loop principal
para el sistema con dos empleados permanentes.

Eventos del modelo:
    - Arribo         : llega un nuevo cliente
    - Fin servicio 1 : el empleado 1 termina de preparar un pedido
    - Fin servicio 2 : el empleado 2 termina de preparar un pedido
    - Cambio de λ    : transición entre franja horaria normal y pico

Importa de core:
    - generacion  : todas las funciones de generación aleatoria
    - parametros  : constantes del modelo (FRANJAS, PREP_*, P_SANDWICH, etc.)
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

    Parámetros:
        lambda_normal : tasa de arribo en franjas normales
        lambda_pico   : tasa de arribo en hora pico

    Retorna:
        dict con el estado completo del sistema listo para simular.
    """
    # Construir tabla de franjas con los lambdas recibidos
    franjas = _construir_franjas(lambda_normal, lambda_pico)

    estado = {
        # ── Parámetros activos (guardados para el reporte) ────────────────
        "lambda_normal": lambda_normal,
        "lambda_pico":   lambda_pico,
        "p_sandwich":    P_SANDWICH,

        # ── Reloj de simulación ───────────────────────────────────────────
        "t": 0.0,

        # ── Tiempos de próximos eventos ───────────────────────────────────
        "t_A":      gen_exponencial(franjas[0][3]),  # primer arribo
        "t_D1":     float("inf"),                    # fin servicio emp. 1
        "t_D2":     float("inf"),                    # fin servicio emp. 2
        "t_cambio": franjas[1][1],                   # primer cambio (t=90)

        # ── Estado de los empleados ───────────────────────────────────────
        "emp1_libre":   True,
        "emp2_libre":   True,
        "cliente_emp1": None,   # id del cliente que atiende el emp. 1
        "cliente_emp2": None,   # id del cliente que atiende el emp. 2

        # ── Cola de espera (disciplina FIFO) ──────────────────────────────
        # Cada entrada: {"id": int, "tipo": str, "t_llegada": float}
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
        "t_llegada":    {},   # t_llegada[id]    = minuto de llegada
        "t_inicio_srv": {},   # t_inicio_srv[id] = minuto de inicio de servicio
        "franja_llegada": {},  # franja_llegada[id] = segmento_idx at arrival time
    }
    return estado


# ── Eventos ───────────────────────────────────────────────────────────────────

def _asignar_empleado(estado: dict, id_cliente: int, tipo: str) -> None:
    """
    Auxiliar: asigna el cliente al primer empleado libre (emp1 tiene prioridad).
    Registra t_inicio_srv y programa el fin de servicio correspondiente.
    Precondición: al menos uno de los dos empleados está libre.
    """
    t    = estado["t"]
    prep = gen_tiempo_prep(tipo, PREP_SANDWICH, PREP_SUSHI)
    estado["t_inicio_srv"][id_cliente] = t

    if estado["emp1_libre"]:
        estado["emp1_libre"]    = False
        estado["cliente_emp1"]  = id_cliente
        estado["t_D1"]          = t + prep
    else:
        estado["emp2_libre"]    = False
        estado["cliente_emp2"]  = id_cliente
        estado["t_D2"]          = t + prep


def evento_arribo(estado: dict) -> None:
    """
    Procesa la llegada de un nuevo cliente.

    Pasos:
        1. Avanzar el reloj a t_A.
        2. Registrar la llegada y determinar el tipo de pedido.
        3. Si hay empleado libre → atender de inmediato.
           Si no                 → encolar (FIFO).
        4. Generar el tiempo del próximo arribo.
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

    if estado["emp1_libre"] or estado["emp2_libre"]:
        _asignar_empleado(estado, id_cliente, tipo)
    else:
        estado["cola"].append({"id": id_cliente, "tipo": tipo})

    estado["t_A"] = t + gen_exponencial(estado["lambda_actual"])


def _liberar_empleado(estado: dict, empleado: int) -> None:
    """
    Auxiliar: libera al empleado indicado al terminar un servicio.
    Si hay clientes en cola, asigna el primero al empleado liberado.
    Registra la espera y actualiza el contador de quejas.

    Parámetros:
        empleado : 1 o 2
    """
    t = estado["t"]

    # Identificar al cliente que acaba de ser atendido
    id_cliente = estado[f"cliente_emp{empleado}"]

    # Calcular espera en cola y registrar queja si corresponde
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

    if estado["cola"]:
        # Atender al siguiente en cola
        siguiente = estado["cola"].pop(0)
        prep = gen_tiempo_prep(siguiente["tipo"], PREP_SANDWICH, PREP_SUSHI)
        estado["t_inicio_srv"][siguiente["id"]] = t
        estado[f"cliente_emp{empleado}"]        = siguiente["id"]
        estado[f"t_D{empleado}"]                = t + prep
        # El empleado sigue ocupado, no se marca libre
    else:
        # Cola vacía: el empleado descansa
        estado[f"emp{empleado}_libre"]   = True
        estado[f"cliente_emp{empleado}"] = None
        estado[f"t_D{empleado}"]         = float("inf")


def evento_fin_servicio(estado: dict, empleado: int) -> None:
    """
    Procesa el fin de servicio del empleado indicado.

    Pasos:
        1. Avanzar el reloj a t_Di.
        2. Liberar al empleado y atender al siguiente (si hay cola).

    Parámetros:
        empleado : 1 o 2
    """
    estado["t"] = estado[f"t_D{empleado}"]
    _liberar_empleado(estado, empleado)


def evento_cambio_segmento(estado: dict) -> None:
    """
    Procesa la transición entre franjas horarias.

    Pasos:
        1. Avanzar el reloj al momento del cambio.
        2. Activar el siguiente segmento (nuevo λ y próximo t_cambio).
    """
    estado["t"] = estado["t_cambio"]
    estado["segmento_idx"] += 1
    idx = estado["segmento_idx"]
    franjas = estado["franjas"]

    if idx < len(franjas):
        _, _, fin_seg, lam = franjas[idx]
        estado["lambda_actual"] = lam
        estado["t_cambio"]      = fin_seg
    else:
        estado["t_cambio"] = float("inf")


# ── Loop principal ────────────────────────────────────────────────────────────

def simular(
    lambda_normal: float = LAMBDA_NORMAL,
    lambda_pico:   float = LAMBDA_PICO,
) -> dict:
    """
    Ejecuta la simulación completa con 2 empleados.

    Parámetros:
        lambda_normal : tasa de arribo en franjas normales
        lambda_pico   : tasa de arribo en hora pico

    Retorna:
        Estado final con todas las estadísticas acumuladas.
    """
    estado = inicializar(lambda_normal, lambda_pico)

    while True:

        # Seleccionar el evento de menor tiempo programado
        candidatos = {
            "arribo":    estado["t_A"],
            "fin_srv_1": estado["t_D1"],
            "fin_srv_2": estado["t_D2"],
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

        # Despachar al manejador correspondiente
        if tipo_ev == "arribo":
            evento_arribo(estado)
        elif tipo_ev == "fin_srv_1":
            evento_fin_servicio(estado, empleado=1)
        elif tipo_ev == "fin_srv_2":
            evento_fin_servicio(estado, empleado=2)
        elif tipo_ev == "cambio":
            evento_cambio_segmento(estado)

    return estado


# ── Auxiliar interno ──────────────────────────────────────────────────────────

def _construir_franjas(lambda_normal: float, lambda_pico: float) -> list:
    """
    Reconstruye la tabla de franjas con los lambdas recibidos como parámetro,
    en lugar de leer directamente las constantes globales.
    Esto permite correr análisis de sensibilidad sin modificar parametros.py.
    """
    return [
        (nombre, inicio, fin, lambda_pico if "pico" in nombre else lambda_normal)
        for nombre, inicio, fin, _ in FRANJAS
    ]
