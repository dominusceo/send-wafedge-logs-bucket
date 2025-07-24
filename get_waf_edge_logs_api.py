# Goal: Send logs from OCI WAF Edge to specific bucket  
# Autor: Ricardo Carrillo <ricardo.d.carrillo@oracle.com>
import oci
import sys
import json
from oci.signer import Signer
from datetime import datetime, timedelta
from urllib.parse import urlencode

VALID_LOG_TYPES = {"ACCESS", "DETECT", "BLOCK"}

def get_waf_edge_logs_and_upload(region, waf_policy_ocid, compartment_ocid, log_type,
                                  webapp_domain, bucket_name, namespace, custom_endpoint):

    if log_type.upper() not in VALID_LOG_TYPES:
        print(json.dumps({
            "error": "Invalid log type",
            "valid_values": list(VALID_LOG_TYPES)
        }, indent=2))
        sys.exit(1)

    config = oci.config.from_file()
    config["region"] = region

    signer = Signer(
        tenancy=config["tenancy"],
        user=config["user"],
        fingerprint=config["fingerprint"],
        private_key_file_location=config["key_file"],
        pass_phrase=config.get("pass_phrase")
    )

    ## Obtener los logs desde WAF Edge
    base_endpoint = f"https://waas.{region}.oraclecloud.com"
    resource_path = f"/20181116/waasPolicies/{waf_policy_ocid}/wafLogs"
    now = datetime.utcnow()
    today = datetime.utcnow().date()
    yesterday = today - timedelta(days=1)
    time_start = datetime.combine(yesterday, datetime.min.time()).isoformat() + "Z"
    time_end = datetime.combine(today, datetime.min.time()).isoformat() + "Z"

    query_params = {
        "logType": log_type.upper(),
        "timeObservedGreaterThanOrEqualTo": time_start,
        "timeObservedLessThan": time_end,
        "compartmentId": compartment_ocid
    }

    query_string = urlencode(query_params)
    full_url = f"{base_endpoint}{resource_path}?{query_string}"

    session = oci._vendor.requests.Session()
    response = session.get(full_url, auth=signer)

    if response.status_code != 200:
        print(json.dumps({
            "error": f"HTTP {response.status_code}",
            "details": response.text
        }, indent=2))
        return

    logs = response.json()
    json_data = json.dumps(logs, indent=2)

    ## Formato del prefijo: webapp_domain/YYYY/MM/DD/
    prefix = f"{webapp_domain}/{now.strftime('%Y')}/{now.strftime('%m')}/{now.strftime('%d')}"
    filename = f"{log_type.lower()}-logs-{now.strftime('%Y%m%dT%H%M%S')}.json"
    object_name = f"{prefix}/{filename}"

    ## Subir al bucket
    object_storage_client = oci.object_storage.ObjectStorageClient(config, signer=signer)
    object_storage_client.base_client.endpoint = custom_endpoint

    put_resp = object_storage_client.put_object(
        namespace_name=namespace,
        bucket_name=bucket_name,
        object_name=object_name,
        put_object_body=json_data.encode("utf-8"),
        content_type="application/json"
    )

    print(json.dumps({
        "message": "Logs subidos correctamente",
        "bucket": bucket_name,
        "object_name": object_name,
        "etag": put_resp.headers.get("etag"),
        "url": f"{custom_endpoint}/n/{namespace}/b/{bucket_name}/o/{object_name.replace('/', '%2F')}"
    }, indent=2))

if __name__ == "__main__":
    if len(sys.argv) != 8:
        print("Uso:")
        print("python get_waf_edge_logs_upload_custom.py <region> <waf_policy_ocid> <compartment_ocid> <log_type> <webapp_domain> <bucket_name> <namespace>")
        print("Ejemplo:")
        print("python get_waf_edge_logs_upload_custom.py eu-frankfurt-1 ocid1.waaspolicy... ocid1.compartment... ACCESS mywebapp mybucket mynamespace")
        sys.exit(1)

    region = sys.argv[1]
    waf_ocid = sys.argv[2]
    compartment_ocid = sys.argv[3]
    log_type = sys.argv[4]
    webapp_domain = sys.argv[5]
    bucket_name = sys.argv[6]
    namespace = sys.argv[7]
    custom_endpoint = f"https://objectstorage.{region}.oraclecloud.com"

    get_waf_edge_logs_and_upload(region, waf_ocid, compartment_ocid, log_type,
                                  webapp_domain, bucket_name, namespace, custom_endpoint)

