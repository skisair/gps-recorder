import os

from datetime import datetime, timezone, timedelta
from azure.cosmosdb.table.tableservice import TableService

JST = timezone(timedelta(hours=+9), 'JST')

STORAGE_ACCOUNT_NAME = 'devstoreaccount1'
STORAGE_ACCOUNT_KEY = 'Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw=='
CONMECTION_STRING = \
    'DefaultEndpointsProtocol=http;' \
    'AccountName=devstoreaccount1;' \
    'AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;' \
    'BlobEndpoint=http://127.0.0.1:10000/devstoreaccount1;' \
    'QueueEndpoint=http://127.0.0.1:10001/devstoreaccount1;' \
    'TableEndpoint=http://127.0.0.1:10002/devstoreaccount1;'

if __name__ == '__main__':
    table_service = TableService(connection_string=CONMECTION_STRING)

    __ = table_service.create_table('tasktable')
    task = {'PartitionKey': 'tasksSeattle', 'RowKey': '001',
            'description': 'Take out the trash', 'priority': 200}
    table_service.insert_entity('tasktable', task)

    tasks = table_service.query_entities('tasktable', filter="PartitionKey eq 'tasksSeattle'")
    for task in tasks:
        print(task.description)
        print(task.priority)

    table_service.delete_table('tasktable')
