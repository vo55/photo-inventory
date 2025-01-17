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
def get_s3_client():
    return boto3.client(
        's3', 
        config=Config(signature_version='s3v4'),aws_access_key_id=app.config.get('ACCESS_KEY'),
        aws_secret_access_key=app.config.get('SECRET_ACCESS_KEY'),
        region_name=app.config.get('AWS_REGION')
    )

def tag_object(object_key):
    s3_client = get_s3_client()
    try:
        response = s3_client.put_object_tagging(
            Bucket=app.config.get('S3_BUCKET_NAME'),
            Key=object_key,
            Tagging={
                'TagSet': [
                    {
                        'Key': 'approved',
                        'Value': 'true'
                    },
                ]
            }
        )
    except Exception as e:
        pass
    

def get_update_date(key='latest'):
    try:
        s3_client = get_s3_client()
        response = s3_client.head_object(Bucket=app.config.get('S3_BUCKET_NAME'), Key=key)
        upload_date = response['LastModified']
    except Exception as e:
        return "unknown"
    return upload_date

def generate_presigned_get_url(key='latest'): 
    s3_client = get_s3_client()
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

def upload_to_s3(file): 
    s3_client = get_s3_client()
    try: 
        filename = app.config.get('S3_PREFIX') + file.filename
        s3_client.upload_fileobj( file, app.config.get('S3_BUCKET_NAME'), filename, ExtraArgs={'ACL': 'bucket-owner-full-control', 'ContentType': 'image/jpeg'} ) 
        return True 
    except Exception as e:
        print(f"Error uploading file: {e}") 
    return False

def get_objects_sorted_by_newest(limit=3, bucket_name=app.config.get('S3_BUCKET_NAME'), tag_key=None, prefix=app.config.get('S3_PREFIX')): 
    # List objects in the bucket with the specified prefix 
    objects = [] 
    s3 = get_s3_client()
    continuation_token = None 
    while True: 
        if continuation_token: 
            response = s3.list_objects_v2(Bucket=bucket_name, Prefix=prefix, ContinuationToken=continuation_token) 
        else: 
            response = s3.list_objects_v2(Bucket=bucket_name, Prefix=prefix) 
        if 'Contents' in response: 
            for obj in response['Contents']: 
                try: # Get object tags 
                    tagging = s3.get_object_tagging(Bucket=bucket_name, Key=obj['Key']) 
                    if tag_key:
                        for tag in tagging['TagSet']:
                            if tag_key == tag['Key']:
                                objects.append(obj) 
                    else:
                        objects.append(obj)
                except Exception as e: # Handle the case where an object doesn't have tags 
                    pass # Break the loop if there are no more objects to list 
        if 'NextContinuationToken' in response: 
            continuation_token = response['NextContinuationToken'] 
        else: 
            break # Sort the objects by LastModified date in descending order 
    objects_sorted = sorted(objects, key=lambda x: x['LastModified'], reverse=True) 
    return objects_sorted[:limit]

### Routes
@auth.verify_password
def verify_password(username, password):
    if username in users and \
            check_password_hash(users.get(username), password):
        return username

@app.route('/')
def hello():
    image_urls = []
    for s3_obj in get_objects_sorted_by_newest(tag_key='approved', limit=5):
        image_urls.append({"url": generate_presigned_get_url(key=s3_obj['Key']), "contributed": s3_obj['LastModified']})
    print(str(image_urls))
    content = render_template(
        'index.html',
        app_name=app.config.get('APP_NAME'),
        title=app.config.get('PAGE_TITLE'),
        description=app.config.get('PAGE_DESCRIPTION'),
        submit_title=app.config.get('SUBMIT_TITLE'),
        data=image_urls,
        upload_date=get_update_date(),
        map_enable=app.config.get('ENABLE_MAP'),
        map_link=app.config.get('MAP_LINK'),
        carousel_interval=app.config.get('CAROUSEL_CYCLE_INTERVAL', 'false')
    )
    return content

@app.route('/submit')
def submit():
    return render_template('submit.html', app_name=app.config.get('APP_NAME') ,title=app.config.get('SUBMIT_TITLE'), description=app.config.get('SUBMIT_DESCRIPTION'), submit_title=app.config.get('SUBMIT_TITLE'))

@app.route('/upload-success')
def success_message():
    return render_template('upload-success.html', app_name=app.config.get('APP_NAME') ,title=app.config.get('SUBMIT_TITLE'), description=app.config.get('SUBMIT_DESCRIPTION'), submit_title=app.config.get('SUBMIT_TITLE'), toast=app.config.get('FILE_UPLOAD_SUCCESS_TOAST'))

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
            return redirect('/upload-success')
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
    for object_key in get_objects_sorted_by_newest():
        urls.append(generate_presigned_get_url(object_key['Key']))
    return render_template('approve.html', urls=urls)


@app.route('/approve-submit', methods=['POST']) 
@auth.login_required
def process_approvals():
    index = int(request.form['index'])
    # this will create a race condition in case someone uploads an object in this millisecond.
    approved_object = get_objects_sorted_by_newest()[index]
    tag_object(approved_object['Key'])
    return redirect('/')


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=app.config['DEBUG'])