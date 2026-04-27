# DiscreteEventSimulationProject

[![Python](https://img.shields.io/badge/Python-3.x-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![Estado](https://img.shields.io/badge/Estado-Proyecto%20acad%C3%A9mico-orange.svg)]()

Proyecto académico de simulación de eventos discretos para la asignatura de Simulación de la Facultad de Matemática y Computación de la Universidad de La Habana. El sistema modela la cocina de "La Cocina de Kojo" con dos empleados permanentes y una variante con un tercer empleado que solo se activa en hora pico.

La simulación estima el porcentaje de clientes que esperan más de 5 minutos en cola y compara el desempeño de ambas variantes bajo distintos valores de llegada en hora pico.

## Tabla de contenidos

- [Descripción del sistema](#descripción-del-sistema)
- [Estructura del proyecto](#estructura-del-proyecto)
- [Fundamentos teóricos](#fundamentos-teóricos)
- [Instalación y ejecución](#instalación-y-ejecución)
- [Parámetros configurables](#parámetros-configurables)
- [Resultados y análisis](#resultados-y-análisis)
- [Decisiones de diseño](#decisiones-de-diseño)
- [Repositorio y autor](#repositorio-y-autor)

## Descripción del sistema

"La Cocina de Kojo" es un sistema de servicio de alimentos que abre de 10:00 a 21:00. Durante la jornada llegan clientes con distinta intensidad según la franja horaria: hay periodos normales y periodos pico. Cada cliente solicita un sándwich o sushi, y el tiempo de preparación depende del tipo de pedido.

El objetivo del proyecto es medir el impacto de la demanda sobre la espera en cola y, en particular, estimar qué porcentaje de clientes espera más de 5 minutos. También se compara si vale la pena incorporar un tercer empleado únicamente durante las horas pico.

## Estructura del proyecto

```text
kojo/
├── main.py                  # Punto de entrada: ejecuta ambas variantes y muestra resultados
├── core/
│   ├── parametros.py        # Parámetros del modelo, franjas horarias y constantes globales
│   ├── generacion.py        # Generación de variables aleatorias con Transformada Inversa
│   └── resultados.py        # Tablas de resultados, sensibilidad y comparación entre variantes
└── modelos/
    └── simulador.py         # Simulador unificado parametrizable para 2 o 3 empleados
```

## Fundamentos teóricos

La **simulación de eventos discretos (DES)** representa un sistema como una secuencia de eventos que ocurren en tiempos específicos. En lugar de avanzar el reloj minuto a minuto, el simulador salta de evento en evento: arribos, fin de servicio y cambios de franja horaria.

En este proyecto, los arribos se generan con una **distribución exponencial** por franja. Esto equivale a un proceso de Poisson homogéneo dentro de cada segmento horario. No se usa thinning ni un proceso no homogéneo completo, porque el enunciado permite trabajar con tasas constantes por tramo.

Las variables aleatorias se construyen desde cero mediante el **método de la Transformada Inversa (TTI)**:

- Interarribos: $X = -(1/\lambda) \ln(U)$
- Preparación de sándwich: $X = a + (b-a)U$, con $U \sim U(0,1)$
- Preparación de sushi: $X = a + (b-a)U$
- Tipo de cliente: $U < 0.5$ produce sándwich; en caso contrario, sushi

Otra decisión importante es representar a los servidores como un **contador de capacidad** en vez de usar variables booleanas separadas por empleado. Como los empleados son intercambiables, basta con saber cuántos están libres y cuántos pedidos están en servicio. Esa idea simplifica el código y permite escalar a más servidores sin reescribir la lógica central.

## Instalación y ejecución

```bash
git clone https://github.com/ronaldcbmtnz/DiscreteEventSimulationProject.git
cd DiscreteEventSimulationProject
python main.py
```

No se requieren dependencias externas: el proyecto usa solo la biblioteca estándar de Python.

## Parámetros configurables

Todos los parámetros del modelo se definen en `core/parametros.py`.

| Parámetro | Valor por defecto | Descripción |
|---|---:|---|
| `SEMILLA` | `None` | Semilla base para reproducibilidad. Si es `None`, cada corrida usa aleatoriedad del sistema. |
| `T_FIN` | `660` | Horizonte de simulación en minutos. Representa la jornada de 10:00 a 21:00. |
| `LAMBDA_NORMAL` | `0.15` | Tasa de llegada en franjas normales, en clientes/minuto. |
| `LAMBDA_PICO` | `0.30` | Tasa de llegada en franjas pico, en clientes/minuto. |
| `P_SANDWICH` | `0.50` | Probabilidad de que un cliente pida sándwich. El resto pide sushi. |
| `PREP_SANDWICH` | `(3, 5)` | Intervalo uniforme para el tiempo de preparación de sándwich, en minutos. |
| `PREP_SUSHI` | `(5, 8)` | Intervalo uniforme para el tiempo de preparación de sushi, en minutos. |
| `UMBRAL_QUEJA` | `5` | Un cliente genera queja si espera más de este valor en cola, en minutos. |
| `FRANJAS` | ver código | Lista de franjas horarias con nombre, inicio, fin y tasa activa. |
| `INDICES_PICO` | `{1, 3}` | Índices de las franjas que se consideran hora pico. |

### Franjas horarias del modelo

| Franja | Tipo | λ activo | Duración |
|---|---|---:|---:|
| 10:00 – 11:30 | Normal | `LAMBDA_NORMAL` | 90 min |
| 11:30 – 13:30 | Pico | `LAMBDA_PICO` | 120 min |
| 13:30 – 17:00 | Normal | `LAMBDA_NORMAL` | 210 min |
| 17:00 – 19:00 | Pico | `LAMBDA_PICO` | 120 min |
| 19:00 – 21:00 | Normal | `LAMBDA_NORMAL` | 120 min |

## Resultados y análisis

El programa ejecuta dos variantes:

- **2 empleados permanentes**
- **3 empleados**, donde el tercero solo opera en hora pico

Además, realiza un análisis de sensibilidad variando `λ_pico` y promediando 30 repeticiones por valor. La comparación relevante no se hace con el porcentaje global de quejas, sino con el **porcentaje de quejas en hora pico**, porque ese es el tramo en el que el tercer empleado realmente influye.

En los resultados promedio, cuando `λ_pico = 0.30`, el tercer empleado reduce las quejas en hora pico en aproximadamente **21 puntos porcentuales** frente al escenario con 2 empleados. Esa reducción justifica claramente la contratación temporal del tercer servidor en escenarios de presión moderada o alta.

La sensibilidad también muestra el punto en que el sistema comienza a saturarse: a medida que `λ_pico` crece, el porcentaje de quejas en pico aumenta con mucha más rapidez que el porcentaje global.

## Decisiones de diseño

- **Homogeneidad por segmento**: dentro de cada franja horaria se usa una tasa constante de llegadas. Eso simplifica la simulación y es consistente con el enunciado del problema.
- **Servidores por contador**: en lugar de mantener variables booleanas por empleado, el sistema usa `servidores_libres` y `capacidad_actual`. Esto hace que la lógica sea más compacta y escalable.
- **Chequeo de salida del tercer empleado**: si el tercer empleado deja la franja pico mientras aún atiende a un cliente, termina ese pedido y luego desaparece del sistema sin aceptar nuevos clientes.
- **Métrica de comparación correcta**: para evaluar el impacto del tercer empleado se usa `% Pico` y no `% Global`, porque el tercer servidor solo afecta las horas pico.

## Repositorio y autor

Repositorio: https://github.com/ronaldcbmtnz/DiscreteEventSimulationProject

Autor: **Ronald Cabrera Martínez**  
Grupo: **C-311**  
Facultad de Matemática y Computación  
Universidad de La Habana
