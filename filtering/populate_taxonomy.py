#!/usr/bin/env python3
"""
Standalone script to populate the Taxonomies collection in MongoDB with data from taxonomy.json.

This script implements Step 1.3 of the embedding project and is completely self-contained
with no dependencies on other project files.
"""

import json
import logging
import os
import sys
import argparse
from typing import Dict, List, Any
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TaxonomyImporter:
    """Handles importing taxonomy data from JSON to MongoDB."""
    
    def __init__(self, mongo_uri=None, db_name=None):
        """Initialize the importer with database connection."""
        # Get MongoDB connection details from environment variables or use defaults
        self.mongo_uri = mongo_uri or os.getenv("MONGO_URI", "mongodb://localhost:27017/")
        self.db_name = db_name or os.getenv("DB_NAME", "documedica")
        self.collection_name = "Taxonomies"
        
        # Connect to MongoDB
        try:
            self.client = MongoClient(self.mongo_uri, serverSelectionTimeoutMS=5000)
            # Test the connection
            self.client.admin.command("ismaster")
            self.db = self.client[self.db_name]
            logger.info(f"Connected to MongoDB: {self.mongo_uri}")
            logger.info(f"Using database: {self.db_name}")
        except ConnectionFailure as e:
            logger.error(f"Database connection failed: {e}")
            raise
        
    def load_taxonomy_data(self, file_path: str) -> List[Dict[str, Any]]:
        """Load taxonomy data from JSON file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('taxonomy', [])
        except FileNotFoundError:
            logger.error(f"Taxonomy file not found: {file_path}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in taxonomy file: {e}")
            raise
    
    def validate_taxonomy_node(self, node: Dict[str, Any]) -> bool:
        """Validate a single taxonomy node."""
        required_fields = ['_id', 'display_name', 'facet', 'parent_id', 'children_ids']
        
        for field in required_fields:
            if field not in node:
                logger.error(f"Missing required field '{field}' in node {node.get('_id', 'unknown')}")
                return False
        
        # Validate data types
        if not isinstance(node['_id'], str) or not node['_id'].strip():
            logger.error(f"Invalid _id in node: {node['_id']}")
            return False
            
        if not isinstance(node['display_name'], str) or not node['display_name'].strip():
            logger.error(f"Invalid display_name in node: {node['_id']}")
            return False
            
        if not isinstance(node['facet'], str) or not node['facet'].strip():
            logger.error(f"Invalid facet in node: {node['_id']}")
            return False
            
        if not isinstance(node['children_ids'], list):
            logger.error(f"Invalid children_ids in node: {node['_id']}")
            return False
        
        return True
    
    def validate_taxonomy_references(self, nodes: List[Dict[str, Any]]) -> bool:
        """Validate that all parent_id and children_ids references exist."""
        node_ids = {node['_id'] for node in nodes}
        
        for node in nodes:
            # Validate parent_id
            if node['parent_id'] is not None and node['parent_id'] not in node_ids:
                logger.error(f"Invalid parent_id '{node['parent_id']}' in node '{node['_id']}'")
                return False
            
            # Validate children_ids
            for child_id in node['children_ids']:
                if child_id not in node_ids:
                    logger.error(f"Invalid child_id '{child_id}' in node '{node['_id']}'")
                    return False
        
        return True
    
    def check_duplicates(self, nodes: List[Dict[str, Any]]) -> bool:
        """Check for duplicate _id values."""
        node_ids = [node['_id'] for node in nodes]
        duplicates = set([x for x in node_ids if node_ids.count(x) > 1])
        
        if duplicates:
            logger.error(f"Duplicate _id values found: {duplicates}")
            return False
        
        return True
    
    def create_indexes(self):
        """Create necessary indexes for the Taxonomies collection."""
        collection = self.db[self.collection_name]
        
        # Create index on parent_id for efficient parent-child queries
        collection.create_index("parent_id")
        logger.info("Created index on parent_id")
        
        # Create index on facet for filtering by category
        collection.create_index("facet")
        logger.info("Created index on facet")
        
        # Create compound index on facet and parent_id for common query patterns
        collection.create_index([("facet", 1), ("parent_id", 1)])
        logger.info("Created compound index on facet and parent_id")
    
    def import_taxonomy(self, file_path: str, drop_existing: bool = False) -> bool:
        """Import taxonomy data from JSON file to MongoDB."""
        try:
            # Load data
            logger.info(f"Loading taxonomy data from {file_path}")
            nodes = self.load_taxonomy_data(file_path)
            logger.info(f"Loaded {len(nodes)} taxonomy nodes")
            
            # Validate data
            logger.info("Validating taxonomy data")
            for node in nodes:
                if not self.validate_taxonomy_node(node):
                    return False
            
            if not self.validate_taxonomy_references(nodes):
                return False
            
            if not self.check_duplicates(nodes):
                return False
            
            logger.info("Taxonomy data validation passed")
            
            # Get collection
            collection = self.db[self.collection_name]
            
            # Drop existing collection if requested
            if drop_existing:
                logger.info(f"Dropping existing {self.collection_name} collection")
                collection.drop()
            
            # Create indexes
            self.create_indexes()
            
            # Insert data in batches
            batch_size = 100
            total_inserted = 0
            
            for i in range(0, len(nodes), batch_size):
                batch = nodes[i:i + batch_size]
                try:
                    result = collection.insert_many(batch, ordered=False)
                    batch_count = len(result.inserted_ids)
                    total_inserted += batch_count
                    logger.info(f"Inserted batch {i//batch_size + 1}: {batch_count} nodes")
                except Exception as e:
                    logger.error(f"Error inserting batch {i//batch_size + 1}: {e}")
                    return False
            
            logger.info(f"Successfully imported {total_inserted} taxonomy nodes")
            return True
            
        except Exception as e:
            logger.error(f"Error importing taxonomy: {e}")
            return False
    
    def verify_import(self) -> bool:
        """Verify that the import was successful."""
        try:
            collection = self.db[self.collection_name]
            total_count = collection.count_documents({})
            
            logger.info(f"Verification: {total_count} documents in {self.collection_name}")
            
            # Check a few sample documents
            sample_docs = list(collection.find().limit(3))
            for doc in sample_docs:
                logger.info(f"Sample document: {doc['_id']} - {doc['display_name']}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error verifying import: {e}")
            return False

def main():
    """Main function to run the taxonomy import."""
    MONGO_URI = "mongodb://localhost:27017/"
    DB_NAME = "documedica"
    COLLECTION_NAME = "Taxonomies"
    TAXONOMY_FILE = "taxonomy.json"
    DROP_EXISTING = True
    
    # Initialize importer
    try:
        importer = TaxonomyImporter(mongo_uri=MONGO_URI, db_name=DB_NAME)
        importer.collection_name = COLLECTION_NAME
    except Exception as e:
        logger.error(f"Failed to initialize database connection: {e}")
        sys.exit(1)
    
    # Import taxonomy
    success = importer.import_taxonomy(TAXONOMY_FILE, drop_existing=DROP_EXISTING)
    
    if success:
        logger.info("Taxonomy import completed successfully")
        
        # Verify import
        if importer.verify_import():
            logger.info("Import verification successful")
        else:
            logger.error("Import verification failed")
            sys.exit(1)
    else:
        logger.error("Taxonomy import failed")
        sys.exit(1)

if __name__ == "__main__":
    main()