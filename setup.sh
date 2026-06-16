#!/bin/bash
set -e

export AIRFLOW_HOME=~/rag_pipeline/airflow
echo 'export AIRFLOW_HOME=~/rag_pipeline/airflow' >> ~/.bashrc
source ~/.bashrc


if [ -f ~/rag_pipeline/.env ]; then
    # Automatically export all variables defined from this point forward
    set -o allexport
    source ~/rag_pipeline/.env
    # Turn off automatic exporting
    set +o allexport
else
    echo ".env file not found"
    exit 1
fi

airflow db migrate


databricks secrets create-scope rag_pipeline 2>/dev/null || echo "Scope already exists, skipping"
databricks secrets put-secret rag_pipeline GEMINI_API_KEY --string-value "$GEMINI_API_KEY"

airflow connections delete databricks_default 2>/dev/null || true
airflow connections add 'databricks_default' \
    --conn-type 'databricks' \
    --conn-host "$DATABRICKS_HOST" \
    --conn-password "$DATABRICKS_TOKEN"

airflow variables set embedding_model_name "sentence-transformers/all-MiniLM-L6-v2"
airflow variables set embedding_model_path "/Volumes/rag_pipeline/silver/models/all-MiniLM-L6-v2"
airflow variables set embedding_dimension "384"
airflow variables set embedding_model_hit_rate "0"
airflow variables set generation_model_name "google/flan-t5-base"
airflow variables set generation_model_score "0"

echo "Setup complete. Starting Airflow."
airflow standalone

