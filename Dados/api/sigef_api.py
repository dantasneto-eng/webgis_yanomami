import requests
import geopandas as gpd
from shapely.geometry import shape

# Endpoints da API do SIGEF via ConectaGov
TOKEN_URL = "https://apigateway.conectagov.estaleiro.serpro.gov.br/oauth2/jwt-token"
SIGEF_URL = "https://apigateway.conectagov.estaleiro.serpro.gov.br/api-sigef-geo/v1/parcelas"

def obter_token(cert_path: str, cert_password: str) -> str:
    """
    Obtém token JWT a partir do certificado digital (.pem)
    """
    response = requests.post(
        TOKEN_URL,
        cert=(cert_path, cert_path),
        data={"grant_type": "client_credentials"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        verify=True
    )
    response.raise_for_status()
    return response.json()["access_token"]

def buscar_parcelas_por_municipio(token: str, municipio: str) -> gpd.GeoDataFrame:
    """
    Consulta parcelas SIGEF pelo nome do município e retorna como GeoDataFrame.
    """
    headers = {"Authorization": f"Bearer {token}"}
    params = {"municipio": municipio}

    response = requests.get(SIGEF_URL, headers=headers, params=params)
    response.raise_for_status()
    dados = response.json()

    if "features" not in dados or len(dados["features"]) == 0:
        print("⚠️ Nenhuma parcela encontrada.")
        return gpd.GeoDataFrame(columns=["geometry"], geometry="geometry", crs="EPSG:4674")

    geometries = [shape(f["geometry"]) for f in dados["features"]]
    atributos = [f["properties"] for f in dados["features"]]

    return gpd.GeoDataFrame(atributos, geometry=geometries, crs="EPSG:4674")




