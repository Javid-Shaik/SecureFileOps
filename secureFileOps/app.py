from flask import Flask, request, redirect, url_for, render_template, send_from_directory
import os
import pyAesCrypt
import zipfile
import shutil
from tqdm import tqdm

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['DECRYPTED_FOLDER'] = 'decrypted'
app.config['ZIP_FOLDER'] = 'zipped'
app.config['TEMP_FOLDER'] = 'temp'  # Temporary folder for extracting files

# Ensure folders exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['DECRYPTED_FOLDER'], exist_ok=True)
os.makedirs(app.config['ZIP_FOLDER'], exist_ok=True)
os.makedirs(app.config['TEMP_FOLDER'], exist_ok=True)

def encrypt_folder(folder_path, password):
    bufferSize = 64*1024
    files_to_encrypt = []
    
    # Collect files that need encryption
    for root, _, files in os.walk(folder_path):
        for file in files:
            file_path = os.path.join(root, file)
            if not file.endswith(".aes"):
                files_to_encrypt.append(file_path)
    
    if not files_to_encrypt:
        print("All files are already encrypted.")
        return
    
    # Encrypt the collected files
    for file_path in tqdm(files_to_encrypt, desc="Encrypting files"):
        output_path = file_path + ".aes"
        pyAesCrypt.encryptFile(file_path, output_path, password, bufferSize)
        os.remove(file_path)
    
    print("Encryption completed.")


def decrypt_folder(folder_path, password):
    bufferSize = 64*1024
    for root, _, files in os.walk(folder_path):
        for file in tqdm(files, desc="Decrypting files"):
            if file.endswith(".aes"):
                input_path = os.path.join(root, file)
                output_path = os.path.join(app.config['TEMP_FOLDER'], file[:-4])
                pyAesCrypt.decryptFile(input_path, output_path, password, bufferSize)
                os.remove(input_path)

def zip_folder(folder_path, zip_path):
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(folder_path):
            for file in tqdm(files, desc="Adding files to zip"):
                file_path = os.path.join(root, file)
                zipf.write(file_path, os.path.relpath(file_path, folder_path))

def unzip_file(zip_file, extract_to):
    with zipfile.ZipFile(zip_file, 'r') as zip_ref:
        zip_ref.extractall(extract_to)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        operation = request.form.get('operation')
        password = request.form.get('password')
        if 'file' not in request.files:
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            return redirect(request.url)
        if file:
            # Save the uploaded file
            uploaded_file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(uploaded_file_path)

            # Ensure the temp folder is empty
            shutil.rmtree(app.config['TEMP_FOLDER'])
            os.makedirs(app.config['TEMP_FOLDER'], exist_ok=True)

            # Define the result zip file path
            result_zip_path = os.path.join(app.config['ZIP_FOLDER'], 'result.zip')

            try:
                if operation == 'encrypt':
                    unzip_file(uploaded_file_path, app.config['TEMP_FOLDER'])
                    encrypt_folder(app.config['TEMP_FOLDER'], password)
                    zip_folder(app.config['TEMP_FOLDER'], result_zip_path)
                elif operation == 'decrypt':
                    unzip_file(uploaded_file_path, app.config['TEMP_FOLDER'])
                    decrypt_folder(app.config['TEMP_FOLDER'], password)
                    zip_folder(app.config['TEMP_FOLDER'], result_zip_path)
                elif operation == 'zip':
                    unzip_file(uploaded_file_path, app.config['TEMP_FOLDER'])
                    zip_folder(app.config['TEMP_FOLDER'], result_zip_path)
                elif operation == 'unzip':
                    unzip_file(uploaded_file_path, app.config['UPLOAD_FOLDER'])
                    result_zip_path = uploaded_file_path  # Return the original file as is

                # Return the result
                return redirect(url_for('download', filename='result.zip'))
            finally:
                # Clean up all folders
                shutil.rmtree(app.config['UPLOAD_FOLDER'])
                shutil.rmtree(app.config['DECRYPTED_FOLDER'])
                shutil.rmtree(app.config['TEMP_FOLDER'])
                os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
                os.makedirs(app.config['DECRYPTED_FOLDER'], exist_ok=True)
                os.makedirs(app.config['TEMP_FOLDER'], exist_ok=True)

    return render_template('index.html')

@app.route('/download/<filename>')
def download(filename):
    file_path = os.path.join(app.config['ZIP_FOLDER'], filename)
    if not os.path.exists(file_path):
        return "File not found", 404
    return send_from_directory(directory=app.config['ZIP_FOLDER'], path=filename)

if __name__ == '__main__':
    app.run(debug=True)
