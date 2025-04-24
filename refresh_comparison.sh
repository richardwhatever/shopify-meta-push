#!/bin/bash

echo "=== Running export_metafields.py ==="
python export_metafields.py -q || exit 1

echo -e "\n=== Running compare_metafields.py ==="
python compare_metafields.py -q || exit 1

echo -e "\n=== Running list_metafields.py ==="
python list_metafields.py || exit 1

echo -e "\n=== All scripts completed successfully ===" 