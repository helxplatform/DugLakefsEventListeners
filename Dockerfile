# The listener triggers Airflow with `airflow dags trigger`, which writes
# through the metadata DB, so it needs the Airflow CLI and the same DB
# drivers as the deployment it triggers. Basing on the roger image gets both
# and keeps the Airflow version in step with the scheduler -- a mismatch
# there means CLI and DB schema disagree.
ARG BASE_IMAGE=containers.renci.org/helxplatform/roger:develop
FROM ${BASE_IMAGE}

# flask is already present in the roger image; nothing else is needed.
COPY src/DugLakefsEventListeners /opt/dug-lakefs-listener/DugLakefsEventListeners

ENV PYTHONPATH=/opt/dug-lakefs-listener \
    PORT=8001

EXPOSE 8001

# gunicorn would be the production answer, but this serves a handful of
# webhook calls a day from inside the cluster; flask's server is adequate
# and one less dependency to track.
ENTRYPOINT ["python", "-m", "DugLakefsEventListeners.main"]
