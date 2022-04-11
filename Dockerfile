FROM apache/airflow:2.2.5

WORKDIR ${AIRFLOW_HOME}

COPY dags/ dags/