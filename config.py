import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

KNOWLEDGE_FOLDER = r"./workspaces/LLM-API-Testing-Framework/Document"
OPENAPI_YAML_PATH = r"./workspaces/LLM-API-Testing-Framework/testdata/sampleTest.yaml"
CSV_OUTPUT = r"./workspaces/LLM-API-Testing-Framework/reports/api_exec_report_consent.csv"
BASE_URL_OVERRIDE = "https://api.restful-api.dev"
VERIFY_SSL = False
REQUEST_TIMEOUT_SECS = 30
USE_LLM_VALIDATION = True
PERPLEXITY_MODEL = "sonar-pro"
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200
TOP_K = 3

