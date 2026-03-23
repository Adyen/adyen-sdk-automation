#!/usr/bin/env bash
set -euo pipefail

OUTPUT_FILE="${1:?Usage: $0 <output-file>}"

ALL_PROJECTS='["java","php","node","python","ruby","go","dotnet"]'
ALL_SERVICES='["checkout","capital","payout","recurring","binlookup","posmobile","paymentsapp","disputes","storedvalue","payment","management","balancecontrol","legalentitymanagement","balanceplatform","transfers","dataprotection","sessionauthentication","configurationwebhooks","acswebhooks","reportwebhooks","transferwebhooks","transactionwebhooks","managementwebhooks","disputewebhooks","negativebalancewarningwebhooks","balancewebhooks","tokenizationwebhooks","relayedauthorizationwebhooks"]'

if [ -z "${INPUT_PROJECTS:-}" ]; then
  echo "projects=$ALL_PROJECTS" >> "$OUTPUT_FILE"
else
  JSON=$(echo "$INPUT_PROJECTS" | tr ',' '\n' | jq -Rsc 'split("\n") | map(gsub("\\s+";" ") | ltrimstr(" ") | rtrimstr(" ")) | map(select(length > 0))')
  INVALID=$(echo "$JSON" | jq -r --argjson allowed "$ALL_PROJECTS" '[.[] | select(. as $item | ($allowed | index($item)) == null)] | join(", ")')
  if [ -n "$INVALID" ]; then
    echo "::error::Invalid project(s): $INVALID. Allowed values: $(echo "$ALL_PROJECTS" | jq -r 'join(", ")')"
    exit 1
  fi
  echo "projects=$JSON" >> "$OUTPUT_FILE"
fi

if [ -z "${INPUT_SERVICES:-}" ]; then
  echo "services=$ALL_SERVICES" >> "$OUTPUT_FILE"
else
  JSON=$(echo "$INPUT_SERVICES" | tr ',' '\n' | jq -Rsc 'split("\n") | map(gsub("\\s+";" ") | ltrimstr(" ") | rtrimstr(" ")) | map(select(length > 0))')
  INVALID=$(echo "$JSON" | jq -r --argjson allowed "$ALL_SERVICES" '[.[] | select(. as $item | ($allowed | index($item)) == null)] | join(", ")')
  if [ -n "$INVALID" ]; then
    echo "::error::Invalid service(s): $INVALID. Allowed values: $(echo "$ALL_SERVICES" | jq -r 'join(", ")')"
    exit 1
  fi
  echo "services=$JSON" >> "$OUTPUT_FILE"
fi
