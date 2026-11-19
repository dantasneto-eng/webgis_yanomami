# ==============================================================================
# IMPORTAÇÃO DAS BIBLIOTECAS NECESSÁRIAS PARA O WEBGIS YANOMAMI (FOCO MINERAÇÃO)
# ==============================================================================

# Biblioteca padrão do Python para lidar com caminhos de arquivos e diretórios
import os
# Biblioteca para criar arquivos temporários ao ler uploads do usuário
import tempfile
# Biblioteca para manipulação de tabelas e dados tabulares (DataFrames)
import pandas as pd
# Biblioteca para criação de gráficos interativos
import plotly.express as px
px.defaults.template = "plotly_white"
# Biblioteca para criação de mapas interativos na web (baseado em Leaflet) e plugins de tela cheia / mapa duplo
import folium
from folium.plugins import DualMap, Fullscreen
# Conector que permite exibir mapas do Folium dentro do Streamlit
from streamlit_folium import st_folium
# Framework principal utilizado para construir a interface web interativa
import streamlit as st
# Biblioteca para leitura e recorte eficiente de arquivos raster (GeoTIFF)
import rasterio
# Ferramentas do Rasterio e Affine para calcular janelas de recorte, máscara vetorial e reamostragem
from rasterio.windows import Window
from rasterio.features import geometry_mask
from rasterio.enums import Resampling
from rasterio.io import MemoryFile
from affine import Affine
# Biblioteca para leitura, manipulação e análise de dados geoespaciais vetoriais
import geopandas as gpd
# Biblioteca para cálculos numéricos e manipulação de matrizes (arrays)
import numpy as np
# Função personalizada do projeto para descobrir o código EPSG da zona UTM ideal em áreas locais
from Dados.zona_utm import calcular_utm
# Biblioteca para recarregar módulos auxiliares (como Dados.utils) quando editados
import importlib
# Dicionários personalizados com as cores RGBA e os nomes das classes do MapBiomas em português
import Dados.utils as dados_utils
importlib.reload(dados_utils)
mapbiomas_colors = dados_utils.color_map
mapbiomas_classes = dados_utils.value_to_class


# ==============================================================================
# CONFIGURAÇÃO INICIAL DA PÁGINA E ESTILOS VISUAIS (CSS)
# ==============================================================================

