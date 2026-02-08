import os
import json

def convert_files_to_json(input_dir, output_dir):
    """
    Converts all files in the input directory (except '6331-sayili-is-sagligi-ve-guvenligi-kanunu.json')
    into JSON format and saves them in the output directory.
    
    Args:
        input_dir (str): Path to the input directory containing files.
        output_dir (str): Path to the output directory to save JSON files.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    for file_name in os.listdir(input_dir):
        if file_name == "6331-sayili-is-sagligi-ve-guvenligi-kanunu.json":
            continue

        input_file_path = os.path.join(input_dir, file_name)
        output_file_path = os.path.join(output_dir, f"{os.path.splitext(file_name)[0]}.json")

        try:
            with open(input_file_path, 'r', encoding='utf-8') as file:
                content = file.read()

            # Assuming the content is already in JSON format or can be converted
            data = json.loads(content)

            with open(output_file_path, 'w', encoding='utf-8') as json_file:
                json.dump(data, json_file, ensure_ascii=False, indent=4)

            print(f"Converted: {file_name} -> {output_file_path}")

        except Exception as e:
            print(f"Error processing {file_name}: {e}")

# Example usage
input_directory = "/Users/selcuk/Desktop/admin_pan/Legislation_RAG/laws"
output_directory = "/Users/selcuk/Desktop/admin_pan/Legislation_RAG/output"
convert_files_to_json(input_directory, output_directory)