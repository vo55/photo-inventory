import json
from flask import Flask, render_template, request, redirect
from flask_httpauth import HTTPBasicAuth
from werkzeug.security import generate_password_hash, check_password_hash
import os
import boto3
from botocore.client import Config
from flask_cors import CORS
from PIL import Image
import io

app = Flask(__name__)
CORS(app)
auth = HTTPBasicAuth()

# Load JSON config
config_path = os.environ.get("PHOTO_INVENTORY_CONFIG_PATH", "config.json")
with open(config_path, 'r') as config_file: 
    config = json.load(config_file) 
    app.config.update(config)

users = { "admin": generate_password_hash(app.config.get('ADMIN_PASS')) }
toast = None


### Shared functions
def generate_presigned_get_url(key='latest'): 
    s3_client = boto3.client(
        's3', 
        config=Config(signature_version='s3v4'),aws_access_key_id=app.config.get('ACCESS_KEY'),
        aws_secret_access_key=app.config.get('SECRET_ACCESS_KEY'),
        region_name=app.config.get('AWS_REGION')
    )
    try: 
        response = s3_client.generate_presigned_url( 
                                                    ClientMethod='get_object',
                                                    Params={
                                                        'Bucket': app.config.get('S3_BUCKET_NAME'),
                                                        'Key': key
                                                        },
                                                    )
    except Exception as e: 
        print(str(e))
        response = None
    return response

def list_newest_objects(limit=3):
    try:
        s3_client = boto3.client(
            's3', 
            config=Config(signature_version='s3v4'),aws_access_key_id=app.config.get('ACCESS_KEY'),
            aws_secret_access_key=app.config.get('SECRET_ACCESS_KEY'),
            region_name=app.config.get('AWS_REGION')
        )
        response = s3_client.list_objects_v2( Bucket=app.config.get('S3_BUCKET_NAME'), MaxKeys=1000 ) 
        objects = response.get('Contents', []) # Sort objects by LastModified date in descending order 
        objects_sorted = sorted(objects, key=lambda obj: obj['LastModified'], reverse=True) 
        newest_objects = objects_sorted[:limit] 
        return newest_objects 
    except Exception as e: 
        print(f"Error listing objects: {e}") 
        return []

def upload_to_s3(file): 
    s3_client = boto3.client(
        's3', 
        config=Config(signature_version='s3v4'),aws_access_key_id=app.config.get('ACCESS_KEY'),
        aws_secret_access_key=app.config.get('SECRET_ACCESS_KEY'),
        region_name=app.config.get('AWS_REGION')
    )
    try: 
        s3_client.upload_fileobj( file, app.config.get('S3_BUCKET_NAME'), f"upload/{file.filename}", ExtraArgs={'ACL': 'bucket-owner-full-control', 'ContentType': 'image/jpeg'} ) 
        return True 
    except Exception as e:
        print(f"Error uploading file: {e}") 
    return False

def rename_object_in_s3(old_key, new_key):
    s3_client = boto3.client(
        's3', 
        config=Config(signature_version='s3v4'),aws_access_key_id=app.config.get('ACCESS_KEY'),
        aws_secret_access_key=app.config.get('SECRET_ACCESS_KEY'),
        region_name=app.config.get('AWS_REGION')
    )
    try: # Copy the object to the new key 
        s3_client.copy_object( Bucket=app.config.get('S3_BUCKET_NAME'), CopySource={'Bucket': app.config.get('S3_BUCKET_NAME'), 'Key': old_key}, Key=new_key, ACL='bucket-owner-full-control', ContentType='image/jpeg' ) 
        # Delete the original object 
        s3_client.delete_object( Bucket=app.config.get('S3_BUCKET_NAME'), Key=old_key ) 
        return True 
    except Exception as e: 
        print(f"Error renaming object: {e}") 
        return False

### Routes

@auth.verify_password
def verify_password(username, password):
    if username in users and \
            check_password_hash(users.get(username), password):
        return username

@app.route('/')
def hello():
    image_url = generate_presigned_get_url()
    toast = None
    if "Referer" in request.headers.keys():
        if "submit" in request.headers.get("Referer"):
            toast = app.config["FILE_UPLOAD_SUCCESS_TOAST"]
    content = render_template(
        'index.html',
        app_name=app.config.get('APP_NAME'),
        title=app.config.get('PAGE_TITLE'),
        description=app.config.get('PAGE_DESCRIPTION'),
        submit_title=app.config.get('SUBMIT_TITLE'),
        image_url=image_url,
        toast=toast
    )
    app.config['TOAST'] = None
    return content

@app.route('/submit')
def submit():
    return render_template('submit.html', app_name=app.config.get('APP_NAME') ,title=app.config.get('SUBMIT_TITLE'), description=app.config.get('SUBMIT_DESCRIPTION'), submit_title=app.config.get('SUBMIT_TITLE'))

@app.route('/upload', methods=['POST'])
def upload():
    if 'file' not in request.files: 
        return redirect('/submit') 
    file = request.files['file'] 
    if file.filename == '': 
        return redirect('/submit') 
    if file and file.content_type.startswith('image/'): 
        image = Image.open(file) 
        image.thumbnail((1000, 1000)) #scale the image to a max width or max height of 1000
        scaled_image = io.BytesIO() 
        image.save(scaled_image, format="JPEG") 
        scaled_image.seek(0) 
        oldfilename = file.filename
        file = scaled_image 
        file.filename = oldfilename
        success = upload_to_s3(file) 
        if success: 
            return redirect('/')
    else: return redirect('/submit')

@app.route('/config') 
@auth.login_required
def show_config():
    if app.config['DEBUG']:
        return f"Debug: {app.config['DEBUG']}, Secret Key: {app.config['SECRET_KEY']}, Some Setting: {app.config['SOME_SETTING']}"
    else:
        return ""

@app.route('/approve') 
@auth.login_required
def approve_submission():
    urls = []
    for object_key in list_newest_objects():
        urls.append(generate_presigned_get_url(object_key['Key']))
    return render_template('approve.html', urls=urls)


@app.route('/approve-submit', methods=['POST']) 
@auth.login_required
def process_approvals():
    index = int(request.form['index'])
    # this will create a race condition in case someone uploads an object in this millisecond.
    approved_object = list_newest_objects()[index]
    rename_object_in_s3(approved_object['Key'], 'latest')
    urls = []
    return redirect('/')


if __name__ == '__main__':
    app.run(host="0.0.0.0", debug=app.config['DEBUG'])