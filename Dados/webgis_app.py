import streamlit as st
import folium
import numpy as np
import cv2
import pandas as pd
import geopandas as gpd
import plotly.express as px
import logging
from typing import Tuple, Optional, Dict, Any

from streamlit_folium import st_folium
from rasterio.io import MemoryFile
from rasterio.mask import mask
from folium.raster_layers import ImageOverlay
from zona_utm import calcular_utm
from utils import color_map, value_to_class

from fpdf import FPDF
from io import BytesIO
from datetime import datetime
from decimal import Decimal

# Configuração inicial
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constantes (deveriam ser movidas para um arquivo de configuração)
PATHS = {
    'embargo': 'D:/UFPI_2024_2025/2W CURSO/mba_dashboards/Dados/embargo_ibama.parquet',
    'desmat': 'D:/UFPI_2024_2025/2W CURSO/mba_dashboards/Dados/prodes.parquet',
    'tis': 'D:/UFPI_2024_2025/2W CURSO/mba_dashboards/Dados/tis.parquet'
}

# ========== FUNÇÕES PRINCIPAIS ==========

@st.cache_data(show_spinner="Preparando dados para visualização...")
def preparar_para_folium(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """
    Prepara um GeoDataFrame para visualização no Folium, convertendo Decimal para float.
    
    Args:
        gdf: GeoDataFrame a ser preparado
        
    Returns:
        GeoDataFrame preparado para visualização
    """
    try:
        for col in gdf.columns:
            if col != 'geometry' and gdf[col].dtype == 'object':
                gdf[col] = gdf[col].apply(lambda x: float(x) if isinstance(x, Decimal) else x)
        return gdf
    except Exception as e:
        logger.error(f"Erro ao preparar dados para Folium: {str(e)}")
        return gdf

def gerar_pdf(gdf_desmat: gpd.GeoDataFrame, 
              gdf_embargo: gpd.GeoDataFrame, 
              gdf_tis: gpd.GeoDataFrame, 
              matriz: np.ndarray) -> BytesIO:
    """
    Gera um relatório PDF com os resultados da análise espacial.
    
    Args:
        gdf_desmat: GeoDataFrame com áreas desmatadas
        gdf_embargo: GeoDataFrame com áreas embargadas
        gdf_tis: GeoDataFrame com terras indígenas
        matriz: Matriz numpy com dados raster
        
    Returns:
        BytesIO com o conteúdo do PDF
    """
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.set_auto_page_break(auto=True, margin=15)

    # Cabeçalho
    data = datetime.now().strftime('%d/%m/%Y %H:%M')
    pdf.cell(200, 10, "Relatório de Análise Espacial", ln=True, align='C')
    pdf.set_font("Arial", 'I', size=10)
    pdf.cell(0, 10, f"Geração: {data}", ln=True)
    pdf.ln(5)

    # Métricas principais
    pdf.set_font("Arial", size=12)
    
    def calcular_area(gdf: gpd.GeoDataFrame) -> float:
        """Calcula área em hectares de um GeoDataFrame."""
        return round(gdf.area.iloc[0] / 10000, 2) if not gdf.empty else 0.0

    pdf.cell(0, 10, f"Área desmatada (ha): {calcular_area(gdf_desmat)}", ln=True)
    pdf.cell(0, 10, f"Área embargada (ha): {calcular_area(gdf_embargo)}", ln=True)
    pdf.cell(0, 10, f"Área de TIs (ha): {calcular_area(gdf_tis)}", ln=True)

    # Resumo por classes
    pdf.ln(10)
    pdf.set_font("Arial", 'B', size=12)
    pdf.cell(0, 10, "Resumo por classes do raster:", ln=True)
    pdf.set_font("Arial", size=11)

    if matriz is not None:
        unique, counts = np.unique(matriz, return_counts=True)
        for val, cnt in zip(unique, counts):
            classe = value_to_class.get(val, "Desconhecida")
            area = (cnt * 900) / 10000
            pdf.cell(0, 10, f"{classe}: {area:.2f} ha", ln=True)
    else:
        pdf.cell(0, 10, "Raster não carregado ou inválido.", ln=True)

    buffer = BytesIO()
    pdf.output(buffer)
    buffer.seek(0)
    return buffer

@st.cache_data(show_spinner="Carregando e processando dados vetoriais...")
def carregar_e_intersectar(path: str, poligono: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """
    Carrega um dataset geoespacial e intersecta com o polígono de interesse.
    
    Args:
        path: Caminho para o arquivo de dados
        poligono: GeoDataFrame com o polígono de análise
        
    Returns:
        GeoDataFrame com a interseção
    """
    try:
        gdf = gpd.read_parquet(path).to_crs(poligono.crs)
        intersect = gpd.sjoin(gdf, poligono, how='inner', predicate='intersects')
        return gpd.overlay(intersect, poligono, how='intersection') if not intersect.empty else gpd.GeoDataFrame()
    except Exception as e:
        logger.error(f"Erro ao carregar e intersectar {path}: {str(e)}")
        return gpd.GeoDataFrame()

@st.cache_data(show_spinner="Processando dados raster...")
def preparar_raster(uploaded_file: BytesIO, 
                   poligono: gpd.GeoDataFrame, 
                   cmap: Dict[int, Tuple[int, int, int, int]]) -> Tuple[Optional[np.ndarray], Optional[list], Optional[np.ndarray]]:
    """
    Prepara dados raster para visualização e análise.
    
    Args:
        uploaded_file: Arquivo raster carregado
        poligono: GeoDataFrame com o polígono de recorte
        cmap: Dicionário de mapeamento de valores para cores
        
    Returns:
        Tupla com (imagem RGB, bounds, matriz de valores)
    """
    try:
        with MemoryFile(uploaded_file.getvalue()) as memfile:
            with memfile.open() as src:
                if poligono.crs != src.crs:
                    poligono = poligono.to_crs(src.crs)
                out_image, out_transform = mask(src, poligono.geometry, crop=True)
                matriz = out_image[0]
                h, w = matriz.shape
                rgb = np.zeros((h, w, 4), dtype=np.uint8)
                for val, cor in cmap.items():
                    rgb[matriz == val] = cor
                img = cv2.resize(rgb, (w, h), interpolation=cv2.INTER_NEAREST)
                minx, miny = out_transform * (0, 0)
                maxx, maxy = out_transform * (w, h)
                return img, [[miny, minx], [maxy, maxx]], matriz
    except Exception as e:
        logger.error(f"Erro ao processar raster: {str(e)}")
        return None, None, None

def add_layer(gdf: gpd.GeoDataFrame, nome: str, cor: str, mapa: folium.Map, 
              tooltip_fields: Optional[list] = None) -> None:
    """
    Adiciona uma camada vetorial ao mapa Folium.
    
    Args:
        gdf: GeoDataFrame com os dados
        nome: Nome da camada
        cor: Cor de preenchimento
        mapa: Mapa Folium
        tooltip_fields: Campos a serem mostrados no tooltip
    """
    if not gdf.empty:
        gdf = preparar_para_folium(gdf)
        
        # Configura tooltip se campos forem fornecidos
        if tooltip_fields:
            tooltip = folium.features.GeoJsonTooltip(
                fields=tooltip_fields,
                aliases=[f.capitalize() for f in tooltip_fields],
                localize=True
            )
        else:
            tooltip = None
            
        folium.GeoJson(
            gdf,
            name=nome,
            style_function=lambda x: {
                'fillColor': cor,
                'color': 'black',
                'weight': 1,
                'fillOpacity': 0.6
            },
            tooltip=tooltip
        ).add_to(mapa)

def criar_mapa_base(poligono: gpd.GeoDataFrame) -> folium.Map:
    """
    Cria um mapa Folium base centrado no polígono de interesse.
    
    Args:
        poligono: GeoDataFrame com o polígono de análise
        
    Returns:
        Mapa Folium configurado
    """
    centroide = poligono.geometry.centroid.iloc[0]
    m = folium.Map(
        location=[centroide.y, centroide.x], 
        zoom_start=12, 
        tiles='Esri World Imagery',
        control_scale=True
    )
    
    # Adiciona o polígono de estudo ao mapa
    folium.GeoJson(
        poligono,
        name="Área de Estudo",
        style_function=lambda x: {
            'fillColor': 'blue',
            'color': 'blue',
            'weight': 2,
            'fillOpacity': 0.1
        }
    ).add_to(m)
    
    return m

def mostrar_metricas(area_des: float, area_emb: float, area_tis: float) -> None:
    """
    Exibe métricas principais na interface.
    
    Args:
        area_des: Área desmatada em hectares
        area_emb: Área embargada em hectares
        area_tis: Área de terras indígenas em hectares
    """
    col1, col2, col3 = st.columns(3)
    col1.metric("Área Desmatada (ha)", f"{area_des:.2f}")
    col2.metric("Área Embargada (ha)", f"{area_emb:.2f}")
    col3.metric("Área de TIs (ha)", f"{area_tis:.2f}")

def mostrar_grafico_distribuicao(area_des: float, area_emb: float, area_tis: float) -> None:
    """
    Exibe gráfico de barras com a distribuição de áreas.
    
    Args:
        area_des: Área desmatada em hectares
        area_emb: Área embargada em hectares
        area_tis: Área de terras indígenas em hectares
    """
    dados = {
        "Tipo": ["Desmatamento", "Embargos", "TIs"],
        "Área (ha)": [area_des, area_emb, area_tis]
    }
    fig = px.bar(
        dados, 
        x="Tipo", 
        y="Área (ha)", 
        color="Tipo",
        title="Distribuição de Áreas",
        labels={"Tipo": "Categoria", "Área (ha)": "Área (hectares)"}
    )
    st.plotly_chart(fig, use_container_width=True)

# ========== INTERFACE DO USUÁRIO ==========

def main():
    st.set_page_config(page_title="WebGIS - Análise Espacial", layout="wide")
    st.title('🌍 WebGIS - Análise Espacial para Regularização')
    
    # Sidebar - Uploads e configurações
    with st.sidebar:
        st.header('Uploads')
        pol_file = st.file_uploader("Polígono (GeoJSON/Shapefile)", type=['geojson', 'shp'])
        ras_file = st.file_uploader("Raster (MapBiomas)", type=['tif'])
        
        st.header("Configurações de Visualização")
        opacidade = st.slider("Opacidade do Raster", 0.1, 1.0, 0.7)
        mostrar_graficos = st.checkbox("Mostrar gráficos", value=True)

    if pol_file and ras_file:
        try:
            # Processamento dos dados
            with st.spinner('Carregando e processando dados...'):
                poligono = gpd.read_file(pol_file)
                
                if poligono.crs.is_geographic:
                    poligono = poligono.to_crs(epsg=calcular_utm(poligono))
                
                # Carrega e intersecta camadas vetoriais
                embargo_gdf = carregar_e_intersectar(PATHS['embargo'], poligono)
                desmat_gdf = carregar_e_intersectar(PATHS['desmat'], poligono)
                tis_gdf = carregar_e_intersectar(PATHS['tis'], poligono)
                
                # Dissolve geometrias para cálculo de área total
                embargo_diss = embargo_gdf.dissolve() if not embargo_gdf.empty else gpd.GeoDataFrame()
                desmat_diss = desmat_gdf.dissolve() if not desmat_gdf.empty else gpd.GeoDataFrame()
                tis_diss = tis_gdf.dissolve() if not tis_gdf.empty else gpd.GeoDataFrame()
                
                # Calcula áreas em hectares
                area_emb = embargo_diss.area.iloc[0]/10000 if not embargo_diss.empty else 0
                area_des = desmat_diss.area.iloc[0]/10000 if not desmat_diss.empty else 0
                area_tis = tis_diss.area.iloc[0]/10000 if not tis_diss.empty else 0
                
                # Prepara dados raster
                img_raster, raster_bounds, matriz = preparar_raster(ras_file, poligono, color_map)
            
            # Mostra métricas
            mostrar_metricas(area_des, area_emb, area_tis)
            
            # Mostra gráfico se habilitado
            if mostrar_graficos:
                mostrar_grafico_distribuicao(area_des, area_emb, area_tis)
            
            # Cria e exibe o mapa
            m = criar_mapa_base(poligono)
            
            if img_raster is not None:
                ImageOverlay(
                    image=img_raster, 
                    bounds=raster_bounds, 
                    name="MapBiomas", 
                    opacity=opacidade,
                    interactive=True
                ).add_to(m)
            
            # Adiciona camadas vetoriais
            add_layer(desmat_gdf, "Área Desmatada", "red", m, tooltip_fields=['area_ha'])
            add_layer(embargo_gdf, "Área Embargada", "orange", m, tooltip_fields=['numero', 'area_ha'])
            add_layer(tis_gdf, "Terras Indígenas", "yellow", m, tooltip_fields=['nome', 'area_ha'])
            
            folium.LayerControl().add_to(m)
            st_folium(m, width="100%", height=600)
            
            # Seção do relatório PDF
            st.markdown("### 📄 Relatório PDF")
            pdf = gerar_pdf(desmat_diss, embargo_diss, tis_diss, matriz)
            st.download_button(
                "📥 Baixar PDF", 
                data=pdf, 
                file_name="relatorio_espacial.pdf", 
                mime="application/pdf",
                help="Clique para baixar o relatório completo em PDF"
            )
            
        except Exception as e:
            st.error(f"Ocorreu um erro durante o processamento: {str(e)}")
            logger.exception("Erro durante o processamento principal:")
    else:
        st.info("📂 Faça o upload do polígono e do raster para iniciar a análise.")

if __name__ == "__main__":
    main()


