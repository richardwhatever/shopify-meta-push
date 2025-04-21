import json
import sys
from collections import Counter

def display_metafields(json_file):
    try:
        # Read the JSON file
        with open(json_file, 'r') as f:
            data = json.load(f)
        
        # Extract metafields from the new format
        # Check if metafields is a dictionary with a "missing" key
        if isinstance(data.get('metafields'), dict) and 'missing' in data['metafields']:
            metafields = data['metafields']['missing']
        else:
            metafields = data.get('metafields', [])
            
        # Extract metaobjects - handle both missing and changed
        missing_metaobjects = []
        changed_metaobjects = []
        
        if isinstance(data.get('metaobjects'), dict):
            if 'missing' in data['metaobjects']:
                missing_metaobjects = data['metaobjects']['missing']
            if 'changed' in data['metaobjects']:
                changed_metaobjects = data['metaobjects']['changed']
        else:
            # Fallback to original behavior
            metaobjects = data.get('metaobjects', [])
        
        # Count total metafields and metaobjects
        total_metafields = len(metafields)
        total_missing_metaobjects = len(missing_metaobjects)
        total_changed_metaobjects = len(changed_metaobjects)
        
        # Count metafields by owner type
        owner_type_counts = Counter()
        for metafield in metafields:
            try:
                owner_type = metafield.get('ownerType', 'Unknown')
                owner_type_counts[owner_type] += 1
            except Exception as e:
                print(f"Error processing metafield: {str(e)}")
                continue
        
        # Group metafields by owner type
        metafields_by_owner = {}
        for metafield in metafields:
            try:
                owner_type = metafield.get('ownerType', 'Unknown')
                if owner_type not in metafields_by_owner:
                    metafields_by_owner[owner_type] = []
                metafields_by_owner[owner_type].append(metafield)
            except Exception as e:
                print(f"Error grouping metafield: {str(e)}")
                continue
        
        # Print summary at the beginning
        print("=== SUMMARY ===")
        print(f"Total metafields: {total_metafields}")
        print(f"Total missing metaobjects: {total_missing_metaobjects}")
        print(f"Total changed metaobjects: {total_changed_metaobjects}")
        print("\nMetafields by owner type:")
        for owner_type, count in owner_type_counts.items():
            print(f"  {owner_type}: {count}")
        print("===============")
        
        # Print metafields grouped by owner type
        print("\nMetafields by owner type:")
        for owner_type, fields in metafields_by_owner.items():
            print(f"\n{owner_type}:")
            for field in fields:
                try:
                    name = field.get('name', '')
                    field_type = field.get('type', '')
                    namespace = field.get('namespace', '')
                    key = field.get('key', '')
                    print(f"  - {name} ({field_type}) - {namespace}.{key}")
                except Exception as e:
                    print(f"  - Error displaying metafield: {str(e)}")
                    continue
        
        # Print missing metaobjects summary
        if missing_metaobjects:
            print(f"\nMissing Metaobjects ({total_missing_metaobjects}):")
            for metaobject in missing_metaobjects:
                try:
                    # Check if metaobject is a dictionary
                    if isinstance(metaobject, dict):
                        name = metaobject.get('name', '')
                        metaobject_type = metaobject.get('type', '')
                        print(f"  - {name} ({metaobject_type})")
                        
                        # Print field definitions if available
                        field_definitions = metaobject.get('fieldDefinitions', [])
                        if field_definitions:
                            print("    Fields:")
                            for field in field_definitions:
                                try:
                                    field_name = field.get('name', '')
                                    field_type = field.get('type', '')
                                    field_key = field.get('key', '')
                                    print(f"      - {field_name} ({field_type}) - key: {field_key}")
                                except Exception as e:
                                    print(f"      - Error displaying field: {str(e)}")
                                    continue
                    else:
                        # Handle case where metaobject is a string or other type
                        print(f"  - {metaobject}")
                except Exception as e:
                    print(f"  - Error displaying metaobject: {str(e)}")
                    continue
        
        # Print changed metaobjects summary
        if changed_metaobjects:
            print(f"\nChanged Metaobjects ({total_changed_metaobjects}):")
            for metaobject in changed_metaobjects:
                try:
                    # Check if metaobject is a dictionary
                    if isinstance(metaobject, dict):
                        # Try to get name from source if available
                        source = metaobject.get('source', {})
                        name = source.get('name', '')
                        metaobject_type = source.get('type', '')
                        
                        # If no source, try to get from id
                        if not name and 'id' in metaobject:
                            id_parts = metaobject['id'].split('::')
                            if len(id_parts) > 1:
                                name = id_parts[1]
                        
                        print(f"  - {name} ({metaobject_type})")
                        
                        # Print changes if available
                        diff = metaobject.get('diff', {})
                        if diff:
                            values_changed = diff.get('values_changed', {})
                            if values_changed:
                                print("    Changes:")
                                for key, change in values_changed.items():
                                    try:
                                        old_value = change.get('old_value', '')
                                        new_value = change.get('new_value', '')
                                        print(f"      - {key}: {old_value} → {new_value}")
                                    except Exception as e:
                                        print(f"      - Error displaying change: {str(e)}")
                                        continue
                    else:
                        # Handle case where metaobject is a string or other type
                        print(f"  - {metaobject}")
                except Exception as e:
                    print(f"  - Error displaying changed metaobject: {str(e)}")
                    continue
        
        # Print summary at the end
        print("\n=== SUMMARY ===")
        print(f"Total metafields: {total_metafields}")
        print(f"Total missing metaobjects: {total_missing_metaobjects}")
        print(f"Total changed metaobjects: {total_changed_metaobjects}")
        print("\nMetafields by owner type:")
        for owner_type, count in owner_type_counts.items():
            print(f"  {owner_type}: {count}")
        print("===============")
        
    except FileNotFoundError:
        print(f"Error: File '{json_file}' not found.")
    except json.JSONDecodeError:
        print(f"Error: '{json_file}' is not a valid JSON file.")
    except Exception as e:
        print(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    # Default to "metafield_diff.json" if no argument is provided
    if len(sys.argv) > 1:
        json_file = sys.argv[1]
    else:
        json_file = "metafield_diff.json"
        print(f"No file specified, using default: {json_file}")
    
    display_metafields(json_file) 