# Define o título da aba do navegador, ícone, layout em tela cheia (wide) e menu lateral aberto
# Mantém o menu lateral aberto por padrão para exibir os botões de navegação
st.set_page_config(
    page_title="WebGIS Yanomami — Monitoramento de Mineração",
    page_icon="⛏️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Injeta CSS personalizado para visual clean, leve e com foco no mapa e nos gráficos
st.markdown(
    """
    <style>
        .block-container {
            padding-top: 1.8rem;
            padding-bottom: 1rem;
            padding-left: 1.5rem;
            padding-right: 1.5rem;
            max-width: 100%;
        }
        div[data-testid="stMetric"] {
            background-color: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 10px;
            padding: 10px 14px;
        }
        div.stButton > button {
            border-radius: 8px;
            font-weight: 600;
        }
        iframe[title="streamlit_folium.st_folium"] {
            width: 100% !important;
            border-radius: 10px;
            border: 1px solid #e2e8f0;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


# ==============================================================================
# CAMINHOS DAS BASES E PALETA DE CORES (ESA WORLDCOVER 10m + MAPBIOMAS)
# ==============================================================================

# Caminhos relativos das bases ambientais armazenadas na pasta Dados
# Usa as versões leves recortadas para a TI Yanomami (< 1 MB) quando disponíveis, permitindo deploy no GitHub/Streamlit Cloud
EMBARGO = "Dados/embargos/embargos_ibama.parquet"
DESMATAMENTO = (
    "Dados/prodes/yanomami_prodes.parquet"
    if os.path.exists("Dados/prodes/yanomami_prodes.parquet")
    else "Dados/prodes/prodes.parquet"
)
TIS = "Dados/tis_poligonais/tis.parquet"
ALERTAS = (
    "Dados/mapbiomas_alertas/yanomami_alertas.parquet"
    if os.path.exists("Dados/mapbiomas_alertas/yanomami_alertas.parquet")
    else "Dados/mapbiomas_alertas/mapbiomas_alertas.parquet"
)

# Caminhos padrão focados na Terra Indígena Yanomami
YANOMAMI_POLIGONO = "Dados/tis_poligonais/YANOMAMI.geojson"
YANOMAMI_RASTER = "Dados/mapbiomas_brazil-collection_11_0-coverage-yanomami-2024.tif"
MAPBIOMAS_YANOMAMI_ANOS = {
    2004: "Dados/mapbiomas_brazil-collection_11_0-coverage-yanomami-2004.tif",
    2014: "Dados/mapbiomas_brazil-collection_11_0-coverage-yanomami-2014.tif",
    2024: "Dados/mapbiomas_brazil-collection_11_0-coverage-yanomami-2024.tif",
}

# Expressão regular usada para identificar embargos do IBAMA ligados a garimpo/mineração
REGEX_MINERACAO = r"min[eé]r|garimp|aur[ií]fer|ouro|lavra|cassiterita"

# Dicionário de cores RGBA oficiais do ESA WorldCover 10m (para o raster da região Yanomami)
ESA_COLORS = {
    10: (0, 100, 0, 255),       # Cobertura Arbórea (Floresta)
    20: (255, 187, 34, 255),    # Vegetação Arbustiva
    30: (255, 255, 76, 255),    # Vegetação Herbácea / Campestre
    40: (240, 150, 255, 255),   # Agricultura
    50: (250, 0, 0, 255),       # Área Construída / Urbana
    60: (180, 180, 180, 255),   # Solo Exposto / Vegetação Esparsa
    70: (240, 240, 240, 255),   # Neve e Gelo
    80: (0, 100, 200, 255),     # Corpos d'Água Permanentes
    90: (0, 150, 160, 255),     # Área Úmida Herbácea
    95: (0, 207, 117, 255),     # Manguezal
    100: (250, 230, 160, 255),  # Musgo e Líquen
}

# Dicionário com os nomes em português das classes do ESA WorldCover 10m
ESA_CLASSES = {
    10: "Cobertura Arbórea (Floresta)",
    20: "Vegetação Arbustiva",
    30: "Vegetação Herbácea / Campestre",
    40: "Agricultura",
    50: "Área Construída",
    60: "Solo Exposto / Vegetação Esparsa",
    70: "Neve e Gelo",
    80: "Corpos d'Água Permanentes",
    90: "Área Úmida Herbácea",
    95: "Manguezal",
    100: "Musgo e Líquen",
}


# ==============================================================================
# INICIALIZAÇÃO DO ESTADO DA SESSÃO (SESSION STATE)
# ==============================================================================

# Define a página inicial como "Mapa" para abrir direto no Mapa Interativo da TI Yanomami
if "pagina_atual" not in st.session_state:
    st.session_state.pagina_atual = "Mapa"

# Mantém o foco na Terra Indígena Yanomami ativado por padrão ao abrir o site
if "modo_yanomami" not in st.session_state:
    st.session_state.modo_yanomami = True

# Contador usado pelo botão "Centralizar Mapa" para resetar o enquadramento do mapa
if "mapa_reset_id" not in st.session_state:
    st.session_state.mapa_reset_id = 0

# Ano ativo na escala temporal do mapa (padrão 2024 - MapBiomas Col. 11)
if "ano_escala_temporal" not in st.session_state:
    st.session_state.ano_escala_temporal = 2024


def obter_ano_raster_correspondente(ano: int) -> int:
    """Mapeia qualquer ano da escala temporal para o GeoTIFF MapBiomas Col. 11 mais próximo (2004, 2014 ou 2024)."""
    if ano <= 2009:
        return 2004
    if ano <= 2019:
        return 2014
    return 2024


# Função auxiliar para trocar a página ativa quando qualquer botão de navegação for clicado
def ir_para(pagina: str):
    """Atualiza a página ativa no estado da sessão do Streamlit."""
    st.session_state.pagina_atual = pagina


# ==============================================================================
# FUNÇÕES DE LEITURA E PROCESSAMENTO COM CACHE
# ==============================================================================

# Mantém a base de embargos do IBAMA em cache na memória para não reler do disco
@st.cache_resource
def abrir_embargo():
    """Carrega o arquivo Parquet de embargos do IBAMA."""
    return gpd.read_parquet(EMBARGO)


# Mantém a base de desmatamento do PRODES em cache na memória
@st.cache_resource
def abrir_desmatamento():
    """Carrega o arquivo Parquet de desmatamento (PRODES)."""
    return gpd.read_parquet(DESMATAMENTO)


# Mantém a base de Terras Indígenas da FUNAI em cache na memória
@st.cache_resource
def abrir_tis():
    """Carrega o arquivo Parquet de Terras Indígenas (FUNAI)."""
    return gpd.read_parquet(TIS)


# Mantém a base de alertas do MapBiomas em cache na memória (contém o vetor VPRESSAO de mineração)
@st.cache_resource
def abrir_mapbiomas_alertas():
    """Carrega o arquivo Parquet de alertas do MapBiomas."""
    return gpd.read_parquet(ALERTAS)


# Lê um polígono a partir de bytes enviados pelo usuário (ou arquivo local)
def ler_poligono_bytes(file_bytes: bytes, file_name: str) -> gpd.GeoDataFrame:
    """Lê um arquivo vetorial preservando a extensão original e garantindo CRS definido."""
    ext = os.path.splitext(file_name)[1].lower()
    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name
    try:
        if ext == ".parquet":
            gdf = gpd.read_parquet(tmp_path)
        else:
            gdf = gpd.read_file(tmp_path)
        # Se o arquivo não tiver CRS definido, assume SIRGAS 2000 (EPSG:4674)
        if gdf.crs is None:
            gdf = gdf.set_crs(epsg=4674)
        return gdf
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


# Escolhe a projeção métrica adequada: Policônica do Brasil (EPSG:5880) para áreas extensas ou UTM local
def escolher_epsg_metrico(gdf_4674: gpd.GeoDataFrame) -> int:
    """Usa EPSG:5880 quando o polígono abrange múltiplos fusos UTM (> 5 graus), senão usa UTM local."""
    minx, _, maxx, _ = gdf_4674.total_bounds
    if (maxx - minx) > 5.0:
        return 5880
    return calcular_utm(gdf_4674)


# Função auxiliar para calcular a área total em hectares de um GeoDataFrame sem contar sobreposições duas vezes
def calcular_area_ha(gdf: gpd.GeoDataFrame, epsg_metrico: int) -> float:
    """Dissolve as geometrias e calcula a área total em hectares na projeção métrica."""
    if len(gdf) == 0:
        return 0.0
    dissolvido = gdf.dissolve(by=None).to_crs(epsg=epsg_metrico)
    return float((dissolvido.area / 10000).sum())


# Função auxiliar para cruzar uma camada ambiental com o polígono de interesse e calcular a área em hectares
def cruzar_camada(camada_base: gpd.GeoDataFrame, poligono_ref: gpd.GeoDataFrame, epsg_metrico: int):
    """Executa filtro espacial (sjoin), recorte exato (overlay) e calcula área total em hectares."""
    # Garante que o polígono esteja no mesmo CRS da camada ambiental
    poligono_alinhado = poligono_ref.to_crs(camada_base.crs) if poligono_ref.crs != camada_base.crs else poligono_ref
    # Filtra rapidamente os polígonos que intersectam a área analisada usando o índice espacial
    filtrada = gpd.sjoin(camada_base, poligono_alinhado[["geometry"]], how="inner", predicate="intersects")
    if len(filtrada) == 0:
        return filtrada, 0.0
    # Remove a coluna auxiliar index_right antes do overlay
    filtrada = filtrada.drop(columns=["index_right"], errors="ignore")
    # Recorta exatamente os polígonos que caem dentro do limite analisado
    recorte = gpd.overlay(filtrada, poligono_alinhado[["geometry"]], how="intersection")
    if len(recorte) == 0:
        return recorte, 0.0
    # Calcula a área real em hectares
    area_ha = calcular_area_ha(recorte, epsg_metrico)
    return recorte, area_ha


# Executa toda a análise vetorial (cruzamento com IBAMA, PRODES, TIs e MapBiomas Alertas/Mineração)
def processar_analise_vetorial(poligono_bytes: bytes, poligono_nome: str):
    """Lê o polígono, define a projeção métrica e realiza os cruzamentos ambientais e de mineração."""
    poligono_analise = ler_poligono_bytes(poligono_bytes, poligono_nome)
    poligono_4674 = poligono_analise.to_crs(epsg=4674)
    epsg_metrico = escolher_epsg_metrico(poligono_4674)
    # Calcula a área total do polígono analisado em hectares
    area_total_ha = float((poligono_4674.to_crs(epsg=epsg_metrico).area / 10000).sum())

    # Carrega as bases ambientais em cache
    gdf_embargo = abrir_embargo()
    gdf_desmat = abrir_desmatamento()
    gdf_ti = abrir_tis()
    gdf_alertas = abrir_mapbiomas_alertas()

    # Remove apenas colunas pessoais sensíveis da tabela de embargos (mantém data_tad para análise temporal)
    colunas_remover = [
        "nom_pessoa", "cpf_cnpj_i", "cpf_cnpj_s", "end_pessoa",
        "des_bairro", "num_cep", "num_fone",
        "dat_altera", "data_cadas", "data_geom", "dt_carga",
    ]
    gdf_embargo_limpo = gdf_embargo.drop(columns=colunas_remover, errors="ignore")

    # Executa os cruzamentos espaciais principais
    entrada_embargo, area_embargo_ha = cruzar_camada(gdf_embargo_limpo, poligono_4674, epsg_metrico)
    entrada_desmat, area_desmat_ha = cruzar_camada(gdf_desmat, poligono_4674, epsg_metrico)
    entrada_ti, area_ti_ha = cruzar_camada(gdf_ti, poligono_4674, epsg_metrico)
    entrada_alertas, area_alertas_ha = cruzar_camada(gdf_alertas, poligono_4674, epsg_metrico)

    # Filtra os alertas do MapBiomas cujo vetor de pressão (VPRESSAO) seja mineração ou garimpo ilegal
    if len(entrada_alertas) > 0 and "VPRESSAO" in entrada_alertas.columns:
        mask_min = entrada_alertas["VPRESSAO"].isin(["ilegal_mining", "mining"])
        alertas_mineracao = entrada_alertas[mask_min].copy()
        # Converte o ano de detecção para número inteiro para facilitar os filtros na interface
        if "ANODETEC" in alertas_mineracao.columns:
            alertas_mineracao["ANODETEC"] = pd.to_numeric(alertas_mineracao["ANODETEC"], errors="coerce").fillna(0).astype(int)
        area_mineracao_ha = calcular_area_ha(alertas_mineracao, epsg_metrico)
    else:
        alertas_mineracao = entrada_alertas.iloc[0:0].copy()
        area_mineracao_ha = 0.0

    # Filtra os embargos do IBAMA cuja descrição cita mineração, garimpo ou extração de minério aurífero
    if len(entrada_embargo) > 0:
        texto_desc = entrada_embargo.get("des_tad", pd.Series("", index=entrada_embargo.index)).fillna("").astype(str)
        texto_infr = entrada_embargo.get("des_infrac", pd.Series("", index=entrada_embargo.index)).fillna("").astype(str)
        mask_emb_min = texto_desc.str.contains(REGEX_MINERACAO, case=False, regex=True) | texto_infr.str.contains(REGEX_MINERACAO, case=False, regex=True)
        embargos_mineracao = entrada_embargo[mask_emb_min].copy()
        area_embargo_mineracao_ha = calcular_area_ha(embargos_mineracao, epsg_metrico)
    else:
        embargos_mineracao = entrada_embargo.iloc[0:0].copy()
        area_embargo_mineracao_ha = 0.0

    return {
        "poligono": poligono_4674,
        "epsg": epsg_metrico,
        "area_total_ha": area_total_ha,
        "entrada_embargo": entrada_embargo,
        "area_embargo_ha": area_embargo_ha,
        "embargos_mineracao": embargos_mineracao,
        "area_embargo_mineracao_ha": area_embargo_mineracao_ha,
        "entrada_desmat": entrada_desmat,
        "area_desmat_ha": area_desmat_ha,
        "entrada_ti": entrada_ti,
        "area_ti_ha": area_ti_ha,
        "entrada_alertas": entrada_alertas,
        "area_alertas_ha": area_alertas_ha,
        "alertas_mineracao": alertas_mineracao,
        "area_mineracao_ha": area_mineracao_ha,
    }


# Lê e processa o raster em resolução otimizada (suporta rasters gigantes como ESA WorldCover 36000x36000 sem travar RAM)
def processar_raster_otimizado(raster_fonte, poligono_bytes: bytes, poligono_nome: str):
    """Recorta a janela do raster sobre o polígono, gera imagem RGBA leve e calcula áreas por classe."""
    poligono = ler_poligono_bytes(poligono_bytes, poligono_nome).copy()

    # Define como abrir o raster: direto do caminho em disco (rápido) ou de bytes em memória (upload)
    def abrir_src():
        if isinstance(raster_fonte, str):
            return rasterio.open(raster_fonte)
        return MemoryFile(raster_fonte).open()

    with abrir_src() as src:
        # Alinha o polígono ao CRS do raster
        if poligono.crs != src.crs:
            poligono = poligono.to_crs(src.crs)

        # Calcula a interseção entre os limites do polígono e os limites do raster
        p_minx, p_miny, p_maxx, p_maxy = poligono.total_bounds
        r_left, r_bottom, r_right, r_top = src.bounds
        inter_minx = max(p_minx, r_left)
        inter_miny = max(p_miny, r_bottom)
        inter_maxx = min(p_maxx, r_right)
        inter_maxy = min(p_maxy, r_top)

        # Se não houver sobreposição geográfica entre polígono e raster, lança erro tratado na interface
        if inter_minx >= inter_maxx or inter_miny >= inter_maxy:
            raise ValueError("Polígono e raster não se sobrepõem.")

        # Calcula a janela de leitura em pixels diretamente pela matriz afim (evita falhas nativas do GDAL)
        t = src.transform
        col_start = max(0, min(src.width, int(np.floor((inter_minx - t.c) / t.a))))
        col_stop = max(0, min(src.width, int(np.ceil((inter_maxx - t.c) / t.a))))
        row_start = max(0, min(src.height, int(np.floor((inter_maxy - t.f) / t.e))))
        row_stop = max(0, min(src.height, int(np.ceil((inter_miny - t.f) / t.e))))
        win_w = max(1, col_stop - col_start)
        win_h = max(1, row_stop - row_start)
        window = Window(col_start, row_start, win_w, win_h)

        # Limita a leitura máxima a 2000 pixels no maior lado para manter boa nitidez das classes sem estourar RAM
        max_dim = max(win_h, win_w)
        if max_dim > 2000:
            fator_escala = max_dim / 2000.0
            out_h = max(1, int(round(win_h / fator_escala)))
            out_w = max(1, int(round(win_w / fator_escala)))
        else:
            out_h, out_w = win_h, win_w

        # Lê apenas a banda 1 já reamostrada para o tamanho seguro usando vizinho mais próximo
        out_image = src.read(
            1,
            window=window,
            out_shape=(out_h, out_w),
            resampling=Resampling.nearest,
        )
        # Calcula as coordenadas exatas dos cantos da janela lida e a nova transformação afim
        win_min_x, win_max_y = t * (col_start, row_start)
        win_max_x, win_min_y = t * (col_stop, row_stop)
        out_transform = Affine.translation(win_min_x, win_max_y) * Affine.scale(
            (win_max_x - win_min_x) / out_w,
            (win_min_y - win_max_y) / out_h,
        )

        # Cria máscara booleana (True = fora do polígono) para zerar pixels externos ao limite da TI
        fora_poligono = geometry_mask(
            poligono.geometry,
            out_shape=(out_h, out_w),
            transform=out_transform,
            invert=False,
        )
        nodata_val = int(src.nodata) if src.nodata is not None else 0
        out_image[fora_poligono] = nodata_val

        # Calcula os limites reais e o centroide da imagem recortada para o Folium
        min_x, max_y = out_transform * (0, 0)
        max_x, min_y = out_transform * (out_w, out_h)
        bounds = [[min_y, min_x], [max_y, max_x]]
        centroid_x, centroid_y = (min_x + max_x) / 2, (min_y + max_y) / 2

        # Detecta automaticamente se o raster é ESA WorldCover (códigos múltiplos de 10) ou MapBiomas
        valores_unicos, contagens = np.unique(out_image, return_counts=True)
        valores_validos = [int(v) for v in valores_unicos if v != nodata_val and v != 0]
        eh_esa = len(valores_validos) > 0 and all(v in ESA_CLASSES for v in valores_validos)

        paleta_cores = ESA_COLORS if eh_esa else mapbiomas_colors
        dicionario_classes = ESA_CLASSES if eh_esa else mapbiomas_classes
        fonte_raster = "ESA WorldCover 10m" if eh_esa else "MapBiomas"

        # Estima o tamanho real do pixel original em metros (10m para ESA ou ~30m para MapBiomas)
        pixel_m2_base = 100.0 if eh_esa else 900.0
        # Multiplica pela área representada por cada pixel reamostrado
        area_por_pixel_ha = (pixel_m2_base * (win_w / out_w) * (win_h / out_h)) / 10000.0

        # Monta a matriz RGBA transparente para exibir sobre o mapa
        rgb_image = np.zeros((out_h, out_w, 4), dtype=np.uint8)
        for valor, cor in paleta_cores.items():
            rgb_image[out_image == valor] = cor

        # Monta a tabela de áreas por classe de cobertura do solo
        linhas_uso = []
        for valor, contagem in zip(valores_unicos, contagens):
            if valor == nodata_val or valor == 0:
                continue
            nome_classe = dicionario_classes.get(int(valor), f"Classe {int(valor)}")
            area_ha = int(contagem) * area_por_pixel_ha
            rgba = paleta_cores.get(int(valor), (120, 120, 120, 255))
            cor_hex = f"#{rgba[0]:02x}{rgba[1]:02x}{rgba[2]:02x}"
            linhas_uso.append({
                "Código": int(valor),
                "Classe": nome_classe,
                "Área (ha)": round(area_ha, 2),
                "Cor": cor_hex,
            })

        df_uso = pd.DataFrame(linhas_uso)
        if len(df_uso) > 0:
            df_uso = df_uso.sort_values(by="Área (ha)", ascending=False).reset_index(drop=True)
            total_uso = df_uso["Área (ha)"].sum()
            df_uso["Percentual (%)"] = ((df_uso["Área (ha)"] / total_uso) * 100).round(2) if total_uso > 0 else 0.0

        return {
            "resized_image": rgb_image,
            "out_image": out_image,
            "paleta_cores": paleta_cores,
            "bounds": bounds,
            "centroid": (centroid_x, centroid_y),
            "df_uso": df_uso,
            "fonte_raster": fonte_raster,
        }


# ==============================================================================
# MENU LATERAL (SIDEBAR): FOCO YANOMAMI, NAVEGAÇÃO E UPLOAD OPCIONAL
# ==============================================================================

# Título e navegação limpa do menu lateral (2 funções principais)
st.sidebar.markdown("### 🛰️ WebGIS Yanomami")
st.sidebar.caption("Monitoramento Ambiental • TCC")

st.sidebar.divider()

paginas = [
    ("Mapa", "🗺️ Mapa Interativo"),
    ("Gráficos e Dados", "📊 Dados e Gráficos"),
]

if st.session_state.pagina_atual not in ("Mapa", "Gráficos e Dados"):
    st.session_state.pagina_atual = "Mapa"

for chave_pagina, rotulo_pagina in paginas:
    tipo_botao = "primary" if st.session_state.pagina_atual == chave_pagina else "secondary"
    if st.sidebar.button(rotulo_pagina, key=f"side_{chave_pagina}", type=tipo_botao, use_container_width=True):
        ir_para(chave_pagina)
        st.rerun()

st.sidebar.divider()

# Seção expansível opcional caso o usuário queira subir outro polígono e raster manualmente
with st.sidebar.expander("📂 Analisar outra área (Opcional)", expanded=False):
    poligono_subido = st.file_uploader(
        label="Outro polígono (.geojson, .parquet, .gpkg, .zip)",
        type=["geojson", "json", "parquet", "gpkg", "zip"],
    )
    raster_subido = st.file_uploader(
        label="Outro raster (.tif / .tiff)",
        type=["tif", "tiff"],
    )


# ==============================================================================
# RESOLUÇÃO DA ÁREA ATIVA (TI YANOMAMI POR PADRÃO OU UPLOAD MANUAL)
# ==============================================================================

# Se o usuário enviou ambos os arquivos manualmente, usa os arquivos enviados; senão usa a TI Yanomami
if poligono_subido is not None and raster_subido is not None:
    st.session_state.modo_yanomami = False
    poligono_bytes = poligono_subido.getvalue()
    poligono_nome = poligono_subido.name
    raster_fonte = raster_subido.getvalue()
    raster_nome = raster_subido.name
    raster_tamanho = len(raster_fonte)
    titulo_area = f"Área Personalizada ({poligono_nome})"
    st.sidebar.success(f"Área personalizada ativa:\n- {poligono_nome}\n- {raster_nome}")
else:
    with open(YANOMAMI_POLIGONO, "rb") as f_pol:
        poligono_bytes = f_pol.read()
    poligono_nome = os.path.basename(YANOMAMI_POLIGONO)

    # Mapeia os rasters da TI Yanomami (priorizando MapBiomas Col. 11: 2004, 2014, 2024)
    rasters_disponiveis = {}
    for ano_mb, caminho_mb in MAPBIOMAS_YANOMAMI_ANOS.items():
        if os.path.exists(caminho_mb):
            rasters_disponiveis[f"MapBiomas Col. 11 — {ano_mb}"] = caminho_mb
    if os.path.isdir("Dados"):
        for arq in sorted(os.listdir("Dados")):
            nome_low = arq.lower()
            caminho_arq = os.path.join("Dados", arq)
            if nome_low.endswith((".tif", ".tiff")) and caminho_arq.replace("\\", "/") not in MAPBIOMAS_YANOMAMI_ANOS.values():
                if "yanomami" in nome_low or "esa_worldcover" in nome_low:
                    rasters_disponiveis[arq] = caminho_arq

    nomes_rasters = list(rasters_disponiveis.keys())
    ano_raster_alvo = obter_ano_raster_correspondente(st.session_state.ano_escala_temporal)
    rotulo_padrao = f"MapBiomas Col. 11 — {ano_raster_alvo}"
    idx_padrao = nomes_rasters.index(rotulo_padrao) if rotulo_padrao in nomes_rasters else 0

    raster_escolhido = st.sidebar.selectbox(
        "📅 Raster / Ano (TI Yanomami):",
        options=nomes_rasters,
        index=idx_padrao,
    )
    raster_fonte = rasters_disponiveis[raster_escolhido]
    raster_nome = raster_escolhido
    raster_tamanho = os.path.getsize(raster_fonte)
    titulo_area = "Terra Indígena Yanomami (RR / AM)"

with st.sidebar.expander("📚 Metodologia e Fontes", expanded=False):
    st.markdown(
        """
        - **Cobertura do Solo:** MapBiomas Coleção 11 (30 m) — 2004, 2014 e 2024
        - **Alertas:** MapBiomas Alertas
        - **Embargos:** IBAMA
        - **Desmatamento:** PRODES / INPE
        - **SRC:** SIRGAS 2000 (cálculos métricos em projeção UTM local)
        """
    )


# ==============================================================================
# CABEÇALHO COMPACTO
# ==============================================================================

st.markdown(f"### WebGIS — {titulo_area}")
st.caption("MapBiomas Col. 11 (2004–2024) • Alertas de Mineração • Embargos IBAMA • PRODES")


# ==============================================================================
# EXECUÇÃO DOS PROCESSAMENTOS ESPACIAIS (COM CACHE LEVE NO SESSION_STATE)
# ==============================================================================

# Cria chaves leves (incluindo versão do dicionário em português) para atualizar o cache automaticamente
chave_vetorial = (poligono_nome, len(poligono_bytes))
chave_raster = (poligono_nome, len(poligono_bytes), raster_nome, raster_tamanho, "pt_v2")

# Só executa o cruzamento vetorial quando o polígono muda
if st.session_state.get("cache_vetorial_key") != chave_vetorial:
    with st.spinner("Cruzando área com MapBiomas Alertas (Mineração), IBAMA e PRODES..."):
        st.session_state.cache_vetorial_res = processar_analise_vetorial(poligono_bytes, poligono_nome)
        st.session_state.cache_vetorial_key = chave_vetorial

res_vetorial = st.session_state.cache_vetorial_res

# Só processa o raster quando o polígono ou o raster mudam
if st.session_state.get("cache_raster_key") != chave_raster:
    try:
        with st.spinner("Processando cobertura do solo (ESA WorldCover / MapBiomas)..."):
            st.session_state.cache_raster_res = processar_raster_otimizado(raster_fonte, poligono_bytes, poligono_nome)
            st.session_state.cache_raster_key = chave_raster
    except ValueError:
        st.error("❌ O polígono selecionado não se sobrepõe ao raster informado.")
        st.stop()

res_raster = st.session_state.cache_raster_res

# Extrai as variáveis processadas para uso nas páginas abaixo
poligono_analise = res_vetorial["poligono"]
epsg_metrico = res_vetorial["epsg"]
area_total_ha = res_vetorial["area_total_ha"]
entrada_embargo = res_vetorial["entrada_embargo"]
area_embargo_ha = res_vetorial["area_embargo_ha"]
embargos_mineracao = res_vetorial["embargos_mineracao"]
area_embargo_mineracao_ha = res_vetorial["area_embargo_mineracao_ha"]
entrada_desmat = res_vetorial["entrada_desmat"]
area_desmat_ha = res_vetorial["area_desmat_ha"]
entrada_ti = res_vetorial["entrada_ti"]
entrada_alertas = res_vetorial["entrada_alertas"]
alertas_mineracao = res_vetorial["alertas_mineracao"]
area_mineracao_ha = res_vetorial["area_mineracao_ha"]


# ==============================================================================
# PÁGINA 1: PAINEL EXCLUSIVO DE MINERAÇÃO E GARIMPO
# ==============================================================================

@st.cache_data
def calcular_evolucao_mineracao_col11() -> pd.DataFrame:
    """Calcula a área exata da classe 30 (Mineração) nos rasters MapBiomas Col. 11 (2004, 2014 e 2024)."""
    linhas = []
    for ano, caminho in sorted(MAPBIOMAS_YANOMAMI_ANOS.items()):
        if not os.path.exists(caminho):
            continue
        with rasterio.open(caminho) as src:
            arr = src.read(1)
            px_min = int(np.count_nonzero(arr == 30))
            area_ha = round(px_min * 0.09, 2)  # pixel 30m x 30m = 900 m² = 0,09 ha
            linhas.append({"Ano": str(ano), "AnoNum": ano, "Pixels": px_min, "Area_ha": area_ha})
    return pd.DataFrame(linhas)


@st.cache_data
def calcular_evolucao_desmatamento_col11() -> pd.DataFrame:
    """Calcula a área antrópica acumulada (desmatamento) e cobertura florestal no MapBiomas Col. 11 (2004, 2014 e 2024)."""
    classes_antropicas = (15, 21, 25, 30, 31, 41)
    linhas = []
    for ano, caminho in sorted(MAPBIOMAS_YANOMAMI_ANOS.items()):
        if not os.path.exists(caminho):
            continue
        with rasterio.open(caminho) as src:
            arr = src.read(1)
            px_floresta = int(np.count_nonzero(np.isin(arr, (3, 6))))
            px_antropico = int(np.count_nonzero(np.isin(arr, classes_antropicas)))
            px_min = int(np.count_nonzero(arr == 30))
            area_floresta = round(px_floresta * 0.09, 2)
            area_antropico = round(px_antropico * 0.09, 2)
            area_min = round(px_min * 0.09, 2)
            linhas.append({
                "Ano": str(ano),
                "AnoNum": ano,
                "Floresta_ha": area_floresta,
                "Antropico_ha": area_antropico,
                "Mineracao_ha": area_min,
                "Outros_Antropicos_ha": round(area_antropico - area_min, 2),
            })
    return pd.DataFrame(linhas)


def renderizar_painel_mineracao():
    df_col11_min = calcular_evolucao_mineracao_col11()
    anos_disponiveis = [2004, 2014, 2024]

    # Filtros focados exclusivamente nos anos 2004, 2014 e 2024
    f1, f2 = st.columns(2)
    with f1:
        anos_sel = st.multiselect(
            "Filtrar anos (MapBiomas Col. 11):",
            options=anos_disponiveis,
            default=anos_disponiveis,
        )
    with f2:
        tipos_disponiveis = sorted(alertas_mineracao["VPRESSAO"].dropna().unique().tolist()) if len(alertas_mineracao) > 0 and "VPRESSAO" in alertas_mineracao.columns else []
        tipos_sel = st.multiselect(
            "Filtrar por vetor de pressão (Alertas):",
            options=tipos_disponiveis,
            default=tipos_disponiveis,
        )

    # Filtra a série Col. 11 para os anos selecionados
    df_col11_filt = df_col11_min[df_col11_min["AnoNum"].isin(anos_sel)].copy() if len(df_col11_min) > 0 else pd.DataFrame()

    # Filtra alertas de mineração apenas para os anos selecionados (ex.: 2024) e vetor de pressão
    df_min_filtrado = alertas_mineracao.copy()
    if len(anos_sel) > 0 and "ANODETEC" in df_min_filtrado.columns:
        df_min_filtrado = df_min_filtrado[df_min_filtrado["ANODETEC"].isin(anos_sel)]
    if len(tipos_sel) > 0 and "VPRESSAO" in df_min_filtrado.columns:
        df_min_filtrado = df_min_filtrado[df_min_filtrado["VPRESSAO"].isin(tipos_sel)]

    # Exibe 4 KPIs mostrando exatamente 2004, 2014, 2024 e Embargos IBAMA
    areas_por_ano = {int(r["AnoNum"]): float(r["Area_ha"]) for _, r in df_col11_min.iterrows()} if len(df_col11_min) > 0 else {}
    a2004 = areas_por_ano.get(2004, 0.0)
    a2014 = areas_por_ano.get(2014, 0.0)
    a2024 = areas_por_ano.get(2024, 0.0)
    crescimento = ((a2024 - a2004) / a2004 * 100) if a2004 > 0 else 0.0

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("⛏️ Mineração 2004 (Col. 11)", f"{a2004:,.2f} ha", "MapBiomas Classe 30")
    m2.metric("⛏️ Mineração 2014 (Col. 11)", f"{a2014:,.2f} ha", "MapBiomas Classe 30")
    m3.metric("⛏️ Mineração 2024 (Col. 11)", f"{a2024:,.2f} ha", f"+{crescimento:,.1f}% desde 2004")
    m4.metric("🚫 Embargos Minerais (IBAMA)", f"{len(embargos_mineracao)}", f"{area_embargo_mineracao_ha:,.2f} ha embargados")

    st.write("")
    g_min1, g_min2 = st.columns(2)

    with g_min1:
        if len(df_col11_filt) > 0:
            fig_ano = px.bar(
                df_col11_filt,
                x="Ano",
                y="Area_ha",
                text_auto=".1f",
                title="Evolução da Mineração — MapBiomas Col. 11 (2004, 2014 e 2024)",
                labels={"Ano": "Ano", "Area_ha": "Área de Mineração (ha)"},
                color_discrete_sequence=["#8e44ad"],
            )
            fig_ano.update_layout(height=380)
            st.plotly_chart(fig_ano, use_container_width=True)

    with g_min2:
        if len(df_min_filtrado) > 0 and "MUNICIPIO" in df_min_filtrado.columns:
            df_mun = (
                df_min_filtrado.groupby("MUNICIPIO", as_index=False)
                .agg(Alertas=("CODEALERTA", "count"), Area_ha=("AREAHA", "sum"))
                .sort_values("Area_ha", ascending=True)
                .tail(10)
            )
            fig_mun = px.bar(
                df_mun,
                x="Area_ha",
                y="MUNICIPIO",
                orientation="h",
                text_auto=".1f",
                title="Top Municípios por Área de Garimpo/Mineração (ha)",
                labels={"MUNICIPIO": "Município", "Area_ha": "Área (ha)"},
                color_discrete_sequence=["#c0392b"],
            )
            fig_mun.update_layout(height=380)
            st.plotly_chart(fig_mun, use_container_width=True)
        else:
            st.info("Selecione o ano **2024** para visualizar o ranking municipal dos alertas de mineração.")

    # Tabelas detalhadas com botão de download em CSV
    tab_m1, tab_m2 = st.tabs([
        f"⛏️ Alertas de Mineração ({len(df_min_filtrado)})",
        f"🚫 Embargos de Mineração IBAMA ({len(embargos_mineracao)})",
    ])

    with tab_m1:
        df_min_tab = pd.DataFrame(df_min_filtrado.drop(columns=["geometry"], errors="ignore"))
        st.dataframe(df_min_tab, use_container_width=True, hide_index=True)
        csv_min = df_min_tab.to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            label="⬇️ Baixar Alertas de Mineração (CSV)",
            data=csv_min,
            file_name="alertas_mineracao_yanomami.csv",
            mime="text/csv",
        )

    with tab_m2:
        df_emb_min_tab = pd.DataFrame(embargos_mineracao.drop(columns=["geometry"], errors="ignore"))
        st.dataframe(df_emb_min_tab, use_container_width=True, hide_index=True)
        csv_emb_min = df_emb_min_tab.to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            label="⬇️ Baixar Embargos de Mineração IBAMA (CSV)",
            data=csv_emb_min,
            file_name="embargos_mineracao_yanomami.csv",
            mime="text/csv",
        )


# ==============================================================================
# PÁGINA 4: PAINEL EXCLUSIVO DE EMBARGOS AMBIENTAIS (IBAMA)
# ==============================================================================

def renderizar_painel_embargos():
    # Verifica se existem embargos sobrepostos à área analisada
    if len(entrada_embargo) == 0:
        st.info("Não foram encontrados embargos do IBAMA nesta área.")
    else:
        # Prepara uma cópia tabular sem geometria e converte colunas numéricas de área, valor e ano
        df_emb = pd.DataFrame(entrada_embargo.drop(columns=["geometry"], errors="ignore")).copy()
        df_emb["qtd_area_e_num"] = pd.to_numeric(df_emb.get("qtd_area_e", 0), errors="coerce").fillna(0.0)
        df_emb["valor_tad_num"] = pd.to_numeric(df_emb.get("valor_tad", 0), errors="coerce").fillna(0.0)
        if "data_tad" in df_emb.columns:
            # Extrai o ano da data do termo de embargo (suporta formatos ISO ou DD/MM/AAAA)
            anos_dt = pd.to_datetime(df_emb["data_tad"], errors="coerce").dt.year
            anos_regex = pd.to_numeric(df_emb["data_tad"].astype(str).str.extract(r"((?:19|20)\d{2})")[0], errors="coerce")
            df_emb["ano_embargo"] = anos_dt.fillna(anos_regex).fillna(0).astype(int)
        else:
            df_emb["ano_embargo"] = 0

        # Cria filtros interativos por Ano, UF, Município e vínculo com mineração/garimpo
        fe0, fe1, fe2, fe3 = st.columns([1.2, 0.9, 1.2, 1.2])
        anos_emb_disp = sorted([int(a) for a in df_emb["ano_embargo"].unique() if a > 0])
        with fe0:
            anos_emb_sel = st.multiselect("Filtrar por Ano:", options=anos_emb_disp, default=anos_emb_disp)

        ufs_disp = sorted(df_emb["sig_uf"].dropna().astype(str).unique().tolist()) if "sig_uf" in df_emb.columns else []
        with fe1:
            ufs_sel = st.multiselect("Filtrar por UF:", options=ufs_disp, default=ufs_disp)

        # Atualiza a lista de municípios conforme os anos e UFs selecionados
        df_por_uf = df_emb.copy()
        if len(anos_emb_sel) > 0:
            df_por_uf = df_por_uf[df_por_uf["ano_embargo"].isin(anos_emb_sel)]
        if len(ufs_sel) > 0 and "sig_uf" in df_por_uf.columns:
            df_por_uf = df_por_uf[df_por_uf["sig_uf"].astype(str).isin(ufs_sel)]

        muns_disp = sorted(df_por_uf["nom_munici"].dropna().astype(str).unique().tolist()) if "nom_munici" in df_por_uf.columns else []
        with fe2:
            muns_sel = st.multiselect("Filtrar por Município:", options=muns_disp, default=muns_disp)

        with fe3:
            filtro_motivo = st.radio(
                "Motivo do embargo:",
                options=["Todos os Embargos", "Apenas Mineração / Garimpo"],
                horizontal=True,
            )

        # Aplica os filtros selecionados ao DataFrame de embargos
        df_emb_filt = df_por_uf.copy()
        if len(muns_sel) > 0 and "nom_munici" in df_emb_filt.columns:
            df_emb_filt = df_emb_filt[df_emb_filt["nom_munici"].astype(str).isin(muns_sel)]
        if filtro_motivo == "Apenas Mineração / Garimpo":
            txt_tad = df_emb_filt.get("des_tad", pd.Series("", index=df_emb_filt.index)).fillna("").astype(str)
            txt_inf = df_emb_filt.get("des_infrac", pd.Series("", index=df_emb_filt.index)).fillna("").astype(str)
            df_emb_filt = df_emb_filt[
                txt_tad.str.contains(REGEX_MINERACAO, case=False, regex=True)
                | txt_inf.str.contains(REGEX_MINERACAO, case=False, regex=True)
            ]

        # Calcula os valores consolidados para os cartões de métricas (KPIs)
        total_autos = len(df_emb_filt)
        area_filt_ha = float(df_emb_filt["qtd_area_e_num"].sum())
        valor_total_rs = float(df_emb_filt["valor_tad_num"].sum())
        municipios_emb = int(df_emb_filt["nom_munici"].nunique()) if "nom_munici" in df_emb_filt.columns and total_autos > 0 else 0

        # Exibe 4 KPIs no mesmo padrão visual da aba de Mineração
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("🚫 Total de Embargos", f"{total_autos:,}", f"{len(embargos_mineracao)} ligados à mineração")
        k2.metric("📐 Área Embargada", f"{area_filt_ha:,.2f} ha", f"Interseção real: {area_embargo_ha:,.2f} ha")
        k3.metric("💰 Valor Total (TAD)", f"R$ {valor_total_rs:,.2f}", "Autos de embargo IBAMA")
        k4.metric("🏙️ Municípios Atingidos", f"{municipios_emb}", "com termos de embargo")

        st.write("")
        # Divide a tela entre gráfico por município e gráfico por UF/tipo de infração
        ge1, ge2 = st.columns(2)

        with ge1:
            if total_autos > 0 and "nom_munici" in df_emb_filt.columns:
                df_emb_mun = (
                    df_emb_filt.groupby("nom_munici", as_index=False)
                    .agg(Embargos=("numero_tad", "count"), Area_ha=("qtd_area_e_num", "sum"))
                    .sort_values("Area_ha", ascending=True)
                    .tail(10)
                )
                fig_emb_mun = px.bar(
                    df_emb_mun,
                    x="Area_ha",
                    y="nom_munici",
                    orientation="h",
                    text_auto=".1f",
                    title="Área Embargada por Município (ha)",
                    labels={"nom_munici": "Município", "Area_ha": "Área (ha)"},
                    color_discrete_sequence=["#e67e22"],
                )
                fig_emb_mun.update_layout(height=380)
                st.plotly_chart(fig_emb_mun, use_container_width=True)

        with ge2:
            # Gráfico de evolução anual dos embargos do IBAMA extraídos de data_tad
            df_emb_anos = df_emb_filt[df_emb_filt["ano_embargo"] > 0]
            if total_autos > 0 and len(df_emb_anos) > 0:
                df_emb_evo = (
                    df_emb_anos.groupby("ano_embargo", as_index=False)
                    .agg(Embargos=("numero_tad", "count"), Area_ha=("qtd_area_e_num", "sum"))
                    .sort_values("ano_embargo")
                )
                df_emb_evo["Ano"] = df_emb_evo["ano_embargo"].astype(str)
                fig_emb_evo = px.bar(
                    df_emb_evo,
                    x="Ano",
                    y="Embargos",
                    text_auto=True,
                    title="Evolução Anual dos Embargos (IBAMA)",
                    labels={"Ano": "Ano do Embargo", "Embargos": "Nº de Embargos"},
                    color_discrete_sequence=["#d35400"],
                )
                fig_emb_evo.update_layout(height=380)
                st.plotly_chart(fig_emb_evo, use_container_width=True)
            else:
                st.info("Sem datas válidas (`data_tad`) para exibir a evolução anual dos embargos filtrados.")

        # Exibe a tabela detalhada dos embargos filtrados e botão de download em CSV
        colunas_exibir = [
            c for c in ["numero_tad", "data_tad", "nom_munici", "sig_uf", "qtd_area_e", "valor_tad", "sit_embarg", "des_infrac", "des_tad"]
            if c in df_emb_filt.columns
        ]
        st.markdown(f"#### 📋 Lista de Embargos ({total_autos} registros)")
        st.dataframe(df_emb_filt[colunas_exibir], use_container_width=True, hide_index=True)

        csv_emb_full = df_emb_filt.drop(columns=["qtd_area_e_num", "valor_tad_num"], errors="ignore").to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            label="⬇️ Baixar Embargos IBAMA Filtrados (CSV)",
            data=csv_emb_full,
            file_name="embargos_ibama_yanomami.csv",
            mime="text/csv",
        )

# PÁGINA 3: MAPA INTERATIVO DA TI YANOMAMI COM CAMADAS DE MINERAÇÃO
# ==============================================================================

if st.session_state.pagina_atual == "Mapa":
    # Inicializa estados persistentes das camadas do mapa (para os botões visuais de liga/desliga)
    defaults_camadas = {
        "camada_basemap": True,
        "camada_poligono": True,
        "camada_mineracao": True,
        "camada_emb_min": True,
        "camada_desmat": False,
        "camada_raster": True,
        "camada_comparar": False,
    }
    for k_cam, v_cam in defaults_camadas.items():
        if k_cam not in st.session_state:
            st.session_state[k_cam] = v_cam

    # Ajustes secundários recolhidos por padrão para deixar a tela limpa e o mapa no topo
    with st.expander("⚙️ Ajustes do Mapa (Mapa de Fundo, Transparência e Centralizar)", expanded=False):
        ctrl1, ctrl2, ctrl3 = st.columns([2, 2, 1])
        with ctrl1:
            mapa_base = st.selectbox(
                "Mapa de Fundo (Basemap)",
                options=["Esri Satélite", "CartoDB Claro", "CartoDB Escuro", "OpenTopoMap"],
                disabled=not st.session_state.camada_basemap,
                help="Desative o botão 'Fundo Esri / Mapa' abaixo para ver apenas o polígono e as classes.",
            )
        with ctrl2:
            opacidade_raster = st.slider(
                f"Transparência ({res_raster['fonte_raster']})",
                min_value=0.0,
                max_value=1.0,
                value=0.80,
                step=0.05,
            )
        with ctrl3:
            st.write("")
            if st.button("🎯 Centralizar Mapa", use_container_width=True):
                st.session_state.mapa_reset_id += 1

    # Escala temporal focada exatamente nos 3 anos dos rasters MapBiomas Col. 11 (2004, 2014, 2024)
    anos_raster = sorted([ano for ano, path in MAPBIOMAS_YANOMAMI_ANOS.items() if os.path.exists(path)])
    anos_mapa = anos_raster

    alertas_mapa = alertas_mineracao.copy()
    if len(anos_mapa) >= 2:
        valor_inicial = (
            st.session_state.ano_escala_temporal
            if st.session_state.ano_escala_temporal in anos_mapa
            else anos_mapa[-1]
        )
        col_ano, col_modo, col_kpi_ano = st.columns([2.4, 1.3, 1.3])
        with col_ano:
            ano_mapa_sel = st.select_slider(
                "⏳ Escala Temporal — Avanço da Mineração (2004 → 2014 → 2024+):",
                options=anos_mapa,
                value=valor_inicial,
            )
        with col_modo:
            modo_temporal = st.radio(
                "Exibição dos alertas:",
                options=["Acumulado até o ano", "Apenas no ano"],
                horizontal=True,
            )

        # Se o usuário mudou o ano na escala temporal e o raster correspondente mudou, atualiza o mapa
        if ano_mapa_sel != st.session_state.ano_escala_temporal:
            ano_raster_anterior = obter_ano_raster_correspondente(st.session_state.ano_escala_temporal)
            ano_raster_novo = obter_ano_raster_correspondente(ano_mapa_sel)
            st.session_state.ano_escala_temporal = ano_mapa_sel
            if ano_raster_novo != ano_raster_anterior:
                st.rerun()

        if modo_temporal == "Acumulado até o ano":
            alertas_mapa = alertas_mineracao[alertas_mineracao["ANODETEC"] <= ano_mapa_sel].copy()
        else:
            alertas_mapa = alertas_mineracao[alertas_mineracao["ANODETEC"] == ano_mapa_sel].copy()

        area_min_alertas = float(alertas_mapa["AREAHA"].sum()) if "AREAHA" in alertas_mapa.columns and len(alertas_mapa) > 0 else 0.0
        ano_raster_ativo = obter_ano_raster_correspondente(ano_mapa_sel)
        # Busca a área exata (resolução 30m) da classe 30 no MapBiomas Col. 11 para bater 100% com as outras abas
        df_col11_mapa = calcular_evolucao_mineracao_col11()
        area_min_raster = 0.0
        if len(df_col11_mapa) > 0 and ano_raster_ativo in df_col11_mapa["AnoNum"].values:
            area_min_raster = float(df_col11_mapa.loc[df_col11_mapa["AnoNum"] == ano_raster_ativo, "Area_ha"].iloc[0])
        elif len(res_raster["df_uso"]) > 0:
            area_min_raster = float(res_raster["df_uso"].loc[res_raster["df_uso"]["Código"] == 30, "Área (ha)"].sum())

        with col_kpi_ano:
            st.metric(
                f"⛏️ Mineração ({ano_mapa_sel})",
                f"{area_min_raster:,.1f} ha (Col.11 {ano_raster_ativo})",
                f"{len(alertas_mapa)} alertas ({area_min_alertas:,.1f} ha)",
            )
    elif len(anos_mapa) == 1:
        st.caption(f"⛏️ Dados de mineração disponíveis para o ano **{anos_mapa[0]}** ({len(alertas_mapa)} alertas).")

    # Botões visuais de liga/desliga para camadas (colorido = ligado, cinza = desligado)
    st.caption("🗂️ **Camadas do Mapa** — clique nos botões para ligar (✅) ou desligar (🚫):")
    tem_par_comparacao = os.path.exists(MAPBIOMAS_YANOMAMI_ANOS.get(2004, "")) and os.path.exists(MAPBIOMAS_YANOMAMI_ANOS.get(2024, ""))

    def botao_camada(col, chave: str, rotulo: str, disabled: bool = False, help_text: str | None = None):
        ativo = st.session_state[chave]
        texto = f"✅ {rotulo}" if ativo else f"🚫 {rotulo} (Off)"
        tipo = "primary" if ativo else "secondary"
        if col.button(texto, key=f"btn_{chave}", type=tipo, use_container_width=True, disabled=disabled, help=help_text):
            st.session_state[chave] = not ativo
            st.rerun()

    r1c1, r1c2, r1c3, r1c4 = st.columns(4)
    botao_camada(r1c1, "camada_poligono", "Limite TI")
    botao_camada(r1c2, "camada_mineracao", "Garimpo / Mineração")
    botao_camada(r1c3, "camada_emb_min", "Embargos IBAMA")
    botao_camada(r1c4, "camada_desmat", "PRODES")

    r2c1, r2c2, r2c3, r2c4 = st.columns(4)
    botao_camada(r2c1, "camada_raster", f"Classes ({res_raster['fonte_raster']})")
    botao_camada(
        r2c2,
        "camada_basemap",
        "Fundo Esri / Mapa",
        help_text="Desligue para remover o mapa de fundo Esri e ver o fundo limpo.",
    )
    botao_camada(r2c3, "camada_comparar", "Comparar 2004 vs 2024", disabled=not tem_par_comparacao)

    so_poligono_classes = (
        not st.session_state.camada_basemap
        and st.session_state.camada_poligono
        and st.session_state.camada_raster
        and not st.session_state.camada_mineracao
        and not st.session_state.camada_emb_min
        and not st.session_state.camada_desmat
    )
    if so_poligono_classes:
        if r2c4.button("🗺️ Voltar Visualização Completa", key="btn_modo_completo", type="secondary", use_container_width=True):
            st.session_state.camada_basemap = True
            st.session_state.camada_poligono = True
            st.session_state.camada_raster = True
            st.session_state.camada_mineracao = True
            st.session_state.camada_emb_min = True
            st.rerun()
    else:
        if r2c4.button(
            "🎯 Só Polígono e Classes",
            key="btn_so_poligono_classes",
            type="secondary",
            use_container_width=True,
            help="Tira o fundo Esri e outras camadas para mostrar apenas o polígono e as classes.",
        ):
            st.session_state.camada_basemap = False
            st.session_state.camada_poligono = True
            st.session_state.camada_raster = True
            st.session_state.camada_mineracao = False
            st.session_state.camada_emb_min = False
            st.session_state.camada_desmat = False
            st.rerun()

    mostrar_poligono = st.session_state.camada_poligono
    mostrar_mineracao = st.session_state.camada_mineracao
    mostrar_emb_min = st.session_state.camada_emb_min
    mostrar_desmat = st.session_state.camada_desmat
    mostrar_raster = st.session_state.camada_raster
    mostrar_basemap = st.session_state.camada_basemap
    comparar_2004_2024 = st.session_state.camada_comparar and tem_par_comparacao

    # Legenda interativa em caixas individuais (quadradinho de cor + checkbox) para ligar/desligar cada classe no mapa
    imagem_raster_mapa = res_raster["resized_image"]
    codigos_ativos = None
    if mostrar_raster and len(res_raster["df_uso"]) > 0:
        with st.expander("🎨 Filtrar Classes do MapBiomas no Mapa (clique para abrir)", expanded=False):
            df_classes_disp = res_raster["df_uso"]
            todos_codigos = [int(r["Código"]) for _, r in df_classes_disp.iterrows()]

            # Botões rápidos para marcar todas, deixar só mineração ou desmarcar todas as caixas
            b_leg1, b_leg2, b_leg3, _ = st.columns([1, 1.2, 1, 2.8])
            if b_leg1.button("✅ Ligar todas", use_container_width=True):
                for cod in todos_codigos:
                    st.session_state[f"chk_classe_{cod}"] = True
            if b_leg2.button("⛏️ Só Mineração (30)", use_container_width=True):
                for cod in todos_codigos:
                    st.session_state[f"chk_classe_{cod}"] = (cod == 30)
            if b_leg3.button("🚫 Desligar todas", use_container_width=True):
                for cod in todos_codigos:
                    st.session_state[f"chk_classe_{cod}"] = False

            # Renderiza cada classe em uma caixa com sua cor oficial e um checkbox individual
            codigos_ativos = set()
            cols_leg = st.columns(4)
            for idx, (_, row_c) in enumerate(df_classes_disp.iterrows()):
                cod_c = int(row_c["Código"])
                nome_c = str(row_c["Classe"])
                cor_c = str(row_c["Cor"])
                chave_chk = f"chk_classe_{cod_c}"
                if chave_chk not in st.session_state:
                    st.session_state[chave_chk] = True

                with cols_leg[idx % 4]:
                    c_cor, c_chk = st.columns([0.22, 1.78])
                    with c_cor:
                        # Exibe o quadradinho colorido correspondente à classe do raster
                        st.markdown(
                            f"<div style='width:16px;height:16px;background:{cor_c};border-radius:3px;border:1px solid #666;margin-top:6px;'></div>",
                            unsafe_allow_html=True,
                        )
                    with c_chk:
                        if st.checkbox(f"{cod_c} — {nome_c}", key=chave_chk):
                            codigos_ativos.add(cod_c)

            # Se nem todas as classes estiverem marcadas, gera a imagem RGBA apenas com as selecionadas
            if codigos_ativos != set(todos_codigos):
                out_arr = res_raster["out_image"]
                paleta = res_raster["paleta_cores"]
                img_filtrada = np.zeros_like(res_raster["resized_image"])
                for cod in codigos_ativos:
                    if cod in paleta:
                        img_filtrada[out_arr == cod] = paleta[cod]
                imagem_raster_mapa = img_filtrada

    # Calcula o centroide e os limites do polígono completo da TI Yanomami para o zoom inicial
    minx, miny, maxx, maxy = poligono_analise.to_crs(epsg=4326).total_bounds
    bounds_poligono = [[miny, minx], [maxy, maxx]]
    centro_lat, centro_lon = (miny + maxy) / 2, (minx + maxx) / 2

    # Mapeia a escolha do mapa de fundo para os parâmetros do Folium (ou None se o fundo estiver desligado)
    tiles_config = {
        "Esri Satélite": ("Esri World Imagery", "Esri"),
        "CartoDB Claro": ("https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png", "CartoDB Positron"),
        "CartoDB Escuro": ("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png", "CartoDB Dark Matter"),
        "OpenTopoMap": ("https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png", "OpenTopoMap"),
    }
    if mostrar_basemap:
        tile_url, tile_attr = tiles_config[mapa_base]
        folium_tile_kwargs = {"tiles": tile_url, "attr": tile_attr}
    else:
        folium_tile_kwargs = {"tiles": None}

    # Função auxiliar para gerar uma legenda HTML fixa no canto inferior direito do mapa
    def construir_legenda_html() -> str:
        """Monta a legenda visual com as cores das camadas vetoriais e classes do raster ativas."""
        itens_html = []
        if mostrar_poligono:
            itens_html.append("<div><span style='background:#f1c40f;border:2px solid #f39c12;'></span> Limite TI Yanomami</div>")
        if mostrar_mineracao and len(alertas_mapa) > 0:
            itens_html.append("<div><span style='background:#9b59b6;border:1px solid #4a235a;'></span> Mineração / Garimpo (Alertas)</div>")
        if mostrar_emb_min and len(entrada_embargo) > 0:
            itens_html.append("<div><span style='background:orange;border:1px solid black;'></span> Embargos IBAMA</div>")
        if mostrar_desmat and len(entrada_desmat) > 0:
            itens_html.append("<div><span style='background:red;border:1px solid darkred;'></span> Desmatamento PRODES</div>")

        if mostrar_raster and len(res_raster["df_uso"]) > 0:
            itens_html.append("<hr style='margin:5px 0;border-color:#ddd;'>")
            df_leg = res_raster["df_uso"]
            if codigos_ativos is not None:
                df_leg = df_leg[df_leg["Código"].isin(codigos_ativos)]
            for _, row_l in df_leg.head(8).iterrows():
                itens_html.append(
                    f"<div><span style='background:{row_l['Cor']};'></span> {int(row_l['Código'])} — {row_l['Classe']}</div>"
                )

        corpo = "".join(itens_html)
        return f"""
        <div id="webgis-legenda" style="
            position: fixed;
            bottom: 24px;
            right: 16px;
            z-index: 9999;
            background: rgba(255, 255, 255, 0.92);
            color: #111;
            padding: 10px 12px;
            border-radius: 8px;
            border: 1px solid #bbb;
            box-shadow: 0 2px 8px rgba(0,0,0,0.25);
            font-size: 12px;
            line-height: 1.5;
            max-width: 260px;
        ">
            <div style="font-weight:700;margin-bottom:4px;">🗺️ Legenda</div>
            <style>
                #webgis-legenda div span {{
                    display: inline-block;
                    width: 12px;
                    height: 12px;
                    margin-right: 6px;
                    vertical-align: middle;
                    border-radius: 2px;
                }}
            </style>
            {corpo}
        </div>
        """

    # Função auxiliar para converter colunas (ex.: Decimal/Data) em texto antes de enviar ao Folium
    def preparar_para_folium(gdf_origem: gpd.GeoDataFrame, colunas: list) -> gpd.GeoDataFrame:
        gdf_out = gdf_origem[colunas].to_crs(epsg=4326).copy()
        for col in colunas:
            if col != "geometry":
                gdf_out[col] = gdf_out[col].astype(str)
        return gdf_out

    # Função auxiliar para filtrar a imagem RGBA pelas classes selecionadas pelo usuário
    def filtrar_imagem_por_classes(res_r: dict) -> np.ndarray:
        """Retorna a imagem RGBA filtrada pelas classes ativas, se houver filtro aplicado."""
        if codigos_ativos is None:
            return res_r["resized_image"]
        out_arr = res_r["out_image"]
        paleta = res_r["paleta_cores"]
        img_f = np.zeros_like(res_r["resized_image"])
        for cod in codigos_ativos:
            if cod in paleta:
                img_f[out_arr == cod] = paleta[cod]
        return img_f

    # Decide entre o modo Mapa Duplo (2004 vs 2024 lado a lado) ou Mapa Único padrão
    if comparar_2004_2024:
        # Carrega e mantém em cache os rasters de 2004 e 2024 para comparação sincronizada
        for ano_cmp in (2004, 2024):
            chave_cmp = f"cache_cmp_{ano_cmp}"
            chave_pol_cmp = (poligono_nome, len(poligono_bytes), ano_cmp)
            if st.session_state.get(f"{chave_cmp}_key") != chave_pol_cmp:
                with st.spinner(f"Preparando raster {ano_cmp} para comparação..."):
                    st.session_state[chave_cmp] = processar_raster_otimizado(
                        MAPBIOMAS_YANOMAMI_ANOS[ano_cmp], poligono_bytes, poligono_nome
                    )
                    st.session_state[f"{chave_cmp}_key"] = chave_pol_cmp

        res_2004 = st.session_state["cache_cmp_2004"]
        res_2024 = st.session_state["cache_cmp_2024"]

        st.info("🔀 **Modo Comparação Ativo:** Esquerda = **2004** | Direita = **2024** (mova ou dê zoom em qualquer lado para sincronizar).")
        m_dual = DualMap(location=[centro_lat, centro_lon], zoom_start=7, **folium_tile_kwargs)
        if not mostrar_basemap:
            m_dual.get_root().header.add_child(folium.Element("<style>.leaflet-container { background: #ffffff !important; }</style>"))

        # Adiciona os rasters de 2004 à esquerda e 2024 à direita
        if mostrar_raster:
            folium.raster_layers.ImageOverlay(
                image=filtrar_imagem_por_classes(res_2004),
                bounds=res_2004["bounds"],
                opacity=opacidade_raster,
                name="MapBiomas 2004",
            ).add_to(m_dual.m1)
            folium.raster_layers.ImageOverlay(
                image=filtrar_imagem_por_classes(res_2024),
                bounds=res_2024["bounds"],
                opacity=opacidade_raster,
                name="MapBiomas 2024",
            ).add_to(m_dual.m2)

        # Adiciona o limite da TI nos dois painéis para referência espacial
        if mostrar_poligono:
            pol_limpo = gpd.GeoDataFrame(geometry=poligono_analise.to_crs(epsg=4326).geometry, crs="EPSG:4326")
            for sub_m in (m_dual.m1, m_dual.m2):
                folium.GeoJson(
                    pol_limpo,
                    name="Limite TI Yanomami",
                    style_function=lambda _: {"fillColor": "#f1c40f", "color": "#f39c12", "weight": 2.0, "fillOpacity": 0.04},
                ).add_to(sub_m)

        # Adiciona os alertas de mineração (2024) e embargos no painel da direita (2024)
        if mostrar_mineracao and len(alertas_mineracao) > 0:
            cols_min = [c for c in ["CODEALERTA", "MUNICIPIO", "ANODETEC", "AREAHA", "geometry"] if c in alertas_mineracao.columns]
            folium.GeoJson(
                preparar_para_folium(alertas_mineracao, cols_min),
                name="⛏️ Mineração (Alertas)",
                style_function=lambda _: {"fillColor": "#9b59b6", "color": "#4a235a", "weight": 1.2, "fillOpacity": 0.75},
            ).add_to(m_dual.m2)

        m_dual.m1.fit_bounds(bounds_poligono)
        m_dual.m2.fit_bounds(bounds_poligono)
        m_dual.get_root().html.add_child(folium.Element(construir_legenda_html()))

        st_folium(
            m_dual,
            width="100%",
            height=860,
            key=f"mapa_dual_{st.session_state.mapa_reset_id}",
            returned_objects=[],
        )
    else:
        # Cria o mapa Folium único centralizado na Terra Indígena Yanomami
        m = folium.Map(location=[centro_lat, centro_lon], zoom_start=7, **folium_tile_kwargs)
        if not mostrar_basemap:
            m.get_root().header.add_child(folium.Element("<style>.leaflet-container { background: #ffffff !important; }</style>"))

        # Adiciona o raster de cobertura do solo se o toggle estiver ativo
        if mostrar_raster:
            folium.raster_layers.ImageOverlay(
                image=imagem_raster_mapa,
                bounds=res_raster["bounds"],
                opacity=opacidade_raster,
                name=res_raster["fonte_raster"],
                interactive=True,
                cross_origin=False,
                zindex=1,
            ).add_to(m)

        # Adiciona o limite oficial da TI Yanomami
        if mostrar_poligono:
            pol_limpo = gpd.GeoDataFrame(geometry=poligono_analise.to_crs(epsg=4326).geometry, crs="EPSG:4326")
            folium.GeoJson(
                pol_limpo,
                name="Limite TI Yanomami",
                style_function=lambda _: {"fillColor": "#f1c40f", "color": "#f39c12", "weight": 2.5, "fillOpacity": 0.06},
            ).add_to(m)

        # Adiciona os alertas de mineração do MapBiomas em roxo com popup informativo ao clicar
        if mostrar_mineracao and len(alertas_mapa) > 0:
            cols_min = [c for c in ["CODEALERTA", "MUNICIPIO", "ESTADO", "ANODETEC", "AREAHA", "VPRESSAO", "geometry"] if c in alertas_mapa.columns]
            min_limpo = preparar_para_folium(alertas_mapa, cols_min)
            popup_min = folium.GeoJsonPopup(
                fields=[c for c in cols_min if c != "geometry"],
                aliases=[f"{c}:" for c in cols_min if c != "geometry"],
            )
            folium.GeoJson(
                min_limpo,
                name="⛏️ Mineração / Garimpo (MapBiomas)",
                style_function=lambda _: {"fillColor": "#9b59b6", "color": "#4a235a", "weight": 1.5, "fillOpacity": 0.8},
                popup=popup_min,
            ).add_to(m)

        # Adiciona os embargos do IBAMA com popup mostrando descrição do auto de infração (des_tad)
        if mostrar_emb_min and len(entrada_embargo) > 0:
            cols_emb = [c for c in ["numero_tad", "nom_munici", "sig_uf", "qtd_area_e", "des_tad", "geometry"] if c in entrada_embargo.columns]
            emb_limpo = preparar_para_folium(entrada_embargo, cols_emb)
            popup_emb = folium.GeoJsonPopup(
                fields=[c for c in cols_emb if c != "geometry"],
                aliases=[f"{c}:" for c in cols_emb if c != "geometry"],
            )
            folium.GeoJson(
                emb_limpo,
                name="🚫 Embargos IBAMA",
                style_function=lambda _: {"fillColor": "orange", "color": "black", "weight": 1.2, "fillOpacity": 0.75},
                popup=popup_emb,
            ).add_to(m)

        # Adiciona os polígonos de desmatamento PRODES se o toggle estiver ativo
        if mostrar_desmat and len(entrada_desmat) > 0:
            desm_limpo = gpd.GeoDataFrame(geometry=entrada_desmat.to_crs(epsg=4326).geometry, crs="EPSG:4326")
            folium.GeoJson(
                desm_limpo,
                name="🪓 Desmatamento PRODES",
                style_function=lambda _: {"fillColor": "red", "color": "darkred", "weight": 1, "fillOpacity": 0.6},
            ).add_to(m)

        # Adiciona opção de fundo limpo no LayerControl do próprio mapa quando o basemap estiver ativo
        if mostrar_basemap:
            folium.TileLayer(
                tiles="data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7",
                attr=" ",
                name="⬜ Sem Mapa de Fundo",
                overlay=False,
                control=True,
                show=False,
            ).add_to(m)

        # Adiciona controle de tela cheia, camadas e legenda fixa nos cantos do mapa
        Fullscreen(
            position="topleft",
            title="Tela cheia",
            title_cancel="Sair da tela cheia",
            force_separate_button=True,
        ).add_to(m)
        folium.LayerControl(position="topright", collapsed=True).add_to(m)
        m.get_root().html.add_child(folium.Element(construir_legenda_html()))
        m.fit_bounds(bounds_poligono)

        # Renderiza o mapa ocupando praticamente toda a tela
        st_folium(
            m,
            width="100%",
            height=880,
            key=f"mapa_webgis_{st.session_state.mapa_reset_id}",
            returned_objects=[],
        )

    st.caption(f"📍 Centro da área: Lat `{centro_lat:.5f}`, Lon `{centro_lon:.5f}` — Clique nos polígonos roxos (Mineração) ou laranjas (IBAMA) para ver detalhes.")


# ==============================================================================
# PÁGINA 3: GRÁFICOS, COBERTURA DO SOLO E TABELAS DE ATRIBUTOS
# ==============================================================================

elif st.session_state.pagina_atual == "Gráficos e Dados":
    # KPIs principais focados nos anos 2004, 2014 e 2024 (MapBiomas Col. 11)
    df_col11_graf = calcular_evolucao_mineracao_col11()
    df_desm_col11 = calcular_evolucao_desmatamento_col11()
    areas_col11 = {int(r["AnoNum"]): float(r["Area_ha"]) for _, r in df_col11_graf.iterrows()} if len(df_col11_graf) > 0 else {}
    desm_por_ano = {int(r["AnoNum"]): float(r["Antropico_ha"]) for _, r in df_desm_col11.iterrows()} if len(df_desm_col11) > 0 else {}
    flor_por_ano = {int(r["AnoNum"]): float(r["Floresta_ha"]) for _, r in df_desm_col11.iterrows()} if len(df_desm_col11) > 0 else {}

    a04 = areas_col11.get(2004, 0.0)
    a14 = areas_col11.get(2014, 0.0)
    a24 = areas_col11.get(2024, 0.0)
    var_pct = ((a24 - a04) / a04 * 100) if a04 > 0 else 0.0

    d04 = desm_por_ano.get(2004, 0.0)
    d14 = desm_por_ano.get(2014, 0.0)
    d24 = desm_por_ano.get(2024, 0.0)
    var_desm_pct = ((d24 - d04) / d04 * 100) if d04 > 0 else 0.0
    dif_flor = flor_por_ano.get(2024, 0.0) - flor_por_ano.get(2004, 0.0)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("📐 Área Total TI", f"{area_total_ha:,.2f} ha", f"EPSG:{epsg_metrico}")
    c2.metric("⛏️ Mineração 2004", f"{a04:,.2f} ha", "MapBiomas Col. 11")
    c3.metric("⛏️ Mineração 2014", f"{a14:,.2f} ha", "MapBiomas Col. 11")
    c4.metric("⛏️ Mineração 2024", f"{a24:,.2f} ha", f"+{var_pct:,.1f}% desde 2004")

    k_d1, k_d2, k_d3, k_d4 = st.columns(4)
    k_d1.metric("🪓 Área Antrópica / Desmat. 2004", f"{d04:,.2f} ha", "MapBiomas Col. 11")
    k_d2.metric("🪓 Área Antrópica / Desmat. 2014", f"{d14:,.2f} ha", "MapBiomas Col. 11")
    k_d3.metric("🪓 Área Antrópica / Desmat. 2024", f"{d24:,.2f} ha", f"+{var_desm_pct:,.1f}% desde 2004")
    k_d4.metric("🌲 Floresta Nativa 2024", f"{flor_por_ano.get(2024, 0.0):,.0f} ha", f"{dif_flor:,.0f} ha vs 2004")

    subtab_uso, subtab_min, subtab_desm, subtab_emb, subtab_exp = st.tabs([
        "🌱 Cobertura do Solo",
        "⛏️ Mineração e Garimpo",
        "🪓 Desmatamento (2004–2024)",
        "🚫 Embargos IBAMA",
        "🔎 Explorador de Dados",
    ])

    with subtab_uso:
        f_g1, f_g2, f_g3 = st.columns([1.3, 1.3, 1.4])
        with f_g1:
            so_mineracao = st.toggle("⛏️ Ver só o gráfico de Mineração (2004, 2014 e 2024)", value=False)
        with f_g2:
            ano_graf_sel = st.radio(
                "📅 Ano (MapBiomas Col. 11):",
                options=[2004, 2014, 2024],
                index=2,
                horizontal=True,
                disabled=so_mineracao,
            )
        with f_g3:
            tipo_viz = st.radio(
                "Formato do gráfico:",
                options=["Barras", "Rosca (Pizza)"],
                horizontal=True,
            )

        if so_mineracao:
            if len(df_col11_graf) == 0:
                st.warning("Rasters de 2004, 2014 e 2024 não encontrados em Dados/.")
            else:
                col_gm1, col_gm2 = st.columns([1.4, 1])
                with col_gm1:
                    if tipo_viz == "Barras":
                        fig_min_only = px.bar(
                            df_col11_graf,
                            x="Ano",
                            y="Area_ha",
                            text_auto=".2f",
                            title="Evolução da Mineração — MapBiomas Col. 11 (2004, 2014 e 2024)",
                            labels={"Ano": "Ano", "Area_ha": "Área de Mineração (ha)"},
                            color_discrete_sequence=["#8e44ad"],
                        )
                        fig_min_only.update_layout(height=440)
                    else:
                        fig_min_only = px.pie(
                            df_col11_graf,
                            names="Ano",
                            values="Area_ha",
                            hole=0.4,
                            title="Proporção da Área de Mineração por Ano (2004, 2014 e 2024)",
                            color_discrete_sequence=["#b388eb", "#8e44ad", "#5e2d79"],
                        )
                        fig_min_only.update_layout(height=440)
                    st.plotly_chart(fig_min_only, use_container_width=True)

                with col_gm2:
                    st.markdown("#### Dados de Mineração (2004, 2014 e 2024)")
                    df_min_show = df_col11_graf[["Ano", "Pixels", "Area_ha"]].rename(columns={"Area_ha": "Área (ha)"})
                    st.dataframe(df_min_show, use_container_width=True, hide_index=True, height=320)
                    csv_min_anos = df_min_show.to_csv(index=False).encode("utf-8-sig")
                    st.download_button(
                        label="⬇️ Baixar Mineração 2004/2014/2024 (CSV)",
                        data=csv_min_anos,
                        file_name="mineracao_yanomami_2004_2014_2024.csv",
                        mime="text/csv",
                        use_container_width=True,
                    )
        else:
            caminho_ano = MAPBIOMAS_YANOMAMI_ANOS.get(ano_graf_sel, raster_fonte)
            chave_ano_graf = (poligono_nome, len(poligono_bytes), ano_graf_sel)
            if st.session_state.get("cache_graf_ano_key") != chave_ano_graf:
                with st.spinner(f"Carregando classes de {ano_graf_sel}..."):
                    st.session_state.cache_graf_ano_res = processar_raster_otimizado(caminho_ano, poligono_bytes, poligono_nome)
                    st.session_state.cache_graf_ano_key = chave_ano_graf
            df_uso = st.session_state.cache_graf_ano_res["df_uso"]

            if len(df_uso) == 0:
                st.warning("Nenhuma classe válida de cobertura do solo foi identificada dentro do recorte.")
            else:
                qtd_classes = st.slider(
                    "Quantidade de classes principais no gráfico:",
                    min_value=1,
                    max_value=len(df_uso),
                    value=min(10, len(df_uso)),
                )
                df_top = df_uso.head(qtd_classes)
                mapa_cores_plotly = dict(zip(df_top["Classe"], df_top["Cor"]))

                col_graf_uso, col_tab_uso = st.columns([1.4, 1])

                with col_graf_uso:
                    if tipo_viz == "Barras":
                        fig_uso = px.bar(
                            df_top.sort_values("Área (ha)"),
                            x="Área (ha)",
                            y="Classe",
                            orientation="h",
                            color="Classe",
                            color_discrete_map=mapa_cores_plotly,
                            text_auto=".2f",
                            title=f"Cobertura do Solo — {ano_graf_sel} (ha)",
                        )
                        fig_uso.update_layout(showlegend=False, height=460)
                    else:
                        fig_uso = px.pie(
                            df_top,
                            names="Classe",
                            values="Área (ha)",
                            hole=0.4,
                            color="Classe",
                            color_discrete_map=mapa_cores_plotly,
                            title=f"Proporção de Cobertura do Solo — {ano_graf_sel} (%)",
                        )
                        fig_uso.update_layout(height=460)
                    st.plotly_chart(fig_uso, use_container_width=True)

                with col_tab_uso:
                    st.markdown(f"#### Tabela Completa — {ano_graf_sel} (hectares)")
                    st.dataframe(
                        df_uso[["Código", "Classe", "Área (ha)", "Percentual (%)"]],
                        use_container_width=True,
                        height=390,
                        hide_index=True,
                    )
                    csv_uso = df_uso[["Código", "Classe", "Área (ha)", "Percentual (%)"]].to_csv(index=False).encode("utf-8-sig")
                    st.download_button(
                        label=f"⬇️ Baixar Tabela {ano_graf_sel} (CSV)",
                        data=csv_uso,
                        file_name=f"cobertura_solo_yanomami_{ano_graf_sel}.csv",
                        mime="text/csv",
                        use_container_width=True,
                    )

    with subtab_min:
        renderizar_painel_mineracao()

    with subtab_desm:
        st.caption(
            "📌 **Nota metodológica:** Os valores de **2004, 2014 e 2024** representam a área antrópica acumulada (desmatamento consolidado: pastagem, mosaico de usos, áreas não vegetadas, mineração, aquicultura e lavouras) no **MapBiomas Col. 11 (30 m)**. Já os alertas vetoriais do **PRODES/Alertas** cobrem o período de **2019 a 2024**."
        )
        if len(df_desm_col11) > 0:
            gd1, gd2 = st.columns(2)
            with gd1:
                df_melt = df_desm_col11.melt(
                    id_vars=["Ano"],
                    value_vars=["Mineracao_ha", "Outros_Antropicos_ha"],
                    var_name="Tipo",
                    value_name="Área (ha)",
                )
                df_melt["Tipo"] = df_melt["Tipo"].map({
                    "Mineracao_ha": "Mineração (Classe 30)",
                    "Outros_Antropicos_ha": "Outros Usos Antrópicos (Pastagem, Mosaico, etc.)",
                })
                fig_desm_col11 = px.bar(
                    df_melt,
                    x="Ano",
                    y="Área (ha)",
                    color="Tipo",
                    barmode="stack",
                    text_auto=".1f",
                    title="Área Antrópica / Desmatamento Acumulado (2004, 2014 e 2024)",
                    color_discrete_map={
                        "Mineração (Classe 30)": "#8e44ad",
                        "Outros Usos Antrópicos (Pastagem, Mosaico, etc.)": "#e67e22",
                    },
                )
                fig_desm_col11.update_layout(height=400, legend_title_text="")
                st.plotly_chart(fig_desm_col11, use_container_width=True)

            with gd2:
                if len(entrada_desmat) > 0 and "ANODETEC" in entrada_desmat.columns:
                    df_prodes_anual = (
                        entrada_desmat.assign(Ano=entrada_desmat["ANODETEC"].astype(int).astype(str))
                        .groupby("Ano", as_index=False)
                        .agg(Alertas=("AREAHA", "count"), Area_ha=("AREAHA", "sum"))
                        .sort_values("Ano")
                    )
                    df_prodes_anual["Area_ha"] = pd.to_numeric(df_prodes_anual["Area_ha"], errors="coerce").round(2)
                    fig_prodes = px.bar(
                        df_prodes_anual,
                        x="Ano",
                        y="Area_ha",
                        text_auto=".1f",
                        title="Desmatamento Detectado por Ano (PRODES / Alertas 2019–2024)",
                        labels={"Area_ha": "Área (ha)"},
                        color_discrete_sequence=["#c0392b"],
                    )
                    fig_prodes.update_layout(height=400)
                    st.plotly_chart(fig_prodes, use_container_width=True)
                else:
                    st.info("Sem registros anuais de alertas PRODES para a área.")

            st.markdown("#### Tabela Síntese — Desmatamento / Uso Antrópico e Floresta (2004, 2014 e 2024)")
            df_desm_tab = df_desm_col11[["Ano", "Antropico_ha", "Mineracao_ha", "Outros_Antropicos_ha", "Floresta_ha"]].rename(
                columns={
                    "Antropico_ha": "Área Antrópica / Desmat. Total (ha)",
                    "Mineracao_ha": "Mineração (ha)",
                    "Outros_Antropicos_ha": "Outros Usos Antrópicos (ha)",
                    "Floresta_ha": "Floresta Nativa 3+6 (ha)",
                }
            )
            st.dataframe(df_desm_tab, use_container_width=True, hide_index=True)
            st.download_button(
                label="⬇️ Baixar Desmatamento 2004/2014/2024 (CSV)",
                data=df_desm_tab.to_csv(index=False).encode("utf-8-sig"),
                file_name="desmatamento_yanomami_2004_2014_2024.csv",
                mime="text/csv",
            )

    with subtab_emb:
        renderizar_painel_embargos()

    with subtab_exp:
        # Converte os GeoDataFrames recortados em DataFrames comuns (sem a coluna geometry)
        df_min = pd.DataFrame(alertas_mineracao.drop(columns=["geometry"], errors="ignore"))
        df_alertas = pd.DataFrame(entrada_alertas.drop(columns=["geometry"], errors="ignore"))
        df_desmat = pd.DataFrame(entrada_desmat.drop(columns=["geometry"], errors="ignore"))
        df_embargo = pd.DataFrame(entrada_embargo.drop(columns=["geometry"], errors="ignore"))

        # Controles de seleção do tema, tipo de gráfico e eixos X/Y
        col1_graf, col2_graf, col3_graf, col4_graf = st.columns(4)

        tema_grafico = col1_graf.selectbox(
            "Selecione o tema da análise",
            options=[
                "Mineração (MapBiomas Alertas)",
                "Todos os Alertas (MapBiomas)",
                "Embargos (IBAMA)",
                "Desmatamento (PRODES)",
            ],
        )

        if tema_grafico == "Mineração (MapBiomas Alertas)":
            df_analisado = df_min
        elif tema_grafico == "Todos os Alertas (MapBiomas)":
            df_analisado = df_alertas
        elif tema_grafico == "Embargos (IBAMA)":
            df_analisado = df_embargo
        else:
            df_analisado = df_desmat

        if len(df_analisado) > 0 and len(df_analisado.columns) > 0:
            tipo_grafico = col2_graf.selectbox(
                "Tipo de gráfico",
                options=["histogram", "bar", "box", "line", "scatter", "violin"],
                index=0,
            )
            plot_func = getattr(px, tipo_grafico)

            max_index = len(df_analisado.columns) - 1
            x_index = min(1, max_index) if max_index >= 1 else 0
            y_index = min(0, max_index)

            x_val = col3_graf.selectbox("Eixo X", options=df_analisado.columns, index=x_index)
            y_val = col4_graf.selectbox("Eixo Y", options=df_analisado.columns, index=y_index)

            plot = plot_func(df_analisado, x=x_val, y=y_val)
            st.plotly_chart(plot, use_container_width=True)

            # Tabela completa expansível e botão de download em CSV
            with st.expander(f"📋 Ver Tabela Completa — {tema_grafico} ({len(df_analisado)} registros)", expanded=True):
                st.dataframe(df_analisado, use_container_width=True)
                csv_tema = df_analisado.to_csv(index=False).encode("utf-8-sig")
                st.download_button(
                    label=f"⬇️ Baixar Dados de {tema_grafico} (CSV)",
                    data=csv_tema,
                    file_name=f"yanomami_{tema_grafico.lower().replace(' ', '_')}.csv",
                    mime="text/csv",
                )
        else:
            st.info(f"Não foram encontradas sobreposições para **{tema_grafico}** dentro da área analisada.")


# ==============================================================================
