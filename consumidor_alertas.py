import os
import json
from datetime import datetime

import paho.mqtt.client as mqtt
import psycopg2
from psycopg2.extras import Json
from dotenv import load_dotenv

    
load_dotenv()

MQTT_HOST = os.getenv("MQTT_HOST", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
TOPIC = "sensores/frio/#"

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "5432")),
    "dbname": os.getenv("DB_NAME", "iot_frio"),
    "user": os.getenv("DB_USER", "iot_user"),
    "password": os.getenv("DB_PASSWORD", "iot_password"),
    "sslmode": os.getenv("DB_SSLMODE", "prefer"),
}


def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)


def guardar_lectura(conn, topic, payload):
    """
    Guarda una lectura recibida por MQTT en PostgreSQL.
    Devuelve el ID de la lectura insertada.
    """

    query = """
        INSERT INTO sensor_readings (
            topic,
            device_id,
            device_type,
            timestamp_sensor,
            temperature_c,
            temperature_min_c,
            temperature_max_c,
            power_kw,
            door_open,
            compressor_on,
            battery_pct,
            rssi,
            raw_payload
        )
        VALUES (
            %(topic)s,
            %(device_id)s,
            %(device_type)s,
            %(timestamp_sensor)s,
            %(temperature_c)s,
            %(temperature_min_c)s,
            %(temperature_max_c)s,
            %(power_kw)s,
            %(door_open)s,
            %(compressor_on)s,
            %(battery_pct)s,
            %(rssi)s,
            %(raw_payload)s
        )
        RETURNING id;
    """

    values = {
        "topic": topic,
        "device_id": payload.get("device_id", "desconocido"),
        "device_type": payload.get("device_type"),
        "timestamp_sensor": payload.get("timestamp"),
        "temperature_c": payload.get("temperature_c"),
        "temperature_min_c": payload.get("temperature_min_c"),
        "temperature_max_c": payload.get("temperature_max_c"),
        "power_kw": payload.get("power_kw"),
        "door_open": payload.get("door_open"),
        "compressor_on": payload.get("compressor_on"),
        "battery_pct": payload.get("battery_pct"),
        "rssi": payload.get("rssi"),
        "raw_payload": Json(payload),
    }

    with conn.cursor() as cur:
        cur.execute(query, values)
        reading_id = cur.fetchone()[0]

    conn.commit()
    return reading_id


def guardar_alertas(conn, reading_id, device_id, alertas):
    """
    Guarda las alertas detectadas en PostgreSQL.
    """

    if not alertas:
        return

    query = """
        INSERT INTO sensor_alerts (
            reading_id,
            device_id,
            alert_type,
            severity,
            message
        )
        VALUES (
            %(reading_id)s,
            %(device_id)s,
            %(alert_type)s,
            %(severity)s,
            %(message)s
        );
    """

    with conn.cursor() as cur:
        for alerta in alertas:
            values = {
                "reading_id": reading_id,
                "device_id": device_id,
                "alert_type": alerta["tipo"],
                "severity": alerta["severidad"],
                "message": alerta["mensaje"],
            }

            cur.execute(query, values)

    conn.commit()


