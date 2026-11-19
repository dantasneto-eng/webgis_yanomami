import streamlit as st
import folium
import numpy as np
import os
import cv2
import pandas as pd
import geopandas as gpd
import plotly.express as px

from streamlit_folium import st_folium
from rasterio.io import MemoryFile
from rasterio.mask import mask
from folium.raster_layers import ImageOverlay
from zona_utm import calcular_utm
from utils import color_map, value_to_class

# UI Header
st.header('WebGIS')
st.subheader('SIG - Análise Espacial na Regularização Fundiária e Ambiental')
st.sidebar.title('Menu')

# File uploaders
poligono_subido = st.sidebar.file_uploader('Escolha o polígono a ser analisado (CAR/SIGEF)')
raster_subido = st.sidebar.file_uploader('Escolha o raster a ser analisado (Mapbiomas)')

# Data file paths (relative paths)
embargo_path = 'Urucui_embargos.parquet'
desmatamento_path = 'Urucui_prodes.parquet'
tis_path = 'dados/tis.parquet'

def load_gdf(path):
    return gpd.read_parquet(path)

@st.cache_resource
def abrir_embargo(uploaded_file=None):
    """Abre GeoDataFrame de embargos.

    uploaded_file: file-like (Streamlit upload) ou None. Se fornecido, tentamos ler dele.
    Caso contrário, tentamos ler do caminho `embargo_path`. Retorna GeoDataFrame vazio se nada disponível.
    """
    if uploaded_file is not None:
        return gpd.read_parquet(uploaded_file)
    if os.path.exists(embargo_path):
        return load_gdf(embargo_path)
    return gpd.GeoDataFrame()

@st.cache_resource
def abrir_desmatamento(uploaded_file=None):
    """Abre GeoDataFrame de desmatamento. Sem widgets aqui (accepts uploaded file)."""
    if uploaded_file is not None:
        return gpd.read_parquet(uploaded_file)
    if os.path.exists(desmatamento_path):
        return load_gdf(desmatamento_path)
    return gpd.GeoDataFrame()

@st.cache_resource
def abrir_tis(uploaded_file=None):
    """Abre GeoDataFrame de TIs. Sem widgets aqui (accepts uploaded file)."""
    if uploaded_file is not None:
        return gpd.read_parquet(uploaded_file)
    if os.path.exists(tis_path):
        return load_gdf(tis_path)
    return gpd.GeoDataFrame()

def drop_embargo_columns(gdf):
    drop_cols = [
        'nom_pessoa','cpf_cnpj_i','cpf_cnpj_s','end_pessoa',
        'des_bairro','num_cep','num_fone','data_tad','dat_altera',
        'data_cadas','data_geom','dt_carga'
    ]
    return gdf.drop(columns=[c for c in drop_cols if c in gdf.columns], errors='ignore')

def dissolve_and_project(gdf, epsg):
    if not gdf.empty:
        gdf = gdf.dissolve(by=None)
        gdf = gdf.to_crs(epsg=epsg)
    return gdf

def overlay_and_sjoin(gdf, poly):
    joined = gpd.sjoin(gdf, poly, how='inner', predicate='intersects')
    overlaid = gpd.overlay(joined, poly, how='intersection')
    return overlaid

def render_map(area_desmat, area_embargo, area_tis, poligono_analise, out_image, bounds, resized_image):
    m = folium.Map(location=[15, 52], zoom_start=8, tiles='Esri World Imagery')
    ImageOverlay(
        image=resized_image,
        bounds=bounds,
        opacity=0.7,
        name='Mapbiomas coleção 9',
        interactive=True,
        cross_origin=False,
        zindex=1
    ).add_to(m)

    # Fit bounds to polygon
    minx, miny, maxx, maxy = poligono_analise.total_bounds
    m.fit_bounds([[miny, minx], [maxy, maxx]])

    def style_function(color):
        return {'fillColor': color, 'color': 'black', 'weight': 1, 'fillOpacity': 0.6}

    if not area_desmat.empty:
        folium.GeoJson(area_desmat, name='Área desmatada', style_function=lambda x: style_function('red')).add_to(m)
    if not area_embargo.empty:
        folium.GeoJson(area_embargo, name='Área embargada', style_function=lambda x: style_function('orange')).add_to(m)
    if not area_tis.empty:
        folium.GeoJson(area_tis, name='Área de TIs', style_function=lambda x: style_function('yellow')).add_to(m)

    folium.LayerControl().add_to(m)
    st_folium(m, width='100%')

def show_area_stats(area_desmat, area_embargo, area_tis):
    col1, col2, col3 = st.columns(3)
    with col1:
        st.subheader('Área desmatada (ha)')
        val = round(area_desmat.area.iloc[0] / 10000, 2) if not area_desmat.empty else 0
        st.subheader(str(val))
    with col2:
        st.subheader('Área embargada (ha)')
        val = round(area_embargo.area.iloc[0] / 10000, 2) if not area_embargo.empty else 0
        st.subheader(str(val))
    with col3:
        st.subheader('Área de TIs (ha)')
        val = round(area_tis.area.iloc[0] / 10000, 2) if not area_tis.empty else 0
        st.subheader(str(val))

def show_raster_stats(out_image):
    unique_values, counts = np.unique(out_image, return_counts=True)
    st.write('Áreas em hectares:')
    for value, count in zip(unique_values, counts):
        class_name = value_to_class.get(value, "Unknown")
        area_ha = (count * 900) / 10000
        st.write(f"{class_name}, {area_ha:.2f} (ha)")

