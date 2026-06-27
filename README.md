# IoT Frío - Simulación de Sensores MQTT

Este proyecto es un prototipo local para simular sensores IoT aplicados al monitoreo de sistemas frigoríficos, como cámaras frigoríficas, heladeras comerciales u otros equipos de refrigeración.

El objetivo es simular la emisión de datos por MQTT, procesar esos mensajes desde un consumidor en Python, detectar alertas básicas, guardar la información en PostgreSQL y visualizar el estado operativo mediante una app en Streamlit.

---

## Arquitectura actual

```text
simulador_sensores.py
↓ publica mensajes MQTT
Mosquitto
↓ distribuye mensajes MQTT
consumidor_alertas.py
↓ procesa lecturas y alertas
PostgreSQL
↓ consulta de datos
Streamlit / DBeaver
```

---

## Componentes

### Mosquitto

Broker MQTT ejecutado en Docker. Recibe los mensajes publicados por el simulador y los distribuye a los clientes suscriptos.

### PostgreSQL

Base de datos ejecutada en Docker. Guarda las lecturas de sensores y las alertas detectadas.

### simulador_sensores.py

Script que simula sensores de sistemas frigoríficos. Publica lecturas periódicas por MQTT.

Actualmente simula:

- Temperatura.
- Consumo eléctrico.
- Estado de puerta abierta/cerrada.
- Estado del compresor.
- Batería del sensor.
- Señal RSSI.
- Eventos anómalos simulados.

### consumidor_alertas.py

Script que se suscribe a los tópicos MQTT, recibe las lecturas, evalúa reglas básicas de alerta y guarda la información en PostgreSQL.

Actualmente detecta:

- Temperatura alta.
- Temperatura baja.
- Puerta abierta.
- Batería baja.
- Señal débil.
- Consumo anómalo simulado.
- Desvío de temperatura simulado.

### app_streamlit.py

Dashboard operativo inicial desarrollado con Streamlit.

Permite visualizar:

- Cantidad de lecturas.
- Cantidad de alertas.
- Equipos activos.
- Temperatura promedio.
- Consumo promedio.
- Estado actual por equipo.
- Evolución de temperatura.
- Evolución de consumo eléctrico.
- Últimas alertas.
- Resumen de alertas por tipo.

---

## Estructura del proyecto

```text
iot-frio/
├── app_streamlit.py
├── consumidor_alertas.py
├── simulador_sensores.py
├── docker-compose.yml
├── requirements.txt
├── README.md
├── .env
├── .env.example
├── .gitignore
│
├── mosquitto/
│   └── mosquitto.conf
│
└── sql/
    └── init.sql
```

---

## Requisitos

- Python 3.x
- Docker Desktop
- DBeaver Community, opcional pero recomendado
- Navegador web para visualizar Streamlit

---

## Variables de entorno

El proyecto utiliza un archivo `.env` para configurar la conexión a MQTT y PostgreSQL.

El archivo `.env` no se sube al repositorio por seguridad. En su lugar, se incluye un archivo `.env.example` como plantilla.

Para crear el `.env` local:

```powershell
Copy-Item .env.example .env
```

Contenido esperado:

```env
# MQTT
MQTT_HOST=localhost
MQTT_PORT=1883

# PostgreSQL
DB_HOST=localhost
DB_PORT=5432
DB_NAME=iot_frio
DB_USER=iot_user
DB_PASSWORD=iot_password
```

---

## Dependencias Python

Instalar dependencias con:

```powershell
py -m pip install -r requirements.txt
```

O alternativamente:

```powershell
python -m pip install -r requirements.txt
```

El archivo `requirements.txt` contiene:

```txt
paho-mqtt
psycopg2-binary
streamlit
pandas
streamlit-autorefresh
python-dotenv
```

---

## Infraestructura con Docker Compose

El proyecto utiliza Docker Compose para levantar los servicios de infraestructura:

- Mosquitto
- PostgreSQL

Para levantar los servicios:

```powershell
docker compose up -d
```

Para verificar que estén corriendo:

```powershell
docker compose ps
```

O también:

```powershell
docker ps
```

Deberían aparecer servicios similares a:

```text
mosquitto-iot-frio
postgres-iot-frio
```

---

## Configuración de Mosquitto

Archivo:

```text
mosquitto/mosquitto.conf
```

