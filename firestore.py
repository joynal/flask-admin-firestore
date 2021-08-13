import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore

# Use the application default credentials
cred = credentials.Certificate('/Users/joynal/.gcloud/kamata-dev.json')
firebase_admin.initialize_app(cred, {
  'projectId': 'kamata-dev',
})

db = firestore.client()

test_coll = db.collection('demo').document('entities').collection('orders')

# create new user
# new_user = test_coll.document()
# new_user.set({
#     'name': 'Adhar',
#     'age': 34
# })

# Update a user
# user = test_coll.document('EjnCMVEhGQF2HwNtISw4')
# user.set({
#     'name': 'Red',
#     'age': 24
# })

# Delete a user
# user = test_coll.document('EjnCMVEhGQF2HwNtISw4').delete()

# read documents
docs = test_coll.stream()
for doc in docs:
    print(f'{doc.id} => {doc.to_dict()}')

# read nested collections
# nested_collections = db.collection('demo').document('entities').collections()

# for collection in nested_collections:
#     print('collection => ', collection.id)
    # for doc in collection.stream():
    #     print(f'{doc.id} => {doc.to_dict()}')


# nested_collections = db.collections()

# for collection in nested_collections:
#     print('collection => ', collection.id)
#     for doc in collection.stream():
#         print(f'{doc.id} => {doc.to_dict()}')