import io
import json
import logging
from fdk import response
import subprocess
import sys
import os

# Ruta del script a ejecutar
script_path = "get_waf_edge_logs_api.py"

# Parámetros que quieres pasar al script
params = ["region", "waf_policy_ocid", "compartment_ocid", "log_type","webapp_domain","bucket_name","namespace"]

# Verifica si el archivo existe
if not os.path.isfile(script_path):
    print(f"Error: El archivo '{script_path}' no existe.")
    sys.exit(1)

# Construir el comando completo
command = ["python", script_path] + params

# Ejecutar el script con los parámetros
try:
    result = subprocess.run(command, capture_output=True, text=True, check=True)
    print("Salida del script:")
    print(result.stdout)
except subprocess.CalledProcessError as e:
    print("El script falló con el siguiente error:")
    print(e.stderr)
