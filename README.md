# Obsidian 2 Trilium converter

Convert Obsidian markdown notes (including images) to trilium supported import zip file.

## System Requirements

- Python 3.10 minimum.

## Usage

```bash
# Package the "Software" directory and output the results to the CWD.
python obsidian2trilium.py ~/notes/Software
# Specify a custom output path.
python obsidian2trilium.py ~/notes/Software --output-path ./output.zip
```

## How it works?

1. The script finds all `.png` files in the specified path.
2. Iterates through all markdown files.
3. For each file tries to find `![[]]` format image links.
4. Each link image name is checked agains image name and path key value pair.
5. The existing image link is converted into a common markdown supported format and for the image path
the base64 representation of the image is used.
6. If any markdown note is considered ready to be zipped it is done in a thread-safe way.