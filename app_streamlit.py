import os

import pandas as pd
import psycopg2
import streamlit as st
from dotenv import load_dotenv
from streamlit_autorefresh import st_autorefresh

load_dotenv()


def get_db_config():
    """
    Lee configuración de PostgreSQL desde Streamlit secrets si existen.
    Si no, usa variables de entorno cargadas desde .env.
    """

    if "postgres" in st.secrets:
        return {
            "host": st.secrets["postgres"]["host"],
            "port": int(st.secrets["postgres"]["port"]),
            "dbname": st.secrets["postgres"]["dbname"],
            "user": st.secrets["postgres"]["user"],
            "password": st.secrets["postgres"]["password"],
            "sslmode": st.secrets["postgres"].get("sslmode", "require"),
        }

    return {
        "host": os.getenv("DB_HOST", "localhost"),
        "port": int(os.getenv("DB_PORT", "5432")),
        "dbname": os.getenv("DB_NAME", "iot_frio"),
        "user": os.getenv("DB_USER", "iot_user"),
        "password": os.getenv("DB_PASSWORD", "iot_password"),
        "sslmode": os.getenv("DB_SSLMODE", "prefer"),
    }


DB_CONFIG = get_db_config()


st.set_page_config(
    page_title="IoT Frío - Monitoreo",
    page_icon="❄️",
    layout="wide"
)

st_autorefresh(interval=5000, key="data_refresh")


@st.cache_data(ttl=5)
def cargar_lecturas():
    query = """
        SELECT
            id,
            topic,
            device_id,
            device_type,
            timestamp_sensor,
            timestamp_received,
            temperature_c,
            temperature_min_c,
            temperature_max_c,
            power_kw,
            door_open,
            compressor_on,
            battery_pct,
            rssi
        FROM sensor_readings
        ORDER BY timestamp_sensor DESC;
    """

    conn = psycopg2.connect(**DB_CONFIG)
    df = pd.read_sql_query(query, conn)
    conn.close()

    return df


@st.cache_data(ttl=5)
def cargar_alertas():
    query = """
        SELECT
            id,
            reading_id,
            device_id,
            timestamp_alert,
            alert_type,
            severity,
            message
        FROM sensor_alerts
        ORDER BY timestamp_alert DESC;
    """

    conn = psycopg2.connect(**DB_CONFIG)
    df = pd.read_sql_query(query, conn)
    conn.close()

    return df


st.title("❄️ IoT Frío - Monitoreo de Sistemas Frigoríficos")

st.caption(
    "Dashboard operativo inicial alimentado por datos simulados vía MQTT, "
    "procesados por Python y almacenados en PostgreSQL."
)

try:
    df_readings = cargar_lecturas()
    df_alerts = cargar_alertas()

except Exception as e:
    st.error("No se pudo conectar a PostgreSQL.")
    st.exception(e)
    st.stop()


if df_readings.empty:
    st.warning("Todavía no hay lecturas guardadas en la base.")
    st.stop()


# Conversión de fechas
df_readings["timestamp_sensor"] = pd.to_datetime(df_readings["timestamp_sensor"])
df_readings["timestamp_received"] = pd.to_datetime(df_readings["timestamp_received"])

if not df_alerts.empty:
    df_alerts["timestamp_alert"] = pd.to_datetime(df_alerts["timestamp_alert"])


# Sidebar de filtros
st.sidebar.header("Filtros")

devices = sorted(df_readings["device_id"].dropna().unique())

selected_devices = st.sidebar.multiselect(
    "Equipos",
    options=devices,
    default=devices
)

df_filtered = df_readings[df_readings["device_id"].isin(selected_devices)]

if not df_alerts.empty:
    df_alerts_filtered = df_alerts[df_alerts["device_id"].isin(selected_devices)]
else:
    df_alerts_filtered = df_alerts


# KPIs principales
total_lecturas = len(df_filtered)
total_alertas = len(df_alerts_filtered)
equipos_activos = df_filtered["device_id"].nunique()
temp_promedio = df_filtered["temperature_c"].mean()
consumo_promedio = df_filtered["power_kw"].mean()

col1, col2, col3, col4, col5 = st.columns(5)

col1.metric("Lecturas", f"{total_lecturas:,}")
col2.metric("Alertas", f"{total_alertas:,}")
col3.metric("Equipos", equipos_activos)
col4.metric("Temp. promedio", f"{temp_promedio:.2f} °C")
col5.metric("Consumo prom.", f"{consumo_promedio:.3f} kW")


st.divider()


# Estado actual por equipo
st.subheader("Estado actual por equipo")

idx_last = df_filtered.groupby("device_id")["timestamp_sensor"].idxmax()
df_current = df_filtered.loc[idx_last].sort_values("device_id")

st.dataframe(
    df_current[
        [
            "device_id",
            "device_type",
            "timestamp_sensor",
            "temperature_c",
            "temperature_min_c",
            "temperature_max_c",
            "power_kw",
            "door_open",
            "compressor_on",
            "battery_pct",
            "rssi",
        ]
    ],
    use_container_width=True,
    hide_index=True
)


st.divider()


# Gráficos
st.subheader("Evolución de temperatura")

for device in selected_devices:
    df_device = df_filtered[df_filtered["device_id"] == device].sort_values("timestamp_sensor")

    if not df_device.empty:
        st.markdown(f"**{device}**")

        chart_df = df_device.set_index("timestamp_sensor")[
            ["temperature_c", "temperature_min_c", "temperature_max_c"]
        ]

        st.line_chart(chart_df)


st.divider()


st.subheader("Evolución de consumo eléctrico")

for device in selected_devices:
    df_device = df_filtered[df_filtered["device_id"] == device].sort_values("timestamp_sensor")

    if not df_device.empty:
        st.markdown(f"**{device}**")

        chart_df = df_device.set_index("timestamp_sensor")[["power_kw"]]

        st.line_chart(chart_df)


st.divider()


# Alertas
st.subheader("Últimas alertas")

if df_alerts_filtered.empty:
    st.success("No hay alertas registradas para los filtros seleccionados.")
else:
    st.dataframe(
        df_alerts_filtered[
            [
                "id",
                "reading_id",
                "device_id",
                "timestamp_alert",
                "alert_type",
                "severity",
                "message",
            ]
        ].head(50),
        use_container_width=True,
        hide_index=True
    )


st.divider()


# Resumen de alertas
st.subheader("Resumen de alertas por tipo")

if df_alerts_filtered.empty:
    st.info("No hay alertas para resumir.")
else:
    df_alert_summary = (
        df_alerts_filtered
        .groupby(["alert_type", "severity"])
        .size()
        .reset_index(name="cantidad")
        .sort_values("cantidad", ascending=False)
    )

    st.dataframe(
        df_alert_summary,
        use_container_width=True,
        hide_index=True
    )


st.caption("Los datos se actualizan automáticamente cada 5 segundos")