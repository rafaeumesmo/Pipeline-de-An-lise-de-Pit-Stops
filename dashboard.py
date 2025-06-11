import streamlit as st
import redis
import json
import time
import pandas as pd

# --- Configurações ---
REDIS_HOST = 'redis'
REDIS_PORT = 6379

st.set_page_config(
    page_title="Dashboard de Pit Stops F1",
    page_icon="🏎️",
    layout="wide"
)

# --- Conexão com Redis ---
@st.cache_resource
def connect_redis():
    try:
        r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
        r.ping()
        st.success("Conectado ao Redis com sucesso!")
        return r
    except Exception as e:
        st.error(f"Não foi possível conectar ao Redis: {e}")
        return None

redis_client = connect_redis()

# --- Layout do Dashboard ---
st.title("🏎️ Dashboard de Pit Stops F1 em Tempo Real")

if redis_client:
    placeholder = st.empty()

    # Inicializa o histórico de dados na session_state do Streamlit
    if 'pitstop_history' not in st.session_state:
        st.session_state.pitstop_history = pd.DataFrame(columns=['driverId', 'duration'])

    while True:
        try:
            # Pega o dado mais recente do Redis
            latest_data_json = redis_client.get('latest_pitstop')
            
            if latest_data_json:
                data = json.loads(latest_data_json)
                
                driver_id = data.get('driverId')
                race_id = data.get('raceId')
                lap = data.get('lap')
                stop_num = data.get('stop')
                duration = float(data.get('duration', 0))
                
                # Adiciona o novo dado ao histórico
                new_data_df = pd.DataFrame([{'driverId': driver_id, 'duration': duration}])
                st.session_state.pitstop_history = pd.concat([st.session_state.pitstop_history, new_data_df], ignore_index=True)
                
                # Limita o histórico aos últimos 30 pontos
                if len(st.session_state.pitstop_history) > 30:
                    st.session_state.pitstop_history = st.session_state.pitstop_history.tail(30)

                with placeholder.container():
                    st.header("Último Pit Stop Registrado")
                    
                    col1, col2, col3, col4 = st.columns(4)
                    col1.metric("Driver ID", driver_id)
                    col2.metric("Race ID", race_id)
                    col3.metric("Lap", lap)
                    col4.metric("Duração", f"{duration:.3f} s")

                    st.header("Histórico de Duração dos Pit Stops (s)")
                    # Prepara dados para o gráfico, usando o índice como eixo X
                    chart_data = st.session_state.pitstop_history[['duration']].reset_index(drop=True)
                    st.line_chart(chart_data)

                    st.write("---")
                    st.subheader("Raw Data (JSON)")
                    st.json(data)
            
            time.sleep(1) # Atualiza a cada 1 segundo

        except Exception as e:
            st.error(f"Erro ao processar dados: {e}")
            time.sleep(5)