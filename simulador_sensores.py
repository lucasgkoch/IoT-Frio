import os
import json
import time
import random
from datetime import datetime, timezone

import paho.mqtt.client as mqtt
from dotenv import load_dotenv

load_dotenv()


MQTT_HOST = os.getenv("MQTT_HOST", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))

CLIENTE = "cliente_001"
SUCURSAL = "sucursal_centro"

EQUIPOS = [
    {
        "device_id": "camara_01",
        "device_type": "camara_congelado",
        "temp_objetivo": -18.0,
        "temp_min": -22.0,
        "temp_max": -15.0,
        "power_base_kw": 1.8
    },
    {
        "device_id": "camara_02",
        "device_type": "camara_refrigerado",
        "temp_objetivo": 4.0,
        "temp_min": 1.0,
        "temp_max": 8.0,
        "power_base_kw": 1.2
    },
    {
        "device_id": "heladera_01",
        "device_type": "heladera_comercial",
        "temp_objetivo": 5.0,
        "temp_min": 2.0,
        "temp_max": 9.0,
        "power_base_kw": 0.45
    }
]


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def generar_lectura(equipo):
    """
    Genera una lectura simulada para un equipo frigorífico.
    """

    # Temperatura normal alrededor del objetivo
    temperature = random.gauss(equipo["temp_objetivo"], 0.6)

    # Simulación de puerta abierta
    door_open = random.random() < 0.08

    if door_open:
        temperature += random.uniform(0.5, 2.5)

    # Simulación de desvío de temperatura
    temp_drift = random.random() < 0.03

    if temp_drift:
        temperature += random.uniform(3.0, 7.0)

    # El compresor se prende si la temperatura está por encima del objetivo
    compressor_on = temperature > equipo["temp_objetivo"] + 0.3

    # Consumo eléctrico según estado del compresor
    if compressor_on:
        power_kw = random.gauss(equipo["power_base_kw"], 0.15)
    else:
        power_kw = random.gauss(equipo["power_base_kw"] * 0.25, 0.05)

    # Simulación de consumo anómalo
    power_anomaly = random.random() < 0.02

    if power_anomaly:
        power_kw *= random.uniform(1.8, 2.8)

    payload = {
        "device_id": equipo["device_id"],
        "device_type": equipo["device_type"],
        "timestamp": now_iso(),
        "temperature_c": round(temperature, 2),
        "temperature_min_c": equipo["temp_min"],
        "temperature_max_c": equipo["temp_max"],
        "power_kw": round(max(power_kw, 0), 3),
        "door_open": door_open,
        "compressor_on": compressor_on,
        "battery_pct": random.randint(80, 100),
        "rssi": random.randint(-85, -45),
        "event_flags": {
            "temp_drift": temp_drift,
            "power_anomaly": power_anomaly
        }
    }

    return payload


def main():
    client = mqtt.Client()
    client.connect(MQTT_HOST, MQTT_PORT, 60)

    print("Simulador MQTT iniciado")
    print(f"Broker: {MQTT_HOST}:{MQTT_PORT}")
    print("Publicando lecturas cada 5 segundos...")
    print("Presioná Ctrl + C para detenerlo")
    print("-" * 80)

    while True:
        for equipo in EQUIPOS:
            topic = (
                f"sensores/frio/"
                f"{CLIENTE}/"
                f"{SUCURSAL}/"
                f"{equipo['device_id']}/"
                f"telemetria"
            )

            payload = generar_lectura(equipo)

            client.publish(topic, json.dumps(payload))

            print(f"Publicado en: {topic}")
            print(json.dumps(payload, indent=2))
            print("-" * 80)

        time.sleep(5)


if __name__ == "__main__":
    main()