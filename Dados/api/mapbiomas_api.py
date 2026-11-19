import requests

API_URL = "https://plataforma.alerta.mapbiomas.org/api/v2/graphql"

def autenticar_mapbiomas(email: str, password: str) -> str:
    query = """
    mutation SignIn($email: String!, $password: String!) {
      signIn(email: $email, password: $password) {
        token
      }
    }
    """
    variables = {"email": email, "password": password}
    response = requests.post(API_URL, json={"query": query, "variables": variables})
    response.raise_for_status()
    return response.json()["data"]["signIn"]["token"]

def buscar_alertas(token: str, data_inicio="2023-01-01", data_fim="2023-12-31", limite=5) -> list:
    query = """
    query PublishedAlerts($filter: PublishedAlertsFilterInput) {
      publishedAlerts(filter: $filter) {
        alertCode
        areaHa
        detectedAt
        publishedAt
        alertBiomes
        alertStates
        alertCities
      }
    }
    """
    variables = {
        "filter": {
            "startDetectedAt": data_inicio,
            "endDetectedAt": data_fim,
            "limit": limite
        }
    }
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.post(API_URL, json={"query": query, "variables": variables}, headers=headers)
    response.raise_for_status()
    return response.json()["data"]["publishedAlerts"]



from api.mapbiomas_api import autenticar_mapbiomas, buscar_alertas

# Troque pelas suas credenciais da plataforma
token = autenticar_mapbiomas("marciocosta,geo@gmail.com", "Marcela@2009")
alertas = buscar_alertas(token, data_inicio="2024-01-01", data_fim="2024-12-31")

for alerta in alertas:
    st.write(f"{alerta['publishedAt']} — {alerta['areaHa']} ha — {', '.join(alerta['alertCities'])}")



