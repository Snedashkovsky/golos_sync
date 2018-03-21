from datetime import datetime
from pistonapi.steemnoderpc import SteemNodeRPC
from pprint import pprint
from tqdm import tqdm
import json
import time
import sys
from connectors import MongoConnector
from blocks import create_block
import numpy as np
from celery import Celery
from time import sleep
from utils import get_connectors, RestartableTask
import click

MAX_BLOCKS_PER_TASK = 10000
MIN_BLOCKS_PER_TASK = 10

app = Celery('sync_all_tsx', broker='redis://localhost:6379/0')

def process_op(connector, opObj, block, blockid):
  """
    Creates and saves an object for an operation
  """
  opType = opObj[0]
  op = opObj[1]
  block_object = create_block(blockid, block, opType, op)
  connector.save_block(block_object)

def process_block(connector, block, blockid):
  """
    Processes all operations in block
  """
  for tx in block['transactions']:
    for opObj in tx['operations']:
      process_op(connector, opObj, block, blockid)

@app.task(base=RestartableTask)
def sync_tsx(connector, database, blocks):
  """
    Celery task that receives specified blocks' info from API
    and stores it into a database
  """
  rpc, connector = get_connectors(database, connector)
  for block_number in tqdm(blocks):
    block = rpc.get_block(block_number)
    process_block(connector, block, block_number)
  sys.stdout.flush()

@click.command()
@click.option('--connector', help='Type of connector (mongo/elasticsearch).', default='mongo')
@click.option('--database', help='Name of database', default='golos_transactions')
def sync_all_tsx(connector, database):
  """
    Creates multiple celery tasks to process blocks 
    after last processed block index saved to a database
  """
  connector_type = connector
  rpc, connector = get_connectors(database, connector)
  config = rpc.get_config()
  block_interval = config["STEEMIT_BLOCK_INTERVAL"]
  last_block = connector.find_last_block()
  current_block = last_block
  while True:
    blocks_per_task = MAX_BLOCKS_PER_TASK
    while current_block - last_block < blocks_per_task:
      sleep(block_interval)
      props = rpc.get_dynamic_global_properties()
      current_block = props['last_irreversible_block_num']
      blocks_per_task = max(blocks_per_task / 10, MIN_BLOCKS_PER_TASK)

    new_blocks = list(range(last_block, current_block))
    for chunk in tqdm(np.array_split(new_blocks, round((current_block - last_block) / blocks_per_task))):
      sync_tsx.delay(connector_type, database, chunk.tolist())
    connector.update_last_block(current_block)
    last_block = current_block

if __name__ == '__main__':
    sync_all_tsx()

