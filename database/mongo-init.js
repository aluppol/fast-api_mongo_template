try {
  const env_vars = [
    'DB_NAME',
    'DB_API_USER',
    'DB_API_PASS',
    'DB_PEOPLE_COLLECTION_NAME',
  ]
  const errors = []
  for (const v of env_vars) {
    if (!process.env[v]) errors.push(`Missing env var ${v}`)
  }

  if (errors.length > 0) throw new Error(errors.join('\n'))
    
  
  db = db.getSiblingDB(process.env.DB_NAME);

  db.createUser({ // API service
    user: process.env.DB_API_USER,
    pwd: process.env.DB_API_PASS,
    roles: [{
      role: 'readWrite',
      db: process.env.DB_NAME
    }]
  });

  db.getCollection(process.env.DB_PEOPLE_COLLECTION_NAME).createIndex({'name': 1 }, {
    unique: true,
    partialFilterExpression: { 'deleted_at': { '$exists': false } }
  });  
} catch (e) {
  print(`Error during initialization: ${e}`);
}