Contenido:

```conf
listener 1883
allow_anonymous true

persistence true
persistence_location /mosquitto/data/

log_dest stdout
log_type all
```

En esta etapa se permite conexión anónima para facilitar las pruebas locales.

Para un entorno productivo se debería configurar autenticación, usuarios, contraseñas y TLS.

---

## Configuración de PostgreSQL

PostgreSQL se levanta desde Docker Compose usando las variables definidas en `.env`.

Datos por defecto:

```text
Host: localhost
Port: 5432
Database: iot_frio
User: iot_user
Password: iot_password
```

---

## Inicialización de base de datos

El archivo:

```text
sql/init.sql
```

crea automáticamente las tablas necesarias cuando PostgreSQL se inicializa con un volumen nuevo.

Tablas creadas:

- `sensor_readings`
- `sensor_alerts`

También se crean índices básicos para mejorar consultas por equipo, fecha y tipo de alerta.

---

## Tablas

### sensor_readings

Guarda una fila por cada lectura recibida desde MQTT.

Campos principales:

- `id`
- `topic`
- `device_id`
- `device_type`
- `timestamp_sensor`
- `timestamp_received`
- `temperature_c`
- `temperature_min_c`
- `temperature_max_c`
- `power_kw`
- `door_open`
- `compressor_on`
- `battery_pct`
- `rssi`
- `raw_payload`

### sensor_alerts

Guarda una fila por cada alerta detectada.

Campos principales:

- `id`
- `reading_id`
- `device_id`
- `timestamp_alert`
- `alert_type`
- `severity`
- `message`

---

## Tópicos MQTT

Formato general:

```text
sensores/frio/{cliente}/{sucursal}/{equipo}/telemetria
```

Ejemplo:

```text
sensores/frio/cliente_001/sucursal_centro/camara_01/telemetria
```

Para escuchar todos los mensajes:

```text
sensores/frio/#
```

---

## Ejecución del proyecto

### 1. Levantar infraestructura

Desde la carpeta raíz del proyecto:

```powershell
cd C:\IOT\iot-frio
docker compose up -d
```

### 2. Instalar dependencias

```powershell
py -m pip install -r requirements.txt
```

### 3. Ejecutar consumidor

En una terminal:

```powershell
py consumidor_alertas.py
```

Este proceso queda escuchando mensajes MQTT, procesando lecturas, detectando alertas y guardando datos en PostgreSQL.

### 4. Ejecutar simulador

En otra terminal:

```powershell
py simulador_sensores.py
```

Este proceso publica lecturas simuladas cada pocos segundos.

### 5. Ejecutar dashboard Streamlit

En otra terminal:

```powershell
py -m streamlit run app_streamlit.py
```

La app debería abrirse en el navegador en una URL similar a:

```text
http://localhost:8501
```

---

## Flujo recomendado de terminales

### Terminal 1 - Consumidor

```powershell
cd C:\IOT\iot-frio
py consumidor_alertas.py
```

### Terminal 2 - Simulador

```powershell
cd C:\IOT\iot-frio
py simulador_sensores.py
```

### Terminal 3 - Streamlit

```powershell
cd C:\IOT\iot-frio
py -m streamlit run app_streamlit.py
```

Docker Desktop mantiene corriendo:

```text
Mosquitto
PostgreSQL
```

---

## Consultas útiles en PostgreSQL

Cantidad de lecturas por equipo:

```sql
SELECT 
    device_id,
    COUNT(*) AS cantidad_lecturas,
    MIN(timestamp_sensor) AS primera_lectura,
    MAX(timestamp_sensor) AS ultima_lectura,
    ROUND(AVG(temperature_c), 2) AS temperatura_promedio,
    ROUND(AVG(power_kw), 3) AS consumo_promedio_kw
FROM sensor_readings
GROUP BY device_id
ORDER BY device_id;
```

Alertas por tipo:

```sql
SELECT 
    alert_type,
    severity,
    COUNT(*) AS cantidad
FROM sensor_alerts
GROUP BY alert_type, severity
ORDER BY cantidad DESC;
```

Alertas por equipo:

```sql
SELECT 
    device_id,
    alert_type,
    COUNT(*) AS cantidad
FROM sensor_alerts
GROUP BY device_id, alert_type
ORDER BY device_id, cantidad DESC;
```

Últimas lecturas con alerta asociada:

