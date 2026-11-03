import urllib.request
import json
import os

# Crear directorio local si no existe
os.makedirs('data', exist_ok=True)
ruta_destino = os.path.join('data', 'mexico_estados.json')

# URL oficial verificada con la geometría de las 32 entidades federativas
url_oficial = "https://raw.githubusercontent.com/codeforgermany/click_that_hood/main/public/data/mexico.geojson"

print("🔄 Descargando capa espacial de México desde repositorio verificado...")

try:
    req = urllib.request.Request(url_oficial, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read().decode('utf-8'))
        
    with open(ruta_destino, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        
    print(f"✅ Capa GeoJSON descargada exitosamente en: {ruta_destino}")
except Exception as e:
    print(f"❌ Error durante la descarga: {e}")