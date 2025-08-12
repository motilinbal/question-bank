from pymongo import MongoClient

# Connect to MongoDB - assuming local instance and database name 'test'.
# Adjust the connection string and database name as needed for your environment.
client = MongoClient('mongodb://localhost:27017/')
db = client['documedica']  # Replace 'test' with your actual database name if different

def format_taxonomy_to_text():
    """
    Queries the 'Taxonomies' collection, builds the hierarchy, and returns a formatted, indented string.
    Groups 'system' facets as main hierarchical content and others as standalone.
    Preserves order of children_ids for child nodes.
    Sorts root nodes alphabetically by display_name within their groups for consistency.
    """
    # Query all documents from the Taxonomies collection
    taxonomy_docs = list(db.Taxonomies.find({}))

    # Create a dictionary for quick lookups by _id
    nodes_map = {doc["_id"]: doc for doc in taxonomy_docs}

    # Find all root nodes (parent_id is None)
    roots = [doc for doc in taxonomy_docs if doc["parent_id"] is None]

    # Group roots: main (facet == 'system') and standalone (others)
    main_roots = [r for r in roots if r['facet'] == 'system']
    standalone_roots = [r for r in roots if r['facet'] != 'system']

    # Sort each group alphabetically by display_name
    main_roots.sort(key=lambda x: x['display_name'])
    standalone_roots.sort(key=lambda x: x['display_name'])

    # This will hold the final formatted lines
    output_lines = ["// Part of the generated rulebook text", "..."]

    def build_hierarchy_for_node(node, level=0):
        """
        Recursive function to build indented lines for a node and its children.
        """
        # Indentation: two spaces per level
        indent = "  " * level
        line = f"{indent}- {node['facet']}: {node['display_name']}"
        output_lines.append(line)

        # Recurse for children, preserving the order in children_ids
        if node.get("children_ids"):
            for child_id in node["children_ids"]:
                child = nodes_map.get(child_id)
                if child:
                    build_hierarchy_for_node(child, level + 1)

    # Build main hierarchical sections
    for root in main_roots:
        build_hierarchy_for_node(root)

    # Add standalone section if any
    if standalone_roots:
        output_lines.append("// Standalone facets")
        for root in standalone_roots:
            build_hierarchy_for_node(root)

    return "\n".join(output_lines)

# Execute and print the formatted text
if __name__ == "__main__":
    formatted_text = format_taxonomy_to_text()
    print(formatted_text)