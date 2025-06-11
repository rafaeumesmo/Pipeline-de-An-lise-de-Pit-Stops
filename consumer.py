import json
import time
import logging
from kafka import KafkaConsumer
import redis
import pika
from minio import Minio
from minio.error import S3Error
import datetime

# Configuração do logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Configurações dos Serviços ---
KAFKA_TOPIC = 'f1_pitstops_raw'
KAFKA_SERVER = 'kafka:29092'

REDIS_HOST = 'redis'
REDIS_PORT = 6379

RABBITMQ_HOST = 'rabbitmq'
RABBITMQ_QUEUE_ALERTS = 'pitstop_alerts'

MINIO_HOST = 'minio:9000'
MINIO_ACCESS_KEY = 'minioadmin'
MINIO_SECRET_KEY = 'minioadmin'
MINIO_BUCKET = 'f1-pitstops'

# --- Funções de Conexão com Retry ---
def connect_kafka():
    while True:
        try:
            consumer = KafkaConsumer(
                KAFKA_TOPIC,
                bootstrap_servers=KAFKA_SERVER,
                auto_offset_reset='earliest',
                value_deserializer=lambda x: json.loads(x.decode('utf-8'))
            )
            logger.info("Conectado ao Kafka com sucesso.")
            return consumer
        except Exception as e:
            logger.error(f"Falha ao conectar no Kafka: {e}. Tentando novamente em 5s.")
            time.sleep(5)

def connect_redis():
    while True:
        try:
            r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0)
            r.ping()
            logger.info("Conectado ao Redis com sucesso.")
            return r
        except Exception as e:
            logger.error(f"Falha ao conectar no Redis: {e}. Tentando novamente em 5s.")
            time.sleep(5)

def connect_rabbitmq():
    while True:
        try:
            connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST))
            channel = connection.channel()
            channel.queue_declare(queue=RABBITMQ_QUEUE_ALERTS)
            logger.info("Conectado ao RabbitMQ com sucesso.")
            return channel, connection
        except Exception as e:
            logger.error(f"Falha ao conectar no RabbitMQ: {e}. Tentando novamente em 5s.")
            time.sleep(5)

def connect_minio():
    while True:
        try:
            client = Minio(
                MINIO_HOST,
                access_key=MINIO_ACCESS_KEY,
                secret_key=MINIO_SECRET_KEY,
                secure=False
            )
            found = client.bucket_exists(MINIO_BUCKET)
            if not found:
                client.make_bucket(MINIO_BUCKET)
                logger.info(f"Bucket '{MINIO_BUCKET}' criado no MinIO.")
            else:
                logger.info(f"Bucket '{MINIO_BUCKET}' já existe no MinIO.")
            return client
        except Exception as e:
            logger.error(f"Falha ao conectar no MinIO: {e}. Tentando novamente em 5s.")
            time.sleep(5)


def main():
    kafka_consumer = connect_kafka()
    redis_client = connect_redis()
    rabbit_channel, rabbit_conn = connect_rabbitmq()
    minio_client = connect_minio()

    logger.info("Iniciando o consumo de mensagens de pit stops...")
    for message in kafka_consumer:
        data = message.value
        logger.info(f"Pit stop recebido: {data}")

        # 1. Armazenar em cache no Redis
        redis_client.set('latest_pitstop', json.dumps(data))

        # 2. Salvar no Data Lake (MinIO)
        try:
            object_name = f"pitstops/{datetime.datetime.now().strftime('%Y%m%d%H%M%S%f')}.json"
            minio_client.put_object(
                MINIO_BUCKET,
                object_name,
                data=json.dumps(data).encode('utf-8'),
                length=-1,
                part_size=10*1024*1024,
                content_type='application/json'
            )
            logger.info(f"Pit stop salvo no MinIO: {object_name}")
        except S3Error as exc:
            logger.error(f"Erro ao salvar no MinIO: {exc}")

        # 3. Verificar e enviar alertas via RabbitMQ
        duration = float(data.get('duration', 0))
        
        # REGRA DE ALERTA: Pit stop maior que 25 segundos
        if duration > 25:
            alert_message = f"ALERTA: Pit stop LONGO detectado! DriverID: {data.get('driverId')}, Duração: {duration}s"
            rabbit_channel.basic_publish(
                exchange='',
                routing_key=RABBITMQ_QUEUE_ALERTS,
                body=alert_message
            )
            logger.warning(f"Alerta enviado: {alert_message}")

    rabbit_conn.close()

if __name__ == "__main__":
    main()