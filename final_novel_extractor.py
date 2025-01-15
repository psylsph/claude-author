import json
import os

def extract_final_versions(input_file: str, output_file: str) -> None:
    """
    Extract only the final versions from the novel JSON structure and save them
    to a new file.
    
    Args:
        input_file (str): Path to the input JSON file
        output_file (str): Path to save the extracted content
    """
    try:
        # Read the input JSON file
        with open(input_file, 'r', encoding='utf-8') as f:
            novel_data = json.load(f)
        
        # Extract final versions and organize them by chapter
        final_versions = {}
        for chapter_key, chapter_data in sorted(novel_data.items()):
            # Extract just the final version text
            final_versions[chapter_key] = chapter_data['final_version']
        
        # Save as JSON
        if output_file.endswith('.json'):
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(final_versions, f, indent=4)
        
        # Save as plain text
        elif output_file.endswith('.txt'):
            with open(output_file, 'w', encoding='utf-8') as f:
                for chapter_key, content in final_versions.items():
                    # Write chapter header
                    chapter_num = chapter_key.split('_')[1]
                    f.write(f"\nChapter {chapter_num}\n")
                    f.write("=" * 50 + "\n\n")
                    # Write chapter content
                    f.write(content)
                    f.write("\n\n")
        
        print(f"Successfully extracted final versions to: {output_file}")
        
    except FileNotFoundError:
        print(f"Error: Could not find input file: {input_file}")
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON format in file: {input_file}")
    except KeyError as e:
        print(f"Error: Missing expected key in JSON structure: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")

def main():
    # Default file paths
    input_path = "novel_output/final_novel.json"
    output_json = "novel_output/final_versions.json"
    output_txt = "novel_output/final_versions.txt"
    
    # Create output directory if it doesn't exist
    os.makedirs("novel_output", exist_ok=True)
    
    # Extract and save in both JSON and text formats
    extract_final_versions(input_path, output_json)
    extract_final_versions(input_path, output_txt)

if __name__ == "__main__":
    main()