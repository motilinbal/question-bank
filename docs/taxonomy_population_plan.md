# Taxonomy Population Plan for Step 1.3

## Overview
This document outlines the detailed plan for populating the Taxonomies collection in MongoDB with the validated taxonomy data from `taxonomy.json`.

## Analysis Completed

### Taxonomy Data Structure
The `taxonomy.json` file contains a hierarchical structure with the following key properties for each node:
- `_id`: Unique string identifier (e.g., "cardio_shock_hypovolemic")
- `display_name`: Human-readable name (e.g., "Hypovolemic Shock")
- `facet`: Category/type of the node (e.g., "subtype", "condition", "system")
- `parent_id`: Reference to parent node (null for top-level nodes)
- `children_ids`: Array of child node IDs

### MongoDB Schema Design
Based on the guidelines in `embedding_project.md`, the Taxonomies collection will use this schema:

```json
{
  "_id": "cardio_shock_hypovolemic",
  "display_name": "Hypovolemic Shock",
  "facet": "subtype",
  "parent_id": "cardio_shock",
  "children_ids": []
}
```

## Implementation Plan

### 1. Python Script Structure (`populate_taxonomy.py`)

```python
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
        self.db_name = db_name or os.getenv("DB_NAME", "documedica_refactored")
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
        
        # Create unique index on _id
        collection.create_index("_id", unique=True)
        logger.info("Created unique index on _id")
        
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
    import argparse
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Import taxonomy data into MongoDB')
    parser.add_argument('--file', '-f', default='taxonomy.json',
                       help='Path to taxonomy JSON file (default: taxonomy.json)')
    parser.add_argument('--mongo-uri', '-u',
                       help='MongoDB connection URI (default: from MONGO_URI env var or mongodb://localhost:27017/)')
    parser.add_argument('--db-name', '-d',
                       help='MongoDB database name (default: from DB_NAME env var or documedica_refactored)')
    parser.add_argument('--collection', '-c', default='Taxonomies',
                       help='MongoDB collection name (default: Taxonomies)')
    parser.add_argument('--no-drop', action='store_true',
                       help='Do not drop existing collection before import')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose logging')
    
    args = parser.parse_args()
    
    # Configure logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Initialize importer
    try:
        importer = TaxonomyImporter(mongo_uri=args.mongo_uri, db_name=args.db_name)
        importer.collection_name = args.collection
    except Exception as e:
        logger.error(f"Failed to initialize database connection: {e}")
        sys.exit(1)
    
    # Import taxonomy
    success = importer.import_taxonomy(args.file, drop_existing=not args.no_drop)
    
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
```

### 2. Standalone Script Features

The script is completely self-contained with the following features:

- **No external dependencies**: Does not import from any project files
- **Environment variable support**: Reads MongoDB connection details from environment variables
- **Command-line arguments**: Supports custom MongoDB URI, database name, and file path
- **Default values**: Provides sensible defaults for all configuration options

### 3. Key Features of the Implementation

#### Data Validation
- Validates all required fields are present
- Checks data types for each field
- Validates parent-child references
- Detects duplicate IDs

#### Error Handling
- Comprehensive logging throughout the process
- Graceful handling of database connection issues
- Batch processing with error recovery
- Clear error messages for troubleshooting

#### Performance Optimization
- Batch insertion for better performance
- Ordered=False to continue on duplicate key errors
- Appropriate indexes for common query patterns

#### Verification
- Counts imported documents
- Samples and logs imported data
- Validates data integrity after import

### 4. Usage Instructions

1. **Basic Import**:
   ```bash
   python populate_taxonomy.py
   ```

2. **Import with Custom MongoDB URI**:
   ```bash
   python populate_taxonomy.py --mongo-uri "mongodb://user:password@host:port/"
   ```

3. **Import with Custom Database and Collection**:
   ```bash
   python populate_taxonomy.py --db-name "my_database" --collection "my_taxonomies"
   ```

4. **Import with Custom JSON File**:
   ```bash
   python populate_taxonomy.py --file "/path/to/taxonomy.json"
   ```

5. **Import Without Dropping Existing Collection**:
   ```bash
   python populate_taxonomy.py --no-drop
   ```

6. **Import with Verbose Logging**:
   ```bash
   python populate_taxonomy.py --verbose
   ```

7. **Import with Logging to File**:
   ```bash
   python populate_taxonomy.py > taxonomy_import.log 2>&1
   ```

8. **Verify Import**:
   ```bash
   python -c "
   from pymongo import MongoClient
   client = MongoClient('mongodb://localhost:27017/')
   db = client['documedica_refactored']
   collection = db['Taxonomies']
   print(f'Total documents: {collection.count_documents({})}')
   print(f'Sample document: {collection.find_one()}')
   "
   ```

### 5. Testing Strategy

1. **Unit Testing**:
   - Test data validation functions
   - Test reference validation
   - Test duplicate detection

2. **Integration Testing**:
   - Test with a small subset of data
   - Test database connection and insertion
   - Test index creation

3. **Full Import Test**:
   - Run with complete dataset
   - Verify all documents are imported
   - Check query performance

### 6. Future Enhancements

1. **Update Mode**:
   - Add functionality to update existing taxonomy without full re-import
   - Handle schema changes gracefully

2. **Export Functionality**:
   - Add ability to export taxonomy from MongoDB to JSON
   - Support different export formats

3. **CLI Arguments**:
   - Add command-line arguments for file path, collection name, etc.
   - Support dry-run mode

4. **Progress Reporting**:
   - Add progress bar for large imports
   - Send notifications on completion

## Next Steps

1. Implement the standalone `populate_taxonomy.py` script as outlined above
2. Test the script with a subset of the taxonomy data
3. Run the full import and verify the results
4. Document the process for future reference

## Key Benefits of the Standalone Approach

- **No Dependencies**: The script can be run independently without any project files
- **Environment Variables**: Uses standard environment variables for configuration
- **Command-Line Flexibility**: Supports various command-line options for different use cases
- **Self-Contained**: All necessary imports and functionality are included in a single file
- **Reusable**: Can be easily copied and used in other projects or environments