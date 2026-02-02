#!/usr/bin/env python
"""
Migration script to:
1. Remove the 'responsabile' field from all documents in the activities collection
2. Add the admin user 'marko' to the 'responsabili' array of all documents

This script connects directly to MongoDB without using Django.
"""

import os
from dotenv import load_dotenv
from pymongo import MongoClient

# Load environment variables
load_dotenv()

# Get MongoDB connection details
MONGODB_URI = (
    os.getenv("MONGODB_URI")
    or os.getenv("MONGO_URI")
    or "mongodb://localhost:27017/?directConnection=true"
)
MONGO_DB = os.getenv("MONGO_DB") or os.getenv("DB_NAME") or "analyst"


def get_marko_user_id(db):
    """Find the user 'marko' in the auth_user collection and return their _id as string."""
    user = db.auth_user.find_one({"username": "marko"})
    if user:
        return str(user["_id"])
    return None


def migrate_activities():
    """Perform the migration on the activities collection."""
    print(f"Connecting to MongoDB: {MONGODB_URI}")
    print(f"Database: {MONGO_DB}")

    client = MongoClient(MONGODB_URI)
    db = client[MONGO_DB]

    # Get marko's user ID
    marko_id = get_marko_user_id(db)
    if not marko_id:
        print("ERROR: User 'marko' not found in auth_user collection!")
        print("Available users:")
        for user in db.auth_user.find({}, {"username": 1, "_id": 1}):
            print(f"  - {user.get('username')} (id: {user['_id']})")
        client.close()
        return False

    print(f"Found user 'marko' with ID: {marko_id}")

    activities = db.activities

    # Count documents before migration
    total_docs = activities.count_documents({})
    docs_with_responsabile = activities.count_documents(
        {"responsabile_iniziativa": {"$exists": True}}
    )

    print("\nBefore migration:")
    print(f"  Total documents: {total_docs}")
    print(f"  Documents with 'responsabile_iniziativa' field: {docs_with_responsabile}")

    # Step 1: Remove the 'responsabile_iniziativa' field from all documents
    print("\nStep 1: Removing 'responsabile_iniziativa' field from all documents...")
    result_unset = activities.update_many({}, {"$unset": {"responsabile_iniziativa": ""}})
    print(f"  Modified {result_unset.modified_count} documents")

    # Step 2: Add marko to responsabili array (using $addToSet to avoid duplicates)
    print(f"\nStep 2: Adding 'marko' (ID: {marko_id}) to 'responsabili' array...")
    result_add = activities.update_many({}, {"$addToSet": {"responsabili": marko_id}})
    print(f"  Modified {result_add.modified_count} documents")

    # Verify the migration
    docs_with_responsabile_after = activities.count_documents(
        {"responsabile_iniziativa": {"$exists": True}}
    )
    docs_with_marko = activities.count_documents({"responsabili": marko_id})

    print("\nAfter migration:")
    print(f"  Documents with 'responsabile_iniziativa' field: {docs_with_responsabile_after}")
    print(f"  Documents with 'marko' in responsabili: {docs_with_marko}")

    client.close()
    print("\nMigration completed successfully!")
    return True


if __name__ == "__main__":
    migrate_activities()
