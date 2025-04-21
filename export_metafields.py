import requests
import argparse
import json
import os
import time
from dotenv import load_dotenv

# Load env variables
load_dotenv()

GRAPHQL_ENDPOINT = "/admin/api/2025-01/graphql.json"

# All valid owner types
OWNER_TYPES = [
    "COLLECTION",
    "CUSTOMER",
    "ORDER",
    "PRODUCT",
    "PRODUCTVARIANT",
    "VALIDATION"
    # --"API_PERMISSION",
    # --"ARTICLE",
    # --"BLOG",
    # --"CARTTRANSFORM",
    # --"COMPANY",
    # --"COMPANY_LOCATION",
    # --"DELIVERY_CUSTOMIZATION",
    # --"DISCOUNT",
    # --"DRAFTORDER",
    # --"FULFILLMENT_CONSTRAINT_RULE",
    # --"GIFT_CARD_TRANSACTION",
    # --"LOCATION",
    # --"MARKET",
    # --"ORDER_ROUTING_LOCATION_RULE",
    # --"PAGE",
    # --"PAYMENT_CUSTOMIZATION",
    # --"SELLING_PLAN",
    # --"SHOP",

]

def fetch_metaobject_definitions(store_url, access_token, verbose=False):
    endpoint = f"https://{store_url}{GRAPHQL_ENDPOINT}"
    headers = {
        "Content-Type": "application/json",
        "X-Shopify-Access-Token": access_token
    }

    query = """
    query {
      metaobjectDefinitions(first: 100) {
        edges {
          node {
            id
            name
            type
            fieldDefinitions {
              name
              key
              type {
                name
              }
              validations {
                name
                value
              }
            }
          }
        }
        pageInfo {
          hasNextPage
          endCursor
        }
      }
    }
    """

    print("\n📦 Fetching metaobject definitions...")
    all_definitions = []
    has_next_page = True
    after_cursor = None
    page_count = 0

    while has_next_page:
        try:
            variables = {
                "after": after_cursor
            } if after_cursor else {}

            if verbose:
                print(f"  - Requesting page {page_count + 1} for metaobjects (cursor: {after_cursor})")

            response = requests.post(
                endpoint,
                headers=headers,
                json={"query": query, "variables": variables},
                timeout=30
            )
            response.raise_for_status()
            data = response.json()

            if verbose:
                print(f"  - Raw API response: {json.dumps(data, indent=2)}")

            if "errors" in data:
                print(f"⚠️ Error fetching metaobjects: {json.dumps(data['errors'], indent=2)}")
                break

            defs = data['data']['metaobjectDefinitions']
            page_count += 1

            for edge in defs['edges']:
                node = edge['node']
                # Flatten the field definitions type
                for field in node['fieldDefinitions']:
                    field['type'] = field['type']['name']
                all_definitions.append(node)

            if verbose:
                print(f"  - Retrieved {len(defs['edges'])} definitions on page {page_count}")

            has_next_page = defs['pageInfo']['hasNextPage']
            after_cursor = defs['pageInfo']['endCursor']

            time.sleep(0.5)  # Rate limiting precaution

        except Exception as e:
            print(f"⚠️ Error fetching metaobjects: {str(e)}")
            break

    print(f"  ✓ Found {len(all_definitions)} metaobject definitions")
    return all_definitions

