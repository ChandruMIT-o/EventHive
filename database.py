from pymongo import MongoClient

client = MongoClient("mongodb://localhost:27017/")

db = client['testing']

col = db['rameez']

col.delete_many({})

col.insert_one({
    'name':'rameez',
    'age':120,
    'state':'enlightment',
    'data':'inhuman'
})

col.insert_many([
    {
        'name':'mirsha',
        'age':20,
        'state':'stupid',
        'data':'bald'
    },
    {
        'name':'iesa',
        'age':2,
        'state':'goose',
        'data':'lazy'
    }
])

col.update_one({
    'name':'mirsha'
},  
{
    '$set':{
    'age':2
    }
})

content = col.find({'$gtr'})

for row in content:
    print(row)