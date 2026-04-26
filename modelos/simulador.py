"""
================================================================================
modelos/simulador.py — Simulador unificado con estado por contadores
================================================================================
Unifica las variantes de 2 y 3 empleados usando una representación de estado
por capacidad y servidores libres, en lugar de banderas por empleado.

Configuraciones soportadas:
    - 2 empleados fijos:
        n_empleados_base=2, tercer_empleado_en_pico=False
    - 3 empleados (3ro solo en hora pico):
        n_empleados_base=2, tercer_empleado_en_pico=True

Eventos del modelo:
    - Arribo      : llega un nuevo cliente
    - Fin servicio: finaliza el pedido de un servidor ocupado
    - Cambio de λ : transición entre franja horaria normal y pico
================================================================================
"""

from core.generacion import gen_exponencial, gen_tipo_cliente, gen_tiempo_prep
from core.parametros import (
    T_FIN, FRANJAS, INDICES_PICO, P_SANDWICH,
    PREP_SANDWICH, PREP_SUSHI, UMBRAL_QUEJA,
    LAMBDA_NORMAL, LAMBDA_PICO,
)


def _assert_invariantes(estado: dict) -> None:
    """Valida invariantes internas del estado de servidores y cola."""
    assert estado["servidores_libres"] >= 0
    assert estado["servidores_libres"] + len(estado["t_fins"]) <= (
        estado["capacidad_actual"] + estado["servidores_fantasma"]
    )
    assert not (len(estado["cola"]) > 0 and estado["servidores_libres"] > 0)


# ── Inicialización ────────────────────────────────────────────────────────────

def inicializar(
    lambda_normal: float,
    lambda_pico: float,
    n_empleados_base: int,
    tercer_empleado_en_pico: bool,
) -> dict:
    """
    Crea el estado inicial del sistema en t = 0 (las 10:00 h).

    Parámetros:
        lambda_normal            : tasa de arribo en franjas normales
        lambda_pico              : tasa de arribo en hora pico
        n_empleados_base         : cantidad de empleados permanentes
        tercer_empleado_en_pico  : activa 1 empleado extra solo en pico

    Retorna:
        dict con el estado completo del sistema listo para simular.
    """
    franjas = _construir_franjas(lambda_normal, lambda_pico)
    primer_cambio = franjas[1][1] if len(franjas) > 1 else float("inf")

    estado = {
        # ── Parámetros activos (guardados para el reporte) ────────────────
        "lambda_normal": lambda_normal,
        "lambda_pico":   lambda_pico,
        "p_sandwich":    P_SANDWICH,

        # ── Configuración de capacidad ─────────────────────────────────────
        "n_empleados_base": n_empleados_base,
        "tercer_empleado_en_pico": tercer_empleado_en_pico,
        "extra_activo": False,

        # ── Reloj de simulación ───────────────────────────────────────────
        "t": 0.0,

        # ── Tiempos de próximos eventos ───────────────────────────────────
        "t_A":      gen_exponencial(franjas[0][3]),
        "t_cambio": primer_cambio,

        # ── Estado agregado de servidores ──────────────────────────────────
        "capacidad_actual": n_empleados_base,
        "servidores_libres": n_empleados_base,
        "servidores_fantasma": 0,
        "t_fins": [],
        "t_fin_to_cliente": {},   # maps t_fin float -> id_cliente

        # ── Cola de espera (disciplina FIFO) ──────────────────────────────
        "cola": [],

        # ── Franja horaria activa ─────────────────────────────────────────
        "segmento_idx": 0,
        "lambda_actual": franjas[0][3],
        "franjas": franjas,

        # ── Contadores ────────────────────────────────────────────────────
        "N_A": 0,
        "N_D": 0,
        "quejas": 0,
        "quejas_pico": 0,
        "quejas_normal": 0,
        "clientes_pico": 0,
        "clientes_normal": 0,

        # ── Control de cierre ─────────────────────────────────────────────
        "t_fin_alcanzado": False,

        # ── Registros por cliente ─────────────────────────────────────────
        "t_llegada": {},
        "t_inicio_srv": {},
        "franja_llegada": {},
    }

    _assert_invariantes(estado)
    return estado


# ── Auxiliares de asignación ─────────────────────────────────────────────────

def _programar_fin(estado: dict, t_fin: float, id_cliente: int) -> None:
    """Programa un fin de servicio y registra el cliente asociado a ese t_fin."""
    # Evita colisiones de clave en t_fin_to_cliente cuando hay empates exactos.
    while t_fin in estado["t_fin_to_cliente"]:
        t_fin += 1e-9
    estado["t_fins"].append(t_fin)
    estado["t_fin_to_cliente"][t_fin] = id_cliente


def _iniciar_servicio(estado: dict, id_cliente: int, tipo: str) -> None:
    """Asigna un cliente a un servidor libre y programa su fin de servicio."""
    t = estado["t"]
    estado["servidores_libres"] -= 1
    prep = gen_tiempo_prep(tipo, PREP_SANDWICH, PREP_SUSHI)
    t_fin_val = t + prep
    estado["t_inicio_srv"][id_cliente] = t
    _programar_fin(estado, t_fin_val, id_cliente)
    _assert_invariantes(estado)


# ── Eventos ───────────────────────────────────────────────────────────────────

def evento_arribo(estado: dict) -> None:
    """
    Procesa la llegada de un nuevo cliente.

    Pasos:
        1. Avanzar el reloj a t_A.
        2. Registrar la llegada y determinar el tipo de pedido.
        3. Si hay servidor libre → atender de inmediato.
           Si no                → encolar (FIFO).
        4. Generar el tiempo del próximo arribo.
    """
    if estado["t_fin_alcanzado"]:
        estado["t_A"] = float("inf")
        return

    t = estado["t_A"]
    estado["t"] = t

    estado["N_A"] += 1
    id_cliente = estado["N_A"]
    estado["t_llegada"][id_cliente] = t
    estado["franja_llegada"][id_cliente] = estado["segmento_idx"]

    if estado["segmento_idx"] in INDICES_PICO:
        estado["clientes_pico"] += 1
    else:
        estado["clientes_normal"] += 1

    tipo = gen_tipo_cliente(P_SANDWICH)

    if estado["servidores_libres"] > 0:
        _iniciar_servicio(estado, id_cliente, tipo)
    else:
        estado["cola"].append({"id": id_cliente, "tipo": tipo})
        _assert_invariantes(estado)

    estado["t_A"] = t + gen_exponencial(estado["lambda_actual"])


def evento_fin_servicio(estado: dict) -> None:
    """
    Procesa el fin de servicio más próximo entre los servidores ocupados.
    """
    t = min(estado["t_fins"])
    estado["t_fins"].remove(t)
    estado["t"] = t
    estado["N_D"] += 1

    id_cliente = estado["t_fin_to_cliente"].pop(t)
    espera = estado["t_inicio_srv"][id_cliente] - estado["t_llegada"][id_cliente]

    franja = estado["franja_llegada"][id_cliente]
    if espera > UMBRAL_QUEJA:
        if franja in INDICES_PICO:
            estado["quejas_pico"] += 1
        else:
            estado["quejas_normal"] += 1
    estado["quejas"] = estado["quejas_pico"] + estado["quejas_normal"]

    # Si cerró el local, la cola restante no se atiende.
    if estado["t_fin_alcanzado"] and estado["cola"]:
        estado["cola"].clear()

    # Si el total visible ya está en capacidad, este servidor era "fantasma".
    servidores_en_uso = len(estado["t_fins"])
    servidores_totales = estado["servidores_libres"] + servidores_en_uso
    if estado["servidores_fantasma"] > 0 and servidores_totales >= estado["capacidad_actual"]:
        estado["servidores_fantasma"] -= 1
    elif servidores_totales < estado["capacidad_actual"]:
        estado["servidores_libres"] += 1

    if estado["cola"] and estado["servidores_libres"] > 0:
        siguiente = estado["cola"].pop(0)
        _iniciar_servicio(estado, siguiente["id"], siguiente["tipo"])
    else:
        _assert_invariantes(estado)


def evento_cambio_segmento(estado: dict) -> None:
    """
    Procesa la transición entre franjas horarias.

    Además de actualizar λ, puede activar o desactivar un tercer empleado
    durante las horas pico cuando tercer_empleado_en_pico=True.
    """
    estado["t"] = estado["t_cambio"]
    estado["segmento_idx"] += 1
    idx = estado["segmento_idx"]
    franjas = estado["franjas"]

    if idx < len(franjas):
        _, _, fin_seg, lam = franjas[idx]
        estado["lambda_actual"] = lam
        estado["t_cambio"] = fin_seg

        if estado["tercer_empleado_en_pico"]:
            if idx in INDICES_PICO and not estado["extra_activo"]:
                # Entrada del tercer empleado en franja pico.
                estado["extra_activo"] = True
                estado["capacidad_actual"] += 1
                estado["servidores_libres"] += 1

                if estado["cola"] and estado["servidores_libres"] > 0:
                    siguiente = estado["cola"].pop(0)
                    _iniciar_servicio(estado, siguiente["id"], siguiente["tipo"])
                else:
                    _assert_invariantes(estado)

            elif idx not in INDICES_PICO and estado["extra_activo"]:
                # Salida del tercer empleado al volver a franja normal.
                estado["extra_activo"] = False
                estado["capacidad_actual"] -= 1
                if estado["servidores_libres"] > 0:
                    estado["servidores_libres"] -= 1
                else:
                    # El 3ro sigue su pedido en curso como servidor "fantasma".
                    estado["servidores_fantasma"] += 1
                _assert_invariantes(estado)
    else:
        estado["t_cambio"] = float("inf")
        if estado["tercer_empleado_en_pico"] and estado["extra_activo"]:
            estado["extra_activo"] = False
            estado["capacidad_actual"] -= 1
            if estado["servidores_libres"] > 0:
                estado["servidores_libres"] -= 1
            else:
                estado["servidores_fantasma"] += 1
        _assert_invariantes(estado)


# ── Loop principal ────────────────────────────────────────────────────────────

def simular(
    lambda_normal: float = LAMBDA_NORMAL,
    lambda_pico: float = LAMBDA_PICO,
    n_empleados_base: int = 2,
    tercer_empleado_en_pico: bool = False,
) -> dict:
    """
    Ejecuta la simulación completa con representación agregada de servidores.

    Parámetros:
        lambda_normal            : tasa de arribo en franjas normales
        lambda_pico              : tasa de arribo en hora pico
        n_empleados_base         : cantidad de empleados permanentes
        tercer_empleado_en_pico  : activa 1 empleado extra en franjas pico

    Retorna:
        Estado final con todas las estadísticas acumuladas.
    """
    estado = inicializar(
        lambda_normal=lambda_normal,
        lambda_pico=lambda_pico,
        n_empleados_base=n_empleados_base,
        tercer_empleado_en_pico=tercer_empleado_en_pico,
    )

    while True:
        candidatos = {
            "arribo": estado["t_A"],
            "fin_srv": min(estado["t_fins"]) if estado["t_fins"] else float("inf"),
            "cambio": estado["t_cambio"],
        }
        tipo_ev = min(candidatos, key=candidatos.get)
        t_ev = candidatos[tipo_ev]

        if t_ev >= T_FIN:
            estado["t_fin_alcanzado"] = True

        # Fin cuando no hay más arribos, ni servicios en curso, ni cambios.
        if (
            estado["t_A"] == float("inf")
            and not estado["t_fins"]
            and estado["t_cambio"] == float("inf")
        ):
            break

        if tipo_ev == "arribo":
            evento_arribo(estado)
        elif tipo_ev == "fin_srv":
            evento_fin_servicio(estado)
        elif tipo_ev == "cambio":
            evento_cambio_segmento(estado)

    return estado


# ── Auxiliar interno ──────────────────────────────────────────────────────────

def _construir_franjas(lambda_normal: float, lambda_pico: float) -> list:
    """
    Reconstruye la tabla de franjas con los lambdas recibidos como parámetro,
    en lugar de leer directamente las constantes globales.
    """
    return [
        (nombre, inicio, fin, lambda_pico if "pico" in nombre else lambda_normal)
        for nombre, inicio, fin, _ in FRANJAS
    ]
