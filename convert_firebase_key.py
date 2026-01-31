import json
import toml

def convert_json_to_toml(json_file_path, toml_file_path):
    """
    Converts a Firebase service account JSON key to Streamlit secrets TOML format
    """
    # Read the JSON file
    with open(json_file_path, 'r') as json_file:
        json_data = json.load(json_file)
    
    # Prepare the TOML data
    toml_data = {
        'type': json_data['type'],
        'project_id': json_data['project_id'],
        'private_key_id': json_data['private_key_id'],
        'private_key': json_data['private_key'],  # TOML will preserve line breaks correctly
        'client_email': json_data['client_email'],
        'client_id': json_data['client_id'],
        'auth_uri': json_data['auth_uri'],
        'token_uri': json_data['token_uri'],
        'auth_provider_x509_cert_url': json_data['auth_provider_x509_cert_url'],
        'client_x509_cert_url': json_data['client_x509_cert_url']
    }
    
    # Write to TOML file
    with open(toml_file_path, 'w') as toml_file:
        toml.dump(toml_data, toml_file)
    
    print(f"Successfully converted {json_file_path} to {toml_file_path}")

if __name__ == "__main__":
    print("Firebase Service Account Key Converter")
    print("=====================================")
    print()
    print("This script will convert your Firebase service account JSON key")
    print("to the proper Streamlit secrets.toml format.")
    print()
    print("To use this script:")
    print("1. Place your service account JSON file in this directory")
    print("2. Rename it to 'service_account.json' or update the filename below")
    print("3. Run this script: python convert_firebase_key.py")
    print()
    
    # Set your JSON file path here
    json_path = input("Enter the path to your JSON service account key file: ")
    toml_path = ".streamlit/secrets.toml"
    
    try:
        convert_json_to_toml(json_path, toml_path)
        print()
        print("Conversion complete! Your secrets.toml file has been updated.")
        print("Make sure the .streamlit folder exists in your project directory.")
    except Exception as e:
        print(f"Error: {e}")