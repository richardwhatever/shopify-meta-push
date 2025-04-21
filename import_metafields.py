import requests
import argparse
import json
import os
import sys
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

GRAPHQL_ENDPOINT = "/admin/api/2025-01/graphql.json"

def graphql_request(store_url, token, query, variables):
    endpoint = f"https://{store_url}{GRAPHQL_ENDPOINT}"
    headers = {
        "Content-Type": "application/json",
        "X-Shopify-Access-Token": token
    }

    try:
        response = requests.post(endpoint, headers=headers, json={"query": query, "variables": variables})
        response.raise_for_status() 
        result = response.json()

        if "errors" in result:
            # Check for access denied errors
            for error in result["errors"]:
                if "ACCESS_DENIED" in str(error):
                    print("\n❌ Access Denied Error:")
                    print(f"   {error['message']}")
                    print("\n🔑 Required Access Scopes:")
                    print("   Your API token needs the following access scopes:")
                    print("   - write_products (for PRODUCT metafields)")
                    print("   - write_customers (for CUSTOMER metafields)")
                    print("   - write_product_variants (for PRODUCTVARIANT metafields)")
                    print("   - write_metaobjects (for metaobjects)")
                    print("\n📚 Documentation: https://shopify.dev/api/usage/access-scopes")
                    print("\n💡 Tip: Create a new custom app in your Shopify admin with the required access scopes.")
                    sys.exit(1)
            
            raise Exception(f"GraphQL error: {result['errors']}")
        return result["data"]
    except requests.exceptions.RequestException as e:
        raise Exception(f"HTTP request failed: {str(e)}")
    except json.JSONDecodeError:
        raise Exception("Invalid JSON response from server")

def check_metafield_exists(store_url, token, namespace, key):
    query = """
    query GetMetafieldDefinition($namespace: String!, $key: String!) {
      metafieldDefinition(namespace: $namespace, key: $key) {
        id
      }
    }
    """
    
    try:
        result = graphql_request(store_url, token, query, {
            "namespace": namespace,
            "key": key
        })
        return result.get("metafieldDefinition") is not None
    except Exception:
        return False

def create_metafield_definition(store_url, token, metafield):
    # First check if the metafield already exists
    if check_metafield_exists(store_url, token, metafield["namespace"], metafield["key"]):
        print(f"⚠️ Metafield {metafield['namespace']}::{metafield['key']} already exists, skipping creation")
        return {"userErrors": []}
    
    mutation = """
    mutation CreateMetafieldDefinition($definition: MetafieldDefinitionInput!) {
      metafieldDefinitionCreate(definition: $definition) {
        createdDefinition {
          id
          name
          key
        }
        userErrors {
          field
          message
        }
      }
    }
    """

    input_payload = {
        "namespace": metafield["namespace"],
        "key": metafield["key"],
        "name": metafield.get("name", ""),
        "description": metafield.get("description", ""),
        "type": metafield["type"],
        "ownerType": metafield["ownerType"],
        "validations": metafield.get("validations", [])
    }

    result = graphql_request(store_url, token, mutation, {"definition": input_payload})
    return result["metafieldDefinitionCreate"]

def update_metafield_definition(store_url, token, metafield):
    mutation = """
    mutation UpdateMetafieldDefinition($id: ID!, $definition: MetafieldDefinitionUpdateInput!) {
      metafieldDefinitionUpdate(id: $id, definition: $definition) {
        metafieldDefinition {
          id
          name
          key
        }
        userErrors {
          field
          message
        }
      }
    }
    """

    input_payload = {
        "name": metafield.get("name", ""),
        "description": metafield.get("description", ""),
        "type": metafield["type"],
        "ownerType": metafield["ownerType"],
        "validations": metafield.get("validations", [])
    }

    # First, we need to get the ID of the existing metafield definition
    query = """
    query GetMetafieldDefinitionId($namespace: String!, $key: String!) {
      metafieldDefinition(namespace: $namespace, key: $key) {
        id
      }
    }
    """
    
    try:
        # Get the ID first
        id_result = graphql_request(store_url, token, query, {
            "namespace": metafield["namespace"],
            "key": metafield["key"]
        })
        
        if not id_result.get("metafieldDefinition"):
            raise Exception(f"Metafield definition {metafield['namespace']}::{metafield['key']} not found")
            
        definition_id = id_result["metafieldDefinition"]["id"]
        
        # Then update using the ID
        result = graphql_request(store_url, token, mutation, {
            "id": definition_id,
            "definition": input_payload
        })
        return result["metafieldDefinitionUpdate"]
    except Exception as e:
        raise Exception(f"Failed to update metafield definition: {str(e)}")

def check_metaobject_exists(store_url, token, type_name):
    query = """
    query GetMetaobjectDefinition($type: String!) {
      metaobjectDefinition(type: $type) {
        id
      }
    }
    """
    
    try:
        result = graphql_request(store_url, token, query, {
            "type": type_name
        })
        return result.get("metaobjectDefinition") is not None
    except Exception:
        return False

def is_reserved_metaobject_type(type_name):
    """Check if a metaobject type is reserved by Shopify (starts with 'shopify--')"""
    return type_name.startswith("shopify--")

def create_metaobject_definition(store_url, token, metaobject):
    # Check if this is a reserved type
    if is_reserved_metaobject_type(metaobject["type"]):
        print(f"⚠️ Metaobject type '{metaobject['type']}' is reserved by Shopify and cannot be created by custom apps")
        return {"userErrors": []}
    
    # Generate a new type name based on the original name
    new_type = f"custom_{metaobject['name'].lower().replace(' ', '_')}"
    
    mutation = """
    mutation CreateMetaobjectDefinition($definition: MetaobjectDefinitionCreateInput!) {
      metaobjectDefinitionCreate(definition: $definition) {
        metaobjectDefinition {
          id
          name
          type
        }
        userErrors {
          field
          message
        }
      }
    }
    """
    
    # Convert field definitions to the format expected by the API
    field_definitions = []
    for field in metaobject.get("fieldDefinitions", []):
        field_def = {
            "name": field["name"],
            "key": field["key"],
            "type": field["type"]
        }
        
        # Add validations if present
        if "validations" in field and field["validations"]:
            field_def["validations"] = []
            for validation in field["validations"]:
                # Skip reference validations as they require existing metaobject definitions
                if validation["name"] == "reference":
                    print(f"⚠️ Skipping reference validation for field {field['name']} as it requires existing metaobject definitions")
                    continue
                    
                # Handle special case for file_type_options which is a JSON string
                if validation["name"] == "file_type_options":
                    try:
                        # Parse the JSON string to get the actual array
                        value_array = json.loads(validation["value"])
                        # Convert array to comma-separated string
                        field_def["validations"].append({
                            "name": validation["name"],
                            "value": ",".join(value_array)
                        })
                    except json.JSONDecodeError:
                        # If parsing fails, use the original string
                        field_def["validations"].append(validation)
                else:
                    field_def["validations"].append(validation)
        
        field_definitions.append(field_def)
    
    input_payload = {
        "name": metaobject["name"],
        "type": new_type,
        "fieldDefinitions": field_definitions
    }
    
    result = graphql_request(store_url, token, mutation, {"definition": input_payload})
    return result["metaobjectDefinitionCreate"]

