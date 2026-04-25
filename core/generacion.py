"""
================================================================================
core/generacion.py — Generación de variables aleatorias
================================================================================
Todas las funciones aplican el método de la Transformada Inversa (TTI):
dado U ~ Uniforme(0,1), se obtiene X = F⁻¹(U).

Este módulo es completamente independiente del modelo — no importa nada
de parametros.py para que pueda usarse en cualquier simulación futura.
Las distribuciones concretas del problema (rangos, probabilidades) se
pasan como argumentos, no se leen como globales.
================================================================================
"""

import math
import random


def gen_uniforme_01() -> float:
    """
    Genera U ~ Uniforme(0, 1).
    Es la fuente base de toda la generación en este simulador.
    """
    return random.random()


def gen_uniforme(a: float, b: float) -> float:
    """
    Genera X ~ Uniforme(a, b) por Transformada Inversa.

    Derivación:
        CDF:     F(x) = (x - a) / (b - a)
        Inversa: x = a + (b - a) * U

    Parámetros:
        a : límite inferior  (debe ser a < b)
        b : límite superior
    """
    U = gen_uniforme_01()
    return a + (b - a) * U


def gen_exponencial(lam: float) -> float:
    """
    Genera X ~ Exponencial(λ) por Transformada Inversa.

    Derivación:
        CDF:     F(x) = 1 - e^(-λx)
        Inversa: x = -1/λ * ln(U)
        Nota:    (1 - U) ~ Uniforme(0,1) igual que U, se simplifica.

    Parámetros:
        lam : tasa λ > 0  (media = 1/λ)
    """
    U = gen_uniforme_01()
    return -(1.0 / lam) * math.log(U)


def gen_tipo_cliente(p_sandwich: float) -> str:
    """
    Decide el tipo de pedido por inversión discreta.

    Método:
        Se parte [0, 1) en dos intervalos según probabilidades acumuladas:
            [0,          p_sandwich)  →  'sandwich'
            [p_sandwich, 1)           →  'sushi'

    Parámetros:
        p_sandwich : probabilidad de pedir sándwich ∈ (0, 1)
    """
    U = gen_uniforme_01()
    return "sandwich" if U < p_sandwich else "sushi"


def gen_tiempo_prep(tipo: str, prep_sandwich: tuple, prep_sushi: tuple) -> float:
    """
    Genera el tiempo de preparación de un pedido según su tipo.

    Parámetros:
        tipo          : 'sandwich' o 'sushi'
        prep_sandwich : (a, b) de la Uniforme para sándwich
        prep_sushi    : (a, b) de la Uniforme para sushi
    """
    if tipo == "sandwich":
        return gen_uniforme(*prep_sandwich)
    else:
        return gen_uniforme(*prep_sushi)