def evaluar_alertas(payload):
    """
    Recibe el payload como diccionario Python
    y devuelve una lista de alertas detectadas.
    """

    alertas = []

    device_id = payload.get("device_id", "desconocido")
    temperature = payload.get("temperature_c")
    temp_min = payload.get("temperature_min_c")
    temp_max = payload.get("temperature_max_c")
    power_kw = payload.get("power_kw")
    door_open = payload.get("door_open")
    battery_pct = payload.get("battery_pct")
    rssi = payload.get("rssi")
    event_flags = payload.get("event_flags", {})

    if temperature is not None and temp_max is not None:
        if temperature > temp_max:
            alertas.append({
                "tipo": "TEMPERATURA_ALTA",
                "severidad": "CRITICA",
                "mensaje": (
                    f"Equipo {device_id}: temperatura alta. "
                    f"Actual: {temperature} °C | Máximo permitido: {temp_max} °C"
                )
            })

    if temperature is not None and temp_min is not None:
        if temperature < temp_min:
            alertas.append({
                "tipo": "TEMPERATURA_BAJA",
                "severidad": "MEDIA",
                "mensaje": (
                    f"Equipo {device_id}: temperatura baja. "
                    f"Actual: {temperature} °C | Mínimo permitido: {temp_min} °C"
                )
            })

    if door_open is True:
        alertas.append({
            "tipo": "PUERTA_ABIERTA",
            "severidad": "BAJA",
            "mensaje": f"Equipo {device_id}: puerta abierta."
        })

    if battery_pct is not None and battery_pct < 20:
        alertas.append({
            "tipo": "BATERIA_BAJA",
            "severidad": "MEDIA",
            "mensaje": f"Equipo {device_id}: batería baja ({battery_pct}%)."
        })

    if rssi is not None and rssi < -80:
        alertas.append({
            "tipo": "SENAL_DEBIL",
            "severidad": "MEDIA",
            "mensaje": f"Equipo {device_id}: señal débil. RSSI: {rssi} dBm."
        })

    if event_flags.get("power_anomaly") is True:
        alertas.append({
            "tipo": "CONSUMO_ANOMALO",
            "severidad": "ALTA",
            "mensaje": (
                f"Equipo {device_id}: posible consumo anómalo. "
                f"Consumo actual: {power_kw} kW."
            )
        })

    if event_flags.get("temp_drift") is True:
        alertas.append({
            "tipo": "DESVIO_TEMPERATURA",
            "severidad": "ALTA",
            "mensaje": f"Equipo {device_id}: se detectó un desvío de temperatura simulado."
        })

    return alertas


def on_connect(client, userdata, flags, reason_code, properties=None):
    print("Consumidor conectado al broker MQTT")
    print(f"Suscripto a: {TOPIC}")
    print("-" * 80)

    client.subscribe(TOPIC)


def on_message(client, userdata, msg):
    topic = msg.topic
    raw_payload = msg.payload.decode("utf-8")

    try:
        payload = json.loads(raw_payload)
    except json.JSONDecodeError:
        print("Mensaje recibido, pero no es JSON válido")
        print(f"Tópico: {topic}")
        print(f"Payload: {raw_payload}")
        print("-" * 80)
        return

    device_id = payload.get("device_id", "desconocido")
    timestamp = payload.get("timestamp", "sin_timestamp")
    temperature = payload.get("temperature_c")
    power_kw = payload.get("power_kw")

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Mensaje recibido")
    print(f"Tópico: {topic}")
    print(f"Equipo: {device_id}")
    print(f"Timestamp sensor: {timestamp}")
    print(f"Temperatura: {temperature} °C")
    print(f"Consumo: {power_kw} kW")

    alertas = evaluar_alertas(payload)

    try:
        conn = get_db_connection()

        reading_id = guardar_lectura(conn, topic, payload)
        guardar_alertas(conn, reading_id, device_id, alertas)

        conn.close()

        print(f"Lectura guardada en PostgreSQL. reading_id: {reading_id}")

    except Exception as e:
        print("ERROR guardando en PostgreSQL")
        print(e)

    if alertas:
        print("")
        print("ALERTAS DETECTADAS:")

        for alerta in alertas:
            print(f"- [{alerta['severidad']}] {alerta['tipo']}: {alerta['mensaje']}")
    else:
        print("Sin alertas.")

    print("-" * 80)


def main():
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)

    client.on_connect = on_connect
    client.on_message = on_message

    print("Iniciando consumidor de alertas...")
    print(f"Broker MQTT: {MQTT_HOST}:{MQTT_PORT}")
    print(f"PostgreSQL: {DB_CONFIG['host']}:{DB_CONFIG['port']} / DB: {DB_CONFIG['dbname']}")

    client.connect(MQTT_HOST, MQTT_PORT, 60)

    client.loop_forever()


if __name__ == "__main__":
    main()