import subprocess
from tkinter.filedialog import askopenfilenames
from tkinter.simpledialog import askstring
import os

input_tiles = askopenfilenames(title="Select Shapefiles to Upload", filetypes=[("Shapefiles", "*.shp")])

schema = askstring(title="Schema Name", prompt="Enter the target schema name in PostGIS:")
tabela = askstring(title="Table Name", prompt="Enter the target table name in PostGIS:")

user =
host = 
password =
dbname =


ogr2ogr -nlt PROMOTE_TO_MULTI -append -lco GEOMETRY_NAME=GEOMETRY_NAME -f "postgreSQL" PG:"dbname=postgres host=localhost port=5432 user=postgres password=postgres" "D:\"UFPI_2024_2025\Webgis\Dados\car_ms\car_ms.shp\car_cod_imovel_MS-5000203-00C40A856ED948018A800407D0C602C9.shp" -nln public.car