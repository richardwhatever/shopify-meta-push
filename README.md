# Shopify Metafields Migration Tool

A powerful CLI tool for managing and migrating Shopify metafield definitions between stores. This tool helps developers and store managers export, compare, and import metafield definitions across different Shopify stores.

## Features

- 📤 **Export Metafield Definitions**: Extract all metafield definitions from a source store
- 📥 **Import Metafield Definitions**: Import definitions into a target store
- 🔍 **Compare Definitions**: Analyze differences between stores
- 📋 **List Metafields**: View all metafield definitions in a store
- ✨ **Supported Owner Types**:
  - Collections
  - Customers
  - Orders
  - Products
  - Product Variants

## Installation

1. Clone this repository:

```bash
git clone https://github.com/your-username/shopify-meta-push.git
cd shopify-meta-push
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Create a `.env` file with your Shopify Admin API credentials:

```bash
SHOPIFY_ADMIN_TOKEN=your_admin_api_token
```

## Quick Start

### 1. Export Metafield Definitions

Export definitions from your source store:

```bash
python export_metafields.py --store source-store.myshopify.com
```

This will create a JSON file containing all metafield definitions.

### 2. Compare Definitions

Compare metafield definitions between source and target stores:

```bash
python compare_metafields.py --source definitions_export_source.json --target definitions_export_target.json
```

This generates a `metafield_diff.json` file showing differences between stores.

### 3. Import Definitions

Import the missing or changed definitions to your target store:

```bash
python import_metafields.py --store target-store.myshopify.com
```

### 4. List Current Metafields

View all metafield definitions in a store:

```bash
python list_metafields.py --store your-store.myshopify.com
```

## Contributing

Contributions are welcome! Here's how you can help:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Environment Variables

Create a `.env` file in the project root with the following variables:

```env
SHOPIFY_ADMIN_TOKEN=your_admin_api_token
```

## License

[Add your license information here]

## Support

[Add support information or contact details here]
