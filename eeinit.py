"""Earth Engine init.
Local: run `earthengine authenticate` once, then set GOOGLE_CLOUD_PROJECT.
CI:    also set EE_SERVICE_ACCOUNT_FILE to a service-account JSON key registered for Earth Engine."""
import json, os
try:
    import certifi
    os.environ.setdefault("SSL_CERT_FILE", certifi.where())
except ImportError:
    pass
import ee
_key = os.environ.get("EE_SERVICE_ACCOUNT_FILE")
if _key:
    ee.Initialize(ee.ServiceAccountCredentials(json.load(open(_key))["client_email"], _key),
                  project=os.environ["GOOGLE_CLOUD_PROJECT"])
else:
    ee.Initialize(project=os.environ["GOOGLE_CLOUD_PROJECT"])
