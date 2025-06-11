import pandas as pd
from kafka import KafkaProducer
import json
import time
import logging

# Configuração do logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configurações
KAFKA_TOPIC = 'f1_pitstops_raw'
KAFKA_SERVER = 'kafka:29092'
DATA_FILE = 'pit_stops.csv'
DELAY_SECONDS = 1

# Inicializa o producer do Kafka
producer = None
while producer is None:
    try:
        producer = KafkaProducer(
            bootstrap_servers=KAFKA_SERVER,
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )
        logger.info("Conectado ao Kafka com sucesso.")
    except Exception as e:
        logger.error(f"Não foi possível conectar ao Kafka: {e}. Tentando novamente em 5 segundos...")
        time.sleep(5)

# Carrega e processa o dataset
try:
    df = pd.read_csv(DATA_FILE)
    # Selecionamos e renomeamos as colunas de interesse
    df = df[['raceId', 'driverId', 'lap', 'stop', 'duration']].copy()
    
    logger.info("Dataset de Pit Stops carregado e pronto para envio.")

    # Envia os dados em loop
    while True:
        # Pega uma amostra aleatória de 500 pit stops para simular um fluxo contínuo
        sample_df = df.sample(n=500)
        for _, row in sample_df.iterrows():
            message = row.to_dict()
            logger.info(f"Enviando pit stop: {message}")
            producer.send(KAFKA_TOPIC, message)
            producer.flush()
            time.sleep(DELAY_SECONDS)
        logger.info("Ciclo de envio de 500 pit stops concluído. Reiniciando...")

except FileNotFoundError:
    logger.error(f"Erro: O arquivo '{DATA_FILE}' não foi encontrado.")
except Exception as e:
    logger.error(f"Ocorreu um erro: {e}")
    