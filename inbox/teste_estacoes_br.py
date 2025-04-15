import zipfile
import xml.etree.ElementTree as ET
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
import matplotlib.pyplot as plt

# 1. Extrair dados do arquivo KMZ
kmz_file = 'aeronet_sites_v3.kmz'

with zipfile.ZipFile(kmz_file, 'r') as z:
    kml_filename = next((name for name in z.namelist() if name.endswith('.kml')), None)
    if not kml_filename:
        raise ValueError("Nenhum arquivo KML encontrado no KMZ.")
    kml_data = z.read(kml_filename)

# Utilizar a namespace conforme definido no arquivo KML
ns = {'kml': 'http://earth.google.com/kml/2.0'}
root = ET.fromstring(kml_data)

# 2. Extrair nome e coordenadas das estações
stations_data = []
placemarks = root.findall('.//kml:Placemark', ns)
for placemark in placemarks:
    # Nome da estação
    name_elem = placemark.find('kml:name', ns)
    station_name = name_elem.text.strip() if name_elem is not None and name_elem.text is not None else "Sem nome"
    
    # Coordenadas da estação
    point_elem = placemark.find('kml:Point', ns)
    if point_elem is not None:
        coordinates_elem = point_elem.find('kml:coordinates', ns)
        if coordinates_elem is not None:
            coords_str = coordinates_elem.text.strip()  # formato: "lon,lat,alt"
            parts = coords_str.split(',')
            if len(parts) >= 2:
                try:
                    lon = float(parts[0])
                    lat = float(parts[1])
                    stations_data.append({'name': station_name, 'lon': lon, 'lat': lat})
                except ValueError:
                    continue

df_stations = pd.DataFrame(stations_data)
print("Estações extraídas:", len(df_stations))

# 3. Criar GeoDataFrame com as estações (assumindo o sistema de referência EPSG:4326)
gdf_stations = gpd.GeoDataFrame(
    df_stations, 
    geometry=gpd.points_from_xy(df_stations.lon, df_stations.lat),
    crs="EPSG:4326"
)

# 4. Carregar shapefile do Brasil
shapefile_zip = 'ne_110m_admin_0_countries.zip'
with zipfile.ZipFile(shapefile_zip, 'r') as z:
    shapefile_dir = shapefile_zip.replace('.zip', '')
    z.extractall(shapefile_dir)

shapefile_path = f"{shapefile_dir}/ne_110m_admin_0_countries.shp"
world = gpd.read_file(shapefile_path)
gdf_brazil = world[world['ADMIN'] == "Brazil"]

# 5. Filtrar as estações que estão dentro do território brasileiro (junção espacial)
# A partir do GeoPandas 0.10, usa-se o parâmetro 'predicate'
stations_in_brazil = gpd.sjoin(gdf_stations, gdf_brazil, predicate='within', how='inner')
stations_in_brazil_names = stations_in_brazil['name'].unique()
print("Estações no Brasil:")
for name in stations_in_brazil_names:
    print(name)

# 6. Plot the map
fig, ax = plt.subplots(figsize=(12, 12))

# Plot the boundaries of all countries
world.boundary.plot(ax=ax, edgecolor='gray', linewidth=0.5, label='Country Boundaries')

# Plot the boundaries of Brazil
gdf_brazil.boundary.plot(ax=ax, edgecolor='black', linewidth=1.5, label='Brazil Boundary')

# Plot all stations
gdf_stations.plot(ax=ax, marker='o', color='blue', markersize=5, label='Stations (Global)')

# Highlight stations within Brazil
stations_in_brazil.plot(ax=ax, marker='o', color='red', markersize=5, label='Stations in Brazil')

# Add legend and details
plt.legend(loc='upper right', fontsize='small', title='Legend')
plt.title("Aeronet Stations and Country Boundaries", fontsize=16)
plt.xlabel("Longitude", fontsize=12)
plt.ylabel("Latitude", fontsize=12)
plt.grid(color='lightgray', linestyle='--', linewidth=0.5)
plt.tight_layout()

# Save the map as an image
plt.savefig("map_stations_brazil_formal.png")
# plt.show()  # Removed to avoid non-interactive environment error