def fetch_metafield_definitions(store_url, access_token, verbose=False):
    endpoint = f"https://{store_url}{GRAPHQL_ENDPOINT}"
    headers = {
        "Content-Type": "application/json",
        "X-Shopify-Access-Token": access_token
    }

    query = """
    query metafieldDefinitions($after: String, $ownerType: MetafieldOwnerType!) {
      metafieldDefinitions(first: 100, after: $after, ownerType: $ownerType) {
        pageInfo {
          hasNextPage
          endCursor
        }
        edges {
          node {
            id
            namespace
            key
            name
            description
            type { name }
            ownerType
            validations { name value }
          }
        }
      }
    }
    """

    print("\n📝 Fetching metafield definitions...")
    all_definitions = []
    owner_type_counts = {}

    for owner_type in OWNER_TYPES:
        print(f"  • Fetching {owner_type}...")
        has_next_page = True
        after_cursor = None
        retry_count = 0
        max_retries = 3
        page_count = 0
        owner_type_definitions = []

        while has_next_page and retry_count < max_retries:
            try:
                variables = {
                    "after": after_cursor,
                    "ownerType": owner_type
                }
                
                if verbose:
                    print(f"    - Requesting page {page_count + 1} for {owner_type} (cursor: {after_cursor})")
                
                response = requests.post(
                    endpoint, 
                    headers=headers, 
                    json={"query": query, "variables": variables},
                    timeout=30  # 30 second timeout
                )
                response.raise_for_status()
                data = response.json()

                if verbose:
                    print(f"    - Raw API response for {owner_type}: {json.dumps(data, indent=2)}")

                if "errors" in data:
                    print(f"⚠️ Error fetching {owner_type}: {json.dumps(data['errors'], indent=2)}")
                    break

                if "data" not in data or data["data"] is None:
                    print(f"⚠️ Invalid response for {owner_type}: {json.dumps(data, indent=2)}")
                    break

                defs = data['data']['metafieldDefinitions']
                page_count += 1
                
                if verbose:
                    print(f"    - Retrieved {len(defs['edges'])} definitions on page {page_count}")
                
                for edge in defs['edges']:
                    node = edge['node']
                    node['type'] = node['type']['name']  # flatten nested type
                    all_definitions.append(node)
                    owner_type_definitions.append(node)

                has_next_page = defs['pageInfo']['hasNextPage']
                after_cursor = defs['pageInfo']['endCursor']
                
                if verbose and has_next_page:
                    print(f"    - More pages available for {owner_type}, continuing...")
                
                time.sleep(0.5)
                
            except requests.Timeout:
                retry_count += 1
                print(f"⚠️ Timeout fetching {owner_type}, attempt {retry_count}/{max_retries}")
                time.sleep(2)
                continue
            except requests.RequestException as e:
                print(f"⚠️ Error fetching {owner_type}: {str(e)}")
                break
            except Exception as e:
                print(f"⚠️ Unexpected error fetching {owner_type}: {str(e)}")
                break

        if retry_count >= max_retries:
            print(f"❌ Failed to fetch {owner_type} after {max_retries} attempts")
        
        owner_type_counts[owner_type] = len(owner_type_definitions)
        print(f"    ✓ Found {len(owner_type_definitions)} definitions")
        
        if verbose:
            print(f"    - Completed {owner_type}: {page_count} pages, {len(owner_type_definitions)} definitions")

    print("\n📊 Summary of metafield definitions:")
    for owner_type, count in owner_type_counts.items():
        print(f"  • {owner_type}: {count} definitions")

    return all_definitions

def main():
    parser = argparse.ArgumentParser(description="Export metafield and metaobject definitions from a Shopify store")
    parser.add_argument("-s", "--source", action="store_true", help="Export from source store")
    parser.add_argument("-t", "--target", action="store_true", help="Export from target store")
    parser.add_argument("--output", help="Output file path (optional)")
    parser.add_argument("-op", "--output-prefix", help="Prefix for output filenames")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output")

    args = parser.parse_args()
    
    # If neither source nor target specified, do both
    if not args.source and not args.target:
        args.source = True
        args.target = True

    def export_store(is_source=True):
        store = os.getenv("SHOPIFY_SOURCE_STORE" if is_source else "SHOPIFY_TARGET_STORE")
        token = os.getenv("SHOPIFY_SOURCE_TOKEN" if is_source else "SHOPIFY_TARGET_TOKEN")
        store_type = "source" if is_source else "target"
        
        if not store:
            raise Exception(f"Missing {store_type} store. Set SHOPIFY_{store_type.upper()}_STORE in your .env file.")
        if not token:
            raise Exception(f"Missing {store_type} token. Set SHOPIFY_{store_type.upper()}_TOKEN in your .env file.")

        print(f"\n🔄 Starting export from {store_type} store: {store}")

        # Set default output filename if not provided
        output_file = args.output
        if not output_file:
            prefix = f"{args.output_prefix}_" if args.output_prefix else ""
            output_file = f"{prefix}definitions_export_{store_type}.json"

        try:
            metafield_definitions = fetch_metafield_definitions(store, token, args.verbose)
            metaobject_definitions = fetch_metaobject_definitions(store, token, args.verbose)
            
            export_data = {
                "metafields": metafield_definitions,
                "metaobjects": metaobject_definitions
            }
            
            with open(output_file, 'w') as f:
                json.dump(export_data, f, indent=2)
            
            print(f"\n✅ Export completed for {store_type} store:")
            print(f"  • {len(metafield_definitions)} metafield definitions")
            print(f"  • {len(metaobject_definitions)} metaobject definitions")
            print(f"  • Saved to: {output_file}")
            
        except Exception as e:
            print(f"❌ Error exporting {store_type} store: {e}")

    # Execute exports based on arguments
    if args.source:
        export_store(is_source=True)
    if args.target:
        export_store(is_source=False)

if __name__ == "__main__":
    main()
