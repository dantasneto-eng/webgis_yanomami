# ⛏️ WebGIS — Terra Indígena Yanomami (Monitoramento de Mineração)

Aplicação **WebGIS interativa em Streamlit** voltada para o monitoramento ambiental da **Terra Indígena Yanomami (RR / AM)**, com foco na expansão da **mineração/garimpo** entre **2004, 2014 e 2024**, cruzada com embargos do IBAMA, alertas do MapBiomas e desmatamento PRODES.

---

## ✨ Funcionalidades

* **🗺️ Mapa Interativo:**
  * Escala temporal interativa (**2004**, **2014** e **2024** — MapBiomas Coleção 11).
  * Modo **Comparação Lado a Lado (`2004 vs 2024`)** sincronizado (`DualMap`).
  * **Legenda interativa em caixas** para ligar/desligar individualmente cada classe de uso e cobertura do solo no mapa (incluindo atalho *Só Mineração — Classe 30*).
  * Botão de **Tela Cheia**, seleção de mapa de fundo (Satélite, CartoDB Claro/Escuro, OpenTopoMap) e popups informativos nos polígonos.
* **📈 Gráficos e Dados:**
  * Comparativo de área minerada em **2004, 2014 e 2024**, opção de visualizar **somente o gráfico de mineração**, cobertura do solo por ano e explorador de dados vetoriais com exportação em CSV.
* **⛏️ Mineração e Garimpo:**
  * Evolução da classe 30 (MapBiomas Col. 11) em **2004, 2014 e 2024**, ranking por município (MapBiomas Alertas), embargos minerais do IBAMA e download em CSV.
* **🚫 Embargos IBAMA:**
  * Filtros por ano (`data_tad`), UF, município e vínculo com mineração/garimpo, KPIs com área e valor total dos autos (`valor_tad`), evolução anual e exportação em CSV.

---

## 📂 Estrutura Principal

```text
Webgis/
├── home.py                  # Aplicação principal Streamlit
├── requirements.txt         # Dependências Python
├── .streamlit/
│   └── config.toml          # Tema padrão (modo escuro)
└── Dados/
    ├── utils.py             # Paleta de cores e classes MapBiomas em português
    ├── zona_utm.py          # Cálculo automático de fuso UTM
    ├── tis_poligonais/      # Limite da TI Yanomami
    ├── mapbiomas_alertas/   # Alertas recortados (yanomami_alertas.parquet)
    ├── embargos/            # Embargos IBAMA
    └── prodes/              # PRODES recortado (yanomami_prodes.parquet)
```

---

## 🚀 Como Executar Localmente

1. Crie e ative um ambiente Python 3.11 (via Conda/Miniconda):
   ```bash
   conda create -n webgis python=3.11 pip -y
   conda activate webgis
   ```
2. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```
3. Execute o aplicativo:
   ```bash
   streamlit run home.py
   ```

---

## ☁️ Deploy (Streamlit Community Cloud)

1. Suba este repositório para o **GitHub**.
2. Acesse [share.streamlit.io](https://share.streamlit.io/), conecte sua conta do GitHub e selecione este repositório.
3. Defina **`home.py`** como *Main file path* e clique em **Deploy**.

---

## 📊 Fontes de Dados

* **MapBiomas Brasil (Coleção 11)** — Cobertura e Uso da Terra (30 m) e **MapBiomas Alertas**
* **IBAMA** — Áreas Embargadas (TAD)
* **INPE / PRODES** — Desmatamento na Amazônia Legal
* **FUNAI** — Limites de Terras Indígenas