```sql
SELECT 
    r.id AS reading_id,
    r.device_id,
    r.timestamp_sensor,
    r.temperature_c,
    r.power_kw,
    r.door_open,
    r.compressor_on,
    a.alert_type,
    a.severity,
    a.message
FROM sensor_readings r
LEFT JOIN sensor_alerts a
    ON r.id = a.reading_id
ORDER BY r.id DESC
LIMIT 50;
```

Total de lecturas y alertas:

```sql
SELECT 
    (SELECT COUNT(*) FROM sensor_readings) AS total_lecturas,
    (SELECT COUNT(*) FROM sensor_alerts) AS total_alertas;
```

---

## Uso con DBeaver

Para conectarse desde DBeaver:

```text
Host: localhost
Port: 5432
Database: iot_frio
Username: iot_user
Password: iot_password
```

Si aparece un error relacionado con zona horaria como:

```text
invalid value for parameter "TimeZone": "America/Buenos_Aires"
```

editar el archivo `dbeaver.ini` y agregar debajo de `-vmargs`:

```text
-Duser.timezone=UTC
```

Luego reiniciar DBeaver.

---

## Comandos útiles de Docker Compose

Levantar servicios:

```powershell
docker compose up -d
```

Ver servicios:

```powershell
docker compose ps
```

Ver logs:

```powershell
docker compose logs
```

Ver logs en vivo:

```powershell
docker compose logs -f
```

Frenar servicios sin eliminarlos:

```powershell
docker compose stop
```

Volver a iniciar servicios detenidos:

```powershell
docker compose start
```

Frenar y remover contenedores, conservando volúmenes:

```powershell
docker compose down
```

Frenar y borrar también los volúmenes:

```powershell
docker compose down -v
```

Cuidado: `docker compose down -v` borra los volúmenes y, por lo tanto, los datos de PostgreSQL.

---

## Comandos útiles de prueba MQTT

Escuchar todos los mensajes del proyecto:

```powershell
docker exec -it mosquitto-iot-frio mosquitto_sub -h localhost -t "sensores/frio/#"
```

Publicar un mensaje manual:

```powershell
docker exec -it mosquitto-iot-frio mosquitto_pub -h localhost -t "sensores/frio/cliente_001/sucursal_centro/camara_01/telemetria" -m "{""device_id"":""camara_01"",""temperature_c"":-18.4,""power_kw"":1.82}"
```

---

## Notas sobre seguridad

Este proyecto está pensado como prototipo local.

Actualmente:

- Mosquitto permite conexiones anónimas.
- Las credenciales de PostgreSQL son simples.
- No se usa TLS.
- No hay autenticación de dispositivos.
- No hay control de usuarios.
- No hay gestión de secretos avanzada.

Para una versión productiva habría que agregar:

- Autenticación MQTT.
- Usuarios y contraseñas por dispositivo o cliente.
- TLS/SSL.
- Gestión de dispositivos.
- Rotación de credenciales.
- Backups.
- Monitoreo de servicios.
- Políticas de retención de datos.
- Seguridad en red.
- Separación de ambientes: desarrollo, staging y producción.

---

## Posibles próximos pasos

Algunas mejoras futuras:

- Mejorar el simulador para que tenga comportamiento térmico más realista.
- Detectar alertas sostenidas en el tiempo y no solo por lectura individual.
- Crear estado de alertas activas/resueltas.
- Agregar estado online/offline de sensores.
- Agregar una tabla de dispositivos.
- Agregar una tabla de clientes/sucursales.
- Mejorar el dashboard operativo.
- Agregar filtros por rango horario.
- Agregar notificaciones por email, WhatsApp, Telegram u otro canal.
- Incorporar sensores físicos reales.
- Evaluar TimescaleDB para optimizar series temporales.
- Dockerizar también el consumidor, el simulador y la app Streamlit.
- Preparar despliegue en un servidor o cloud.

---

## Estado actual

El proyecto actualmente permite:

- Simular sensores frigoríficos.
- Publicar telemetría por MQTT.
- Consumir mensajes desde Python.
- Detectar alertas básicas.
- Guardar lecturas y alertas en PostgreSQL.
- Visualizar datos en un dashboard Streamlit.
- Consultar la base desde DBeaver.

```text
MVP técnico end-to-end funcionando localmente.
```