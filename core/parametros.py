"""
================================================================================
core/parametros.py — Parámetros del modelo
================================================================================
Único lugar donde se definen las constantes del modelo.
Cualquier variante del simulador (2 o 3 empleados) importa desde aquí.

Para ajustar el modelo, solo hay que modificar este archivo.
================================================================================
"""

# ── Reproducibilidad ─────────────────────────────────────────────────────────
# Fijar un entero para resultados reproducibles.
# Cambiar a None para obtener resultados distintos en cada corrida.
SEMILLA = 42

# ── Horizonte de simulación ───────────────────────────────────────────────────
# El día empieza a las 10:00 (t = 0) y termina a las 21:00 (t = 660 min).
T_FIN = 660  # minutos

# ── Tasas de arribo (clientes por minuto) ─────────────────────────────────────
# λ = 0.15  →  1 cliente cada ~6.7 min  (horario normal, sistema cómodo)
# λ = 0.30  →  1 cliente cada ~3.3 min  (hora pico, sistema bajo presión)
LAMBDA_NORMAL = 0.15
LAMBDA_PICO   = 0.30

# ── Composición de la demanda ─────────────────────────────────────────────────
# Probabilidad de que un cliente pida sándwich (el resto pide sushi).
P_SANDWICH = 0.50

# ── Tiempos de preparación en minutos [a, b] ──────────────────────────────────
# Distribuyen Uniforme(a, b) — cualquier valor en el rango es igualmente probable.
PREP_SANDWICH = (3, 5)   # Uniforme(3, 5) → media 4.0 min
PREP_SUSHI    = (5, 8)   # Uniforme(5, 8) → media 6.5 min

# ── Umbral de queja ───────────────────────────────────────────────────────────
# Un cliente genera queja si su espera en cola supera este valor.
UMBRAL_QUEJA = 5  # minutos

# ── Franjas horarias ──────────────────────────────────────────────────────────
# Cada entrada: (nombre_descriptivo, minuto_inicio, minuto_fin, lambda_activo)
# Los minutos son relativos a las 10:00 (t = 0).
#
# El tercer empleado estará activo en las franjas marcadas como PICO.
# Esas franjas son los índices 1 y 3 de esta lista.
FRANJAS = [
    ("10:00–11:30 (normal)", 0,   90,  LAMBDA_NORMAL),   # idx 0
    ("11:30–13:30 (pico)",   90,  210, LAMBDA_PICO),     # idx 1 ← pico
    ("13:30–17:00 (normal)", 210, 420, LAMBDA_NORMAL),   # idx 2
    ("17:00–19:00 (pico)",   420, 540, LAMBDA_PICO),     # idx 3 ← pico
    ("19:00–21:00 (normal)", 540, 660, LAMBDA_NORMAL),   # idx 4
]

# Índices de las franjas que corresponden a hora pico
# (el tercer empleado se activa/desactiva en estas transiciones)
INDICES_PICO = {1, 3}
