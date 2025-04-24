import json
import argparse
from deepdiff import DeepDiff


def load_definitions(file_path):
    """
    Load both metafields and metaobjects from a JSON file.
    Returns a tuple of (metafields, metaobjects).
    """
    with open(file_path, 'r') as f:
        data = json.load(f)
        
        metafields = []
        metaobjects = []
        
        if isinstance(data, dict):
            # Handle structure with separate metafields and metaobjects keys
            if 'metafields' in data:
                metafields = data['metafields']
            if 'metaobjects' in data:
                metaobjects = data['metaobjects']
                
            # Handle structure with definitions key
            elif 'definitions' in data:
                # Try to separate metafields and metaobjects
                for item in data['definitions']:
                    if is_metaobject(item):
                        metaobjects.append(item)
                    else:
                        metafields.append(item)
                        
            # Try to find any key that contains a list of objects
            else:
                for key, value in data.items():
                    if isinstance(value, list) and value and isinstance(value[0], dict):
                        # Try to separate metafields and metaobjects
                        for item in value:
                            if is_metaobject(item):
                                metaobjects.append(item)
                            else:
                                metafields.append(item)
        elif isinstance(data, list):
            # Try to separate metafields and metaobjects
            for item in data:
                if is_metaobject(item):
                    metaobjects.append(item)
                else:
                    metafields.append(item)
        else:
            raise ValueError(f"Unexpected JSON structure in {file_path}.")
            
        return metafields, metaobjects


def is_metaobject(item):
    """
    Determine if an item is a metaobject definition.
    """
    return 'id' in item and 'MetaobjectDefinition' in item['id']


def normalize_metafield(metafield):
    """
    Strips non-essential fields and ensures a consistent format for comparison.
    """
    keys_to_keep = [
        "namespace", "key", "type", "name", "description",
        "ownerType", "visibleToStorefront", "validations"
    ]
    
    return {k: metafield.get(k) for k in keys_to_keep if k in metafield}


def normalize_metaobject(metaobject):
    """
    Strips non-essential fields and ensures a consistent format for comparison.
    """
    keys_to_keep = [
        "name", "type", "fieldDefinitions"
    ]
    
    return {k: metaobject.get(k) for k in keys_to_keep if k in metaobject}


def metafield_id(mf):
    """
    Generate a unique identifier for a metafield.
    """
    return f"{mf.get('namespace', '')}::{mf.get('key', '')}"


def metaobject_id(mo):
    """
    Generate a unique identifier for a metaobject.
    """
    return f"metaobject::{mo.get('name', '')}"


def compare_definitions(source_metafields, source_metaobjects, target_metafields, target_metaobjects):
    """
    Compare both metafields and metaobjects between source and target.
    """
    # Compare metafields
    source_mf_map = {metafield_id(mf): normalize_metafield(mf) for mf in source_metafields}
    target_mf_map = {metafield_id(mf): normalize_metafield(mf) for mf in target_metafields}
    
    missing_metafields = []
    changed_metafields = []
    
    for id_, source_mf in source_mf_map.items():
        if id_ not in target_mf_map:
            missing_metafields.append(source_mf)
        else:
            diff = DeepDiff(source_mf, target_mf_map[id_], ignore_order=True)
            if diff:
                changed_metafields.append({
                    "id": id_,
                    "diff": diff.to_dict(),
                    "source": source_mf,
                    "target": target_mf_map[id_]
                })
    
    # Compare metaobjects
    source_mo_map = {metaobject_id(mo): normalize_metaobject(mo) for mo in source_metaobjects}
    target_mo_map = {metaobject_id(mo): normalize_metaobject(mo) for mo in target_metaobjects}
    
    missing_metaobjects = []
    changed_metaobjects = []
    
    for id_, source_mo in source_mo_map.items():
        if id_ not in target_mo_map:
            missing_metaobjects.append(source_mo)
        else:
            diff = DeepDiff(source_mo, target_mo_map[id_], ignore_order=True)
            if diff:
                changed_metaobjects.append({
                    "id": id_,
                    "diff": diff.to_dict(),
                    "source": source_mo,
                    "target": target_mo_map[id_]
                })
    
    return {
        "metafields": {
            "missing": missing_metafields,
            "changed": changed_metafields
        },
        "metaobjects": {
            "missing": missing_metaobjects,
            "changed": changed_metaobjects
        }
    }


def main():
    parser = argparse.ArgumentParser(description="Compare metafield and metaobject definitions between two stores")
    parser.add_argument("--source", default="definitions_export_source.json", help="Source definitions JSON file")
    parser.add_argument("--target", default="definitions_export_target.json", help="Target definitions JSON file")
    parser.add_argument("--output", default="definitions_diff.json", help="Output file for differences")

    args = parser.parse_args()

    source_metafields, source_metaobjects = load_definitions(args.source)
    target_metafields, target_metaobjects = load_definitions(args.target)

    result = compare_definitions(
        source_metafields, source_metaobjects,
        target_metafields, target_metaobjects
    )

    with open(args.output, 'w') as f:
        json.dump(result, f, indent=2)

    print(f"✅ Comparison done.")
    print(f"📊 Metafields: {len(result['metafields']['missing'])} missing, {len(result['metafields']['changed'])} changed.")
    print(f"📊 Metaobjects: {len(result['metaobjects']['missing'])} missing, {len(result['metaobjects']['changed'])} changed.")
    print(f"📁 Output saved to {args.output}")


if __name__ == "__main__":
    main()
