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
    Si no existen secrets, usa variables de entorno cargadas desde .env.
    """

    try:
        postgres_secrets = st.secrets.get("postgres", None)
    except Exception:
        postgres_secrets = None

    if postgres_secrets:
        return {
            "host": postgres_secrets["host"],
            "port": int(postgres_secrets["port"]),
            "dbname": postgres_secrets["dbname"],
            "user": postgres_secrets["user"],
            "password": postgres_secrets["password"],
            "sslmode": postgres_secrets.get("sslmode", "require"),
        }

    return {
        "host": os.getenv("DB_HOST", "localhost"),
        "port": int(os.getenv("DB_PORT", "5432")),
        "dbname": os.getenv("DB_NAME", "iot_frio"),
        "user": os.getenv("DB_USER", "iot_user"),
        "password": os.getenv("DB_PASSWORD", "iot_password"),
        "sslmode": os.getenv("DB_SSLMODE", "prefer"),
    }

def get_time_delta(label):
    """
    Convierte la opción seleccionada en el sidebar
    a un rango de tiempo utilizable para filtrar datos.
    """

    if label == "Últimos 15 minutos":
        return pd.Timedelta(minutes=15)
    if label == "Última hora":
        return pd.Timedelta(hours=1)
    if label == "Últimas 3 horas":
        return pd.Timedelta(hours=3)
    if label == "Últimas 6 horas":
        return pd.Timedelta(hours=6)
    if label == "Últimas 12 horas":
        return pd.Timedelta(hours=12)
    if label == "Últimas 24 horas":
        return pd.Timedelta(hours=24)

    return None


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

time_window_label = st.sidebar.selectbox(
    "Rango de tiempo",
    options=[
        "Últimos 15 minutos",
        "Última hora",
        "Últimas 3 horas",
        "Últimas 6 horas",
        "Últimas 12 horas",
        "Últimas 24 horas",
        "Todo"
    ],
    index=1
)


# Filtro por equipo
df_filtered = df_readings[df_readings["device_id"].isin(selected_devices)].copy()

# Filtro por rango de tiempo
time_delta = get_time_delta(time_window_label)
min_timestamp = None
max_timestamp = None

if time_delta is not None and not df_filtered.empty:
    # Usamos la última lectura disponible como referencia,
    # no la hora actual del servidor.
    max_timestamp = df_filtered["timestamp_sensor"].max()
    min_timestamp = max_timestamp - time_delta

    df_filtered = df_filtered[
        df_filtered["timestamp_sensor"] >= min_timestamp
    ]


# Filtro de alertas
if not df_alerts.empty:
    df_alerts_filtered = df_alerts[df_alerts["device_id"].isin(selected_devices)].copy()

    if time_delta is not None and min_timestamp is not None:
        df_alerts_filtered = df_alerts_filtered[
            df_alerts_filtered["timestamp_alert"] >= min_timestamp
        ]
else:
    df_alerts_filtered = df_alerts


if df_filtered.empty:
    st.warning(
        "No hay lecturas para los filtros seleccionados. "
        "Probá ampliar el rango de tiempo o seleccionar otros equipos."
    )
    st.stop()


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


if time_window_label != "Todo" and min_timestamp is not None and max_timestamp is not None:
    st.caption(
        f"Mostrando datos desde {min_timestamp.strftime('%Y-%m-%d %H:%M:%S')} "
        f"hasta {max_timestamp.strftime('%Y-%m-%d %H:%M:%S')}."
    )
else:
    st.caption("Mostrando todos los datos disponibles para los filtros seleccionados.")


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


st.caption("Los datos se actualizan automáticamente cada 5 segundos.")