#!/usr/bin/env bash
# Actualiza el subdominio DuckDNS de Civix con la Elastic IP de la EC2.
# Lee credenciales de duckdns.env (ignorado por Git) y evita poner el token
# en los argumentos visibles del proceso curl o en la salida del comando.
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="${DUCKDNS_CONFIG:-${SCRIPT_DIR}/duckdns.env}"

if [[ ! -r "${CONFIG_FILE}" ]]; then
  echo "No encuentro ${CONFIG_FILE}. Copia duckdns.env.example y completa el token." >&2
  exit 2
fi

# Este archivo es una configuración local privada, creada por el operador.
set -a
# shellcheck disable=SC1090
source "${CONFIG_FILE}"
set +a

# Tolera archivos editados en Windows y guardados con CRLF.
DUCKDNS_SUBDOMAIN="${DUCKDNS_SUBDOMAIN//$'\r'/}"
DUCKDNS_TOKEN="${DUCKDNS_TOKEN//$'\r'/}"
CIVIX_ELASTIC_IP="${CIVIX_ELASTIC_IP:-}"
CIVIX_ELASTIC_IP="${CIVIX_ELASTIC_IP//$'\r'/}"

: "${DUCKDNS_SUBDOMAIN:?Define DUCKDNS_SUBDOMAIN en duckdns.env}"
: "${DUCKDNS_TOKEN:?Define DUCKDNS_TOKEN en duckdns.env}"

if [[ ! "${DUCKDNS_SUBDOMAIN}" =~ ^[a-zA-Z0-9-]+$ ]]; then
  echo "DUCKDNS_SUBDOMAIN debe ser solo el prefijo (sin .duckdns.org)." >&2
  exit 2
fi
if [[ ! "${DUCKDNS_TOKEN}" =~ ^[a-zA-Z0-9_-]+$ ]]; then
  echo "El token DuckDNS tiene caracteres inesperados; verifica duckdns.env." >&2
  exit 2
fi

IP_PARAM=""
if [[ -n "${CIVIX_ELASTIC_IP:-}" ]]; then
  if [[ ! "${CIVIX_ELASTIC_IP}" =~ ^([0-9]{1,3}\.){3}[0-9]{1,3}$ ]]; then
    echo "CIVIX_ELASTIC_IP no parece una dirección IPv4." >&2
    exit 2
  fi
  IFS='.' read -r -a OCTETS <<< "${CIVIX_ELASTIC_IP}"
  for OCTET in "${OCTETS[@]}"; do
    if (( 10#${OCTET} > 255 )); then
      echo "CIVIX_ELASTIC_IP contiene un octeto fuera del rango IPv4." >&2
      exit 2
    fi
  done
  IP_PARAM="&ip=${CIVIX_ELASTIC_IP}"
fi

# La URL con token viaja por stdin de curl, no como argumento del proceso.
RESPONSE="$(curl --fail --silent --show-error --config - <<CURL_CONFIG
url = "https://www.duckdns.org/update?domains=${DUCKDNS_SUBDOMAIN}&token=${DUCKDNS_TOKEN}${IP_PARAM}"
CURL_CONFIG
)"

if [[ "${RESPONSE}" != OK* ]]; then
  echo "DuckDNS no confirmó la actualización: ${RESPONSE}" >&2
  exit 1
fi

echo "DuckDNS actualizado: ${DUCKDNS_SUBDOMAIN}.duckdns.org -> ${CIVIX_ELASTIC_IP:-IP pública detectada}"
