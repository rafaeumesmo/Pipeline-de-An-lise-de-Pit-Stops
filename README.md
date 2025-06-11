# 🏎️ Pipeline de Análise de Pit Stops da F1 em Tempo Real

Este projeto implementa um pipeline completo de ingestão, processamento, armazenamento e visualização de dados em tempo real, utilizando um dataset de pit stops da Fórmula 1.

## Integrante e Participação

* **Rafael Severo**: Responsável pela concepção, desenvolvimento e documentação de todo o pipeline, incluindo a configuração da arquitetura de serviços (Docker, Kafka, Redis, RabbitMQ, MinIO), a codificação dos scripts de ingestão e consumo, e a criação do dashboard de visualização.

## Arquitetura do Pipeline

O pipeline é composto pelos seguintes serviços, todos orquestrados com Docker Compose em uma única rede:

-   **Producer (Python)**: Um script que lê os dados do arquivo `pit_stops.csv` e publica cada evento de pit stop em um tópico do Kafka.
-   **Kafka**: Atua como um *message broker* distribuído, recebendo os dados brutos no tópico `f1_pitstops_raw` e garantindo a entrega para os consumidores.
-   **Consumer (Python)**: O coração do pipeline. Ele consome os dados do Kafka e executa três tarefas simultaneamente:
    1.  **Cache Rápido**: Armazena a informação do último pit stop em um cache no **Redis** para acesso de baixa latência pelo dashboard.
    2.  **Sistema de Alertas**: Envia uma mensagem para uma fila no **RabbitMQ** se um pit stop demorar **mais de 25 segundos**, sinalizando um possível problema.
    3.  **Data Lake**: Salva o registro JSON de todos os pit stops em um bucket no **MinIO**, nosso Data Lake, para armazenamento histórico e análises futuras.
-   **Streamlit**: Um dashboard web interativo que se conecta ao Redis para buscar e exibir os dados do último pit stop e o histórico de durações em tempo real.
-   **MinIO**: Um sistema de armazenamento de objetos compatível com a API S3, utilizado como Data Lake.
-   **Redis**: Um banco de dados em memória, usado para cache e acesso rápido aos dados mais recentes.
-   **RabbitMQ**: Um *message broker* tradicional, usado para gerenciar a fila de alertas críticos.


## Como Executar o Pipeline

**Pré-requisitos:**
* Docker
* Docker Compose

**Passos:**

1.  **Estrutura de Arquivos:**
    Certifique-se de que seu diretório de projeto está organizado da seguinte forma:

    ```
    pipeline_f1/
    ├── docker-compose.yml
    ├── Dockerfile.producer
    ├── Dockerfile.consumer
    ├── Dockerfile.streamlit
    ├── producer.py
    ├── consumer.py
    ├── dashboard.py
    ├── requirements.txt
    └── pit_stops.csv   <-- Coloque o dataset aqui!
    ```

2.  **Construa e Inicie os Contêineres:**
    No diretório raiz do projeto (onde o arquivo `docker-compose.yml` está localizado), execute o seguinte comando no terminal:
    ```bash
    docker-compose up --build -d
    ```
    O comando `--build` garante que as imagens Docker serão construídas a partir dos `Dockerfile`s, e `-d` executa os contêineres em modo "detached" (em segundo plano).

3.  **Acesse os Serviços:**
    Após alguns instantes para que todos os serviços iniciem, você poderá acessar as diferentes partes do pipeline:

    * **Dashboard em Tempo Real (Streamlit)**:
        Acesse `http://localhost:8501` no seu navegador. Você verá os dados dos pit stops sendo atualizados em tempo real.

    * **Console do MinIO (Data Lake)**:
        Acesse `http://localhost:9001`. Use as credenciais `minioadmin` / `minioadmin` para fazer login. Você encontrará o bucket `f1-pitstops` com os arquivos JSON de cada evento sendo criados.

    * **Management UI do RabbitMQ (Alertas)**:
        Acesse `http://localhost:15672`. Use as credenciais `guest` / `guest`. Navegue até a aba "Queues" e observe a fila `pitstop_alerts`. Mensagens de alerta aparecerão aqui sempre que um pit stop demorar mais de 25 segundos.

4.  **Verifique os Logs (Opcional):**
    Para acompanhar o que cada serviço está fazendo em tempo real, você pode verificar os logs de um contêiner específico:
    ```bash
    # Logs do producer enviando os dados
    docker logs -f producer

    # Logs do consumer processando os dados
    docker logs -f consumer
    ```

5.  **Para Parar o Pipeline:**
    Para parar e remover todos os contêineres, redes e volumes criados, execute o seguinte comando no mesmo diretório:
    ```bash
    docker-compose down
    ```
