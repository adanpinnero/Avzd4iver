"""Catálogo de protocolos guiados paso a paso.

Cada protocolo es una lista de pasos cortos. La UI los reproduce uno a uno
por TTS, esperando confirmación del conductor antes de avanzar.
"""

from __future__ import annotations


PROTOCOLS: dict[str, dict] = {
    "pasajero_inconsciente": {
        "title": "Pasajero inconsciente o con posible infarto",
        "steps": [
            "Detén el vehículo en zona segura y activa luces de emergencia.",
            "Pide por radio a central una ambulancia indicando tu posición.",
            "Pide ayuda a pasajeros para despejar el entorno del afectado.",
            "Verifica pulso y respiración. Si no respira, inicia reanimación.",
            "Acompaña a los servicios de emergencia cuando lleguen.",
            "Permanece localizable hasta que central autorice reanudar ruta.",
        ],
    },
    "pelea": {
        "title": "Pelea entre pasajeros",
        "steps": [
            "Detén el vehículo en zona segura y activa luces de emergencia.",
            "No intervengas físicamente. Activa alerta a central por radio.",
            "Solicita a los pasajeros implicados bajar del vehículo.",
            "Si persiste, permanece en cabina y espera a la policía.",
            "Recoge testigos si hay lesiones: nombre y contacto.",
            "Registra la incidencia antes de reanudar el turno.",
        ],
    },
    "choque_leve": {
        "title": "Choque leve sin heridos",
        "steps": [
            "Detén el vehículo. Activa emergencias. No obstaculices la vía.",
            "Comprueba que no hay heridos en tu bus ni en el otro vehículo.",
            "Avisa a central por radio con tu posición y matrícula contraria.",
            "Intercambia datos de seguro con el otro conductor.",
            "Toma fotos de daños, matrículas y posición de vehículos.",
            "Rellena el parte amistoso o espera a la grúa según instruya central.",
        ],
    },
    "objeto_sospechoso": {
        "title": "Objeto sospechoso abandonado",
        "steps": [
            "No toques el objeto ni permitas que nadie se acerque.",
            "Detén el vehículo en zona abierta y abre todas las puertas.",
            "Evacúa a los pasajeros a al menos 50 metros.",
            "Avisa a central indicando descripción del objeto y ubicación.",
            "Aleja tú mismo a la misma distancia. Espera a los TEDAX.",
            "No uses la radio cerca del objeto si central lo indica.",
        ],
    },
    "averia_tunel": {
        "title": "Avería o parada en túnel",
        "steps": [
            "Activa luces de emergencia. Intenta salir del túnel si es posible.",
            "Si no es posible, detén el vehículo y apaga el motor.",
            "Abre puertas. Ordena a pasajeros salir por lado seguro.",
            "Dirige al grupo a la salida más cercana a pie.",
            "Avisa a central con kilómetro y sentido del túnel.",
            "No vuelvas al vehículo hasta autorización de bomberos o central.",
        ],
    },
    "agresion_conductor": {
        "title": "Agresión directa al conductor",
        "steps": [
            "Mantén la cabina cerrada. No respondas a la provocación.",
            "Activa alerta roja por voz o botón de pánico.",
            "Detén el vehículo en zona iluminada con testigos cerca.",
            "Abre puertas traseras y pide al agresor bajar.",
            "Si tienes lesiones, no reinicies marcha. Espera asistencia.",
            "Registra la incidencia con fotos y testigos antes de acabar turno.",
        ],
    },
    "evacuacion_emergencia": {
        "title": "Evacuación total del autobús",
        "steps": [
            "Detén el vehículo. Activa emergencias y freno de estacionamiento.",
            "Abre todas las puertas y las claraboyas si es necesario.",
            "Indica en voz alta: salir por puerta central y trasera.",
            "Si hay fuego, coge el extintor. Si no lo controlas, evacúa.",
            "Reúne a los pasajeros a 20 metros del vehículo.",
            "Avisa a central con tu posición exacta y naturaleza del riesgo.",
        ],
    },
}


def list_protocols() -> list[tuple[str, str]]:
    return [(k, v["title"]) for k, v in PROTOCOLS.items()]


def get_protocol(key: str) -> dict | None:
    return PROTOCOLS.get(key)