def main():
    parser = argparse.ArgumentParser(description="Import metafield and metaobject definitions into a Shopify store")
    parser.add_argument("--target-store", help="Target Shopify store (e.g. mystore.myshopify.com)")
    parser.add_argument("--target-token", help="Admin API token")
    parser.add_argument("--input", default="metafield_diff.json", help="Input file from comparison step")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without making changes")
    parser.add_argument("--force", action="store_true", help="Force creation even if items already exist")
    parser.add_argument("--prefix", default="custom_", help="Prefix to use for new metaobject types")

    args = parser.parse_args()
    
    # Get store URL from args or environment variable
    store_url = args.target_store or os.getenv("SHOPIFY_TARGET_STORE")
    if not store_url:
        raise Exception("Missing target store. Provide via --target-store or set SHOPIFY_TARGET_STORE in .env")
    
    # Get token from args or environment variable
    token = args.target_token or os.getenv("SHOPIFY_TARGET_TOKEN")
    if not token:
        raise Exception("Missing token. Provide via --target-token or set SHOPIFY_TARGET_TOKEN in .env")

    try:
        with open(args.input, 'r') as f:
            diff_data = json.load(f)
    except FileNotFoundError:
        raise Exception(f"Input file '{args.input}' not found")
    except json.JSONDecodeError:
        raise Exception(f"Invalid JSON in file '{args.input}'")

    # Process metafields
    metafields = diff_data.get("metafields", {})
    missing_metafields = metafields.get("missing", [])
    changed_metafields = metafields.get("changed", [])

    if args.dry_run:
        print("🔍 DRY RUN MODE - No changes will be made")
        print(f"\n📥 Would import {len(missing_metafields)} new metafield definitions:")
        for mf in missing_metafields:
            print(f"   - {mf['namespace']}::{mf['key']} ({mf['type']}) for {mf['ownerType']}")
        
        print(f"\n🔄 Would update {len(changed_metafields)} changed metafield definitions:")
        for mf in changed_metafields:
            print(f"   - {mf['namespace']}::{mf['key']} ({mf['type']}) for {mf['ownerType']}")
        
        # Process metaobjects
        metaobjects = diff_data.get("metaobjects", {})
        missing_metaobjects = metaobjects.get("missing", [])
        changed_metaobjects = metaobjects.get("changed", [])
        
        print(f"\n📥 Would import {len(missing_metaobjects)} new metaobject definitions:")
        for mo in missing_metaobjects:
            if is_reserved_metaobject_type(mo["type"]):
                print(f"   - {mo['name']} of type {mo['type']} (RESERVED - will be skipped)")
            else:
                new_type = f"{args.prefix}{mo['name'].lower().replace(' ', '_')}"
                print(f"   - {mo['name']} (will create as type '{new_type}')")
        
        print(f"\n🔄 Would update {len(changed_metaobjects)} changed metaobject definitions:")
        for mo in changed_metaobjects:
            if is_reserved_metaobject_type(mo["type"]):
                print(f"   - {mo['name']} of type {mo['type']} (RESERVED - will be skipped)")
            else:
                new_type = f"{args.prefix}{mo['name'].lower().replace(' ', '_')}"
                print(f"   - {mo['name']} (will create as type '{new_type}')")
        
        return

    print(f"📥 Importing {len(missing_metafields)} new metafield definitions...")
    for mf in missing_metafields:
        try:
            # Skip if already exists and not forcing
            if not args.force and check_metafield_exists(store_url, token, mf["namespace"], mf["key"]):
                print(f"⚠️ Metafield {mf['namespace']}::{mf['key']} already exists, skipping creation")
                continue
                
            response = create_metafield_definition(store_url, token, mf)
            if response["userErrors"]:
                print(f"❌ Error for {mf['namespace']}::{mf['key']}: {response['userErrors'][0]['message']}")
            else:
                print(f"✅ Created {mf['namespace']}::{mf['key']}")
        except Exception as e:
            print(f"❌ Failed to create {mf['namespace']}::{mf['key']}: {str(e)}")

    print(f"\n🔄 Updating {len(changed_metafields)} changed metafield definitions...")
    for mf in changed_metafields:
        try:
            response = update_metafield_definition(store_url, token, mf)
            if response["userErrors"]:
                print(f"❌ Error updating {mf['namespace']}::{mf['key']}: {response['userErrors'][0]['message']}")
            else:
                print(f"✅ Updated {mf['namespace']}::{mf['key']}")
        except Exception as e:
            print(f"❌ Failed to update {mf['namespace']}::{mf['key']}: {str(e)}")

    # Process metaobjects
    metaobjects = diff_data.get("metaobjects", {})
    missing_metaobjects = metaobjects.get("missing", [])
    changed_metaobjects = metaobjects.get("changed", [])

    print(f"\n📥 Importing {len(missing_metaobjects)} new metaobject definitions...")
    for mo in missing_metaobjects:
        try:
            # Skip if this is a reserved type
            if is_reserved_metaobject_type(mo["type"]):
                print(f"⚠️ Metaobject type '{mo['type']}' is reserved by Shopify and cannot be created by custom apps")
                continue
                
            response = create_metaobject_definition(store_url, token, mo)
            if response["userErrors"]:
                print(f"❌ Error for metaobject {mo['name']}: {response['userErrors'][0]['message']}")
            else:
                new_type = response["metaobjectDefinition"]["type"]
                print(f"✅ Created metaobject {mo['name']} with type {new_type}")
        except Exception as e:
            print(f"❌ Failed to create metaobject {mo['name']}: {str(e)}")

    print(f"\n🔄 Processing {len(changed_metaobjects)} changed metaobject definitions...")
    for mo in changed_metaobjects:
        try:
            # Skip if this is a reserved type
            if is_reserved_metaobject_type(mo["type"]):
                print(f"⚠️ Metaobject type '{mo['type']}' is reserved by Shopify and cannot be created by custom apps")
                continue
                
            # For changed metaobjects, we'll create a new one with the same name and fields
            response = create_metaobject_definition(store_url, token, mo)
            if response["userErrors"]:
                print(f"❌ Error for metaobject {mo['name']}: {response['userErrors'][0]['message']}")
            else:
                new_type = response["metaobjectDefinition"]["type"]
                print(f"✅ Created metaobject {mo['name']} with type {new_type}")
        except Exception as e:
            print(f"❌ Failed to create metaobject {mo['name']}: {str(e)}")

if __name__ == "__main__":
    main()