def show_graphs(df_desmat, df_embargo, df_ti):
    col1_graf, col2_graf, col3_graf, col4_graf = st.columns(4)
    tema_grafico = col1_graf.selectbox('Selecione o tema do gráfico', options=['Desmatamento', 'Embargo', 'Terras Indígenas'])
    tipo_grafico = col2_graf.selectbox('Selecione o tipo de gráfico', options=['box', 'bar', 'line', 'scatter', 'violin', 'histogram'], index=5)

    df_map = {
        'Desmatamento': df_desmat,
        'Embargo': df_embargo,
        'Terras Indígenas': df_ti
    }
    df_analisado = df_map[tema_grafico]

    if not df_analisado.empty:
        x_val = col3_graf.selectbox('Selecione o eixo x do gráfico', options=df_analisado.columns, index=min(6, len(df_analisado.columns)-1))
        y_val = col4_graf.selectbox('Selecione o eixo y do gráfico', options=df_analisado.columns, index=min(5, len(df_analisado.columns)-1))
        plot_func = getattr(px, tipo_grafico)
        plot = plot_func(df_analisado, x=x_val, y=y_val)
        st.plotly_chart(plot, use_container_width=True)
    else:
        st.info("Não há dados para o gráfico selecionado.")

# Main workflow
if poligono_subido and raster_subido:
    poligono_analise = gpd.read_file(poligono_subido)

    # Se os arquivos locais não existirem, permitir upload via sidebar (fora das funções cacheadas)
    uploaded_embargo = None
    uploaded_desmat = None
    uploaded_tis = None
    if not os.path.exists(embargo_path):
        uploaded_embargo = st.sidebar.file_uploader('Envie o arquivo de embargos (Urucui_embargos.parquet)', type=['parquet'], key='upload_embargo')
    if not os.path.exists(desmatamento_path):
        uploaded_desmat = st.sidebar.file_uploader('Envie o arquivo de desmatamento (Urucui_prodes.parquet)', type=['parquet'], key='upload_desmat')
    if not os.path.exists(tis_path):
        uploaded_tis = st.sidebar.file_uploader('Envie o arquivo de TIs (tis.parquet)', type=['parquet'], key='upload_tis')

    # Carrega dados usando os arquivos enviados (se houver) ou arquivos locais
    try:
        gdf_embargo = abrir_embargo(uploaded_embargo)
    except Exception as e:
        st.error(f'Erro ao carregar embargos: {e}')
        gdf_embargo = gpd.GeoDataFrame()

    try:
        gdf_desmat = abrir_desmatamento(uploaded_desmat)
    except Exception as e:
        st.error(f'Erro ao carregar desmatamento: {e}')
        gdf_desmat = gpd.GeoDataFrame()

    try:
        gdf_ti = abrir_tis(uploaded_tis)
    except Exception as e:
        st.error(f'Erro ao carregar TIs: {e}')
        gdf_ti = gpd.GeoDataFrame()

    gdf_embargo = drop_embargo_columns(gdf_embargo)

    entrada_embargo = overlay_and_sjoin(gdf_embargo, poligono_analise)
    entrada_desmat = overlay_and_sjoin(gdf_desmat, poligono_analise)
    entrada_tis = overlay_and_sjoin(gdf_ti, poligono_analise)

    epsg_arquivo = calcular_utm(poligono_analise)

    area_embargo = dissolve_and_project(entrada_embargo, epsg_arquivo)
    area_desmat = dissolve_and_project(entrada_desmat, epsg_arquivo)
    area_tis = dissolve_and_project(entrada_tis, epsg_arquivo)

    if area_embargo.empty:
        st.warning("Nenhuma sobreposição com embargos foi encontrada.")
    if area_desmat.empty:
        st.warning("Nenhum dado de desmatamento encontrado na área analisada.")
    if area_tis.empty:
        st.warning("Nenhum dado de TIs encontrado na área analisada.")

    # Raster analysis
    with MemoryFile(raster_subido.getvalue()) as memfile:
        with memfile.open() as src:
            if poligono_analise.crs != src.crs:
                poligono_analise = poligono_analise.to_crs(src.crs)
            geometries = poligono_analise.geometry
            out_image, out_transform = mask(src, geometries, crop=True)
            out_image = out_image[0]
            height, width = out_image.shape
            rgb_image = np.zeros((height, width, 4), dtype=np.uint8)
            for value, color in color_map.items():
                rgb_image[out_image == value] = color
            resized_image = cv2.resize(rgb_image, (width, height), interpolation=cv2.INTER_NEAREST)
            min_x, min_y = out_transform * (0, 0)
            max_x, max_y = out_transform * (width, height)
            bounds = [[min_y, min_x], [max_y, max_x]]

    show_area_stats(area_desmat, area_embargo, area_tis)
    render_map(area_desmat, area_embargo, area_tis, poligono_analise, out_image, bounds, resized_image)
    show_raster_stats(out_image)

    # Prepare DataFrames for graphs
    df_desmat = pd.DataFrame(entrada_desmat).drop(columns=['geometry'], errors='ignore') if not entrada_desmat.empty else pd.DataFrame()
    df_embargo = pd.DataFrame(entrada_embargo).drop(columns=['geometry'], errors='ignore') if not entrada_embargo.empty else pd.DataFrame()
    df_ti = pd.DataFrame(entrada_tis).drop(columns=['geometry'], errors='ignore') if not entrada_tis.empty else pd.DataFrame()
    show_graphs(df_desmat, df_embargo, df_ti)
else:
    st.warning('Suba os arquivos para iniciar o WebGIS')
