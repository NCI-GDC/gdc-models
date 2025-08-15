import argparse
import sys
from copy import deepcopy
from pathlib import Path

import yaml


def analyze_mapping(data, path="", results=None, parent_key=None):
    """
    Recursively analyze the mapping structure to find objects with 'properties' but without 'type: nested'.

    Args:
        data: Current level of the mapping data (dict or other)
        path: Current path in the mapping tree (string)
        results: List to store found issues (list)
        parent_key: The key of the current object in its parent (string)

    Returns:
        List of dictionaries containing path and issue details
    """
    if results is None:
        results = []

    if isinstance(data, dict):
        # Check if current object has 'properties' but not 'type: nested'
        # Skip the root node (path is empty or "root")
        if "properties" in data and path and path != "root":
            obj_type = data.get("type")
            if obj_type != "nested":
                results.append(
                    {
                        "path": path,
                        "type": obj_type,
                        "has_properties": True,
                        "has_nested_type": False,
                        "properties_count": len(data["properties"])
                        if isinstance(data["properties"], dict)
                        else 0,
                        "parent_key": parent_key,
                    }
                )

        # Recursively check all nested objects
        for key, value in data.items():
            current_path = f"{path}.{key}" if path else key
            analyze_mapping(value, current_path, results, key)

    elif isinstance(data, list):
        # Handle lists (though less common in ES mappings)
        for i, item in enumerate(data):
            current_path = f"{path}[{i}]" if path else f"[{i}]"
            analyze_mapping(item, current_path, results, f"[{i}]")

    return results


def fix_mapping(data, issues):
    """
    Add 'type: nested' to all objects identified in issues.

    Args:
        data: The original mapping data (dict)
        issues: List of issues from analyze_mapping

    Returns:
        Fixed mapping data (dict)
    """
    fixed_data = deepcopy(data)

    for issue in issues:
        path = issue["path"]
        path_parts = path.split(".")

        # Navigate to the object that needs fixing
        current = fixed_data
        for part in path_parts[:-1]:
            if part.startswith("[") and part.endswith("]"):
                # Handle array indices
                index = int(part[1:-1])
                current = current[index]
            else:
                current = current[part]

        # Get the final key and add type: nested
        final_key = path_parts[-1]
        if final_key.startswith("[") and final_key.endswith("]"):
            index = int(final_key[1:-1])
            if isinstance(current[index], dict) and "properties" in current[index]:
                current[index]["type"] = "nested"
        else:
            if isinstance(current[final_key], dict) and "properties" in current[final_key]:
                current[final_key]["type"] = "nested"

    return fixed_data


def load_yaml_file(file_path):
    """Load and parse YAML file."""
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            return yaml.safe_load(file)
    except FileNotFoundError:
        print(f"Error: File '{file_path}' not found.")
        return None
    except yaml.YAMLError as e:
        print(f"Error parsing YAML file: {e}")
        return None
    except Exception as e:
        print(f"Error reading file: {e}")
        return None


def save_yaml_file(data, file_path):
    """Save data to YAML file."""
    try:
        with open(file_path, "w", encoding="utf-8") as file:
            yaml.dump(data, file, default_flow_style=False, sort_keys=False, indent=2)
        return True
    except Exception as e:
        print(f"Error saving file '{file_path}': {e}")
        return False


def print_results(issues, fix_mode=False):
    """Print the analysis results in a formatted way."""
    if not issues:
        print(
            "✅ No issues found! All objects with 'properties' have 'type: nested' (excluding root)."
        )
        return

    action = "Fixed" if fix_mode else "Found"
    print(
        f"🔍 {action} {len(issues)} object(s) with 'properties' but without 'type: nested':\n"
    )

    for i, issue in enumerate(issues, 1):
        print(f"{i}. Path: {issue['path']}")
        print(
            f"   Type: {issue['type'] or 'not specified'} → {'nested' if fix_mode else 'needs nested'}"
        )
        print(f"   Properties count: {issue['properties_count']}")
        print()


def main():
    """Execute this function to run the analyzer."""
    parser = argparse.ArgumentParser(
        description="Analyze Elasticsearch mapping YAML files for objects with 'properties' but without 'type: nested'",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze a mapping file
  python es_mapping_analyzer.py mapping.yaml

  # Fix issues and save to new file
  python es_mapping_analyzer.py mapping.yaml --fix --output fixed_mapping.yaml

  # Fix issues and overwrite original file
  python es_mapping_analyzer.py mapping.yaml --fix --output mapping.yaml
        """,
    )

    parser.add_argument("mapping_file", help="Path to the Elasticsearch mapping YAML file")
    parser.add_argument(
        "--fix",
        action="store_true",
        help='Add "type: nested" to all objects with properties but without nested type (excludes root)',
    )
    parser.add_argument(
        "--output",
        "-o",
        metavar="FILE",
        help="Output file path for fixed mapping (required when using --fix)",
    )

    args = parser.parse_args()

    # Validate arguments
    if args.fix and not args.output:
        print("Error: --output is required when using --fix")
        sys.exit(1)

    # Verify input file exists and has yaml extension
    if not Path(args.mapping_file).exists():
        print(f"Error: File '{args.mapping_file}' does not exist.")
        sys.exit(1)

    if not args.mapping_file.lower().endswith((".yaml", ".yml")):
        print("Warning: File doesn't have a .yaml or .yml extension.")

    print(f"Analyzing Elasticsearch mapping file: {args.mapping_file}")
    if args.fix:
        print(f"Fix mode enabled - will save corrected mapping to: {args.output}")
    print()

    # Load YAML file
    mapping_data = load_yaml_file(args.mapping_file)
    if mapping_data is None:
        sys.exit(1)

    # Analyze the mapping
    issues = analyze_mapping(mapping_data)

    if args.fix:
        if issues:
            # Fix the mapping
            fixed_data = fix_mapping(mapping_data, issues)

            # Save the fixed mapping
            if save_yaml_file(fixed_data, args.output):
                print(f"✅ Fixed mapping saved to: {args.output}")
                print_results(issues, fix_mode=True)
            else:
                print("❌ Failed to save fixed mapping")
                sys.exit(1)
        else:
            print("✅ No fixes needed - no issues found!")
    else:
        # Print analysis results
        print_results(issues)

        if issues:
            print(f"💡 To fix these issues automatically, run:")
            print(
                f"   python {sys.argv[0]} {args.mapping_file} --fix --output fixed_mapping.yaml"
            )

    # Return non-zero exit code if issues found and not in fix mode
    if issues and not args.fix:
        sys.exit(1)


if __name__ == "__main__":
    main()
