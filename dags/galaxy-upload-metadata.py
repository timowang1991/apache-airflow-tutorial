from datetime import datetime, timedelta

from airflow import DAG
# from airflow.operators.docker_operator import DockerOperator
from airflow.providers.cncf.kubernetes.operators.kubernetes_pod import KubernetesPodOperator
from airflow.kubernetes.secret import Secret
from airflow.operators.python_operator import PythonOperator

from airflow.models import Variable

import json

def printSomething():
    return 'print something'

with DAG(
    'galaxy-upload-metadata',

    default_args={
        'depends_on_past': False,
        'retries': 1,
        'retry_delay': timedelta(minutes=5),
    },
    description='galaxy-upload-metadata DAG',
    schedule_interval=timedelta(minutes=1),
    start_date=datetime(2022, 4, 1),
    catchup=False,
) as dag:

    content = json.dumps({
        'hello': 'world'
    })

    t1 = PythonOperator(
        task_id='print_something',
        python_callable=printSomething
    )

    # t2 = DockerOperator(
    #     task_id='upload',
    #     image='gcr.io/nft-galaxy/galaxy-metadata-upload:test',
    #     command=f'node src/services/google-cloud functional-tests/0407.json \'{content}\'',
    #     environment={
    #         'GALAXY_METADATA_UPLOAD_CREDENTIALS': Variable.get('GALAXY_METADATA_UPLOAD_CREDENTIALS'),
    #         'CLOUD_STORAGE_METADATA_BUCKET_NAME': 'galaxy-metadata'
    #     },
    #     network_mode='bridge',
    # )

    # t3 = DockerOperator(
    #     task_id='try_template',
    #     image='node:16-alpine3.12',
    #     command='node -e "console.log(\'===================\',process.env)"',
    #     environment={
    #         'TEST_TEMPLATE': '{{ti.xcom_pull(task_ids="print_something")}}'
    #     },
    #     network_mode='bridge'
    # )

    # secret = Secret(
    #     # Expose the secret as environment variable.
    #     deploy_type='env',
    #     # The name of the environment variable, since deploy_type is `env` rather
    #     # than `volume`.
    #     deploy_target='GALAXY_METADATA_UPLOAD_CREDENTIALS',
    #     # Name of the Kubernetes Secret
    #     secret='galaxy-airflow-secret',
    #     # Key of a secret stored in this Secret object
    #     key='GALAXY_METADATA_UPLOAD_CREDENTIALS'
    # )

    # need to run `kubectl create secret generic galaxy-airflow-service-account --from-file=service.account.json -n airflow` ahead
    secret = Secret(
        deploy_type='volume',
        # Path where we mount the secret as volume
        deploy_target='/var/secrets/google',
        # Name of Kubernetes Secret
        secret='galaxy-airflow-service-account',
        # Key in the form of service account file name
        key='service-account.json'
    )

    t2 = KubernetesPodOperator(
        task_id='upload',
        name='upload',
        namespace='airflow',
        image='gcr.io/nft-galaxy/galaxy-metadata-upload:test',
        cmds=['node', 'src/services/google-cloud', 'functional-tests/0407.json', f'\'{content}\''],
        secrets=[secret],
        env_vars={
            'CLOUD_STORAGE_METADATA_BUCKET_NAME': 'galaxy-metadata',
            # 'GALAXY_METADATA_UPLOAD_CREDENTIALS': Variable.get('GALAXY_METADATA_UPLOAD_CREDENTIALS'),
            'GOOGLE_APPLICATION_CREDENTIALS': '/var/secrets/google/service-account.json'
        }
    )

    t3 = KubernetesPodOperator(
        task_id='try_template',
        name='try_template',
        namespace='airflow',
        image='node:16-alpine3.12',
        cmds=['node', '-e', 'console.log(\'===================\',process.env)'],
        env_vars={
            'TEST_TEMPLATE': '{{ti.xcom_pull(task_ids="print_something")}}'
        }
    )

    t1 >> t3
