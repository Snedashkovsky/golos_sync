from pymongo import MongoClient, ASCENDING

class Connector:
  def __init__(self):
    pass

  def save_block(self, block):
    pass

  def find_last_block(self):
    pass

  def update_last_block(self, last_block):
    pass

  def save_instance(self, instance):
    pass

  def get_instances_to_update(self, collection):
    pass

class MongoConnector(Connector):
  def __init__(self, database, host="localhost:27017"):
    self.client = MongoClient(host)
    self.database = self.client[database]
    self.create_indices()

  def create_indices(self):
    self.database.reblog.create_index([('blockid', ASCENDING), ('permlink', ASCENDING), ('account', ASCENDING)])
    self.database.follow.create_index([('blockid', ASCENDING), ('follower', ASCENDING), ('following', ASCENDING)])

  def save_block(self, block):
    try:
      collection = block.get_collection()
      dictionary = block.to_dict()
      query = block.get_query()
      block.use_connector(self)
      self.database[collection].update(query, {"$set": dictionary}, upsert=True)    
    except:
      print("Exception in block {} ({})".format(block.block_id, block.to_dict())) 

  def find_last_block(self):
    init = self.database.status.find_one({'_id': 'height_all_tsx'})
    if (init):
      return init['value']
    else: 
      return 1

  def update_last_block(self, last_block):
    self.database.status.update({'_id': 'height_all_tsx'}, {"$set": {'value': last_block}}, upsert=True)

  # TODO join method with save_block
  def save_instance(self, instance):
    dictionary = instance.to_dict()
    instance_id = instance.get_id()
    collection = instance.get_collection()
    instance.use_connector(self)
    self.database[collection].update({'_id': instance_id}, {"$set": dictionary}, upsert=True)

  def get_instances_to_update(self, collection):
    return self.database[collection].find({'need_update': True})