### Photo Inventory Service
This Containerized Web App allows to show the latest approved photo contribution of a place of interest. This could be an item exchange in your local community (e.g. to exchange books and other for free) or other places of interest for people where the help of others is needed. The texts are fully configurable through the config. 

There are three main pages right now, that the user and administrator will use:

_Index Page_
`/` - View the approved image.
![Index Page](index_example.png)

_Submit Photo_
`/submit` - People can open the website and submit a photo, to share the current items in the exchange, for example.
![Submission Page](submit_example.png)

_Approve Submission_
- `/approve` - login as an administrator via Basic Auth. Approve submissions to update the publicly visible photo of the inventory. The latest 3 Submissions are shown.
![Approve Page](approve_example.png)



#### Getting Started
The Web Application is based on Python and can be run in a Python Virtual Environment or via Docker. In order to make the Container Stateless, an Amazon S3 Bucket is being used.

*_Prerequisites_*:
The app works with AWS S3. Therefore there must be:
- A (private) Bucket
- An IAM User with Access Key & Credentials and permissions to the Bucket (List Files, Get Files, Upload Files/Put)

In order to fulfill this prerequisite, please create an S3 Bucket (https://docs.aws.amazon.com/AmazonS3/latest/userguide/create-bucket-overview.html). The Bucket can be private (the Web App uses pre-signed URLs to show photographs, uploads are done through the Web App without pre-signed URLs). After the S3 Bucket is created, please create an IAM User trough the IAM Service. The User needs permissions (List, Get, Upload/Put) for the S3 Bucket and the Objects within. Create Security Credentials and note them (you will need them for the config later).

_Config:_
The Config allows for customization of the Web Application. There is an example under `/config.json`. You can update this or specify a custom config and overwrite the env var `PHOTO_INVENTORY_CONFIG_PATH` with e.g. `my-custom-config.json`. The following variables should be updated:

- ADMIN_PASS - the administration password used for sites such as accepting submissions. *DO NOT USE THE DEFAULT PASSWORD.*
- ACCESS_KEY - the AWS ACCESS KEY of the IAM User created for accessing the S3 Bucket
- SECRET_ACCESS_KEY - the AWS SECRET ACCESS KEY of the IAM User created for accessing the S3 Bucket
- BUCKET_NAME - the AWS S3 Bucket Name of the created Bucket where the photos should be stored
- DEBUG - true/false

There are additional config values that you can update. For example the Page Title, the Description in the Index Page as well as the Text for Photo Submission.

Make sure to not push your config into the repository as it will contain secrets.

_Starting the App:_
Create a venv by running `python3 -m venv venv` and activate it by running `pip install -r requirements.txt`. Export your config file by running `export PHOTO_INVENTORY_CONFIG_PATH=MYPATH`. Then run `python app.py`.

_Running in Docker:_
Run `docker build . -t photo-inventory` (optionally tag the image). Run the image with your custom config `docker run -p 8080:5000 -e PHOTO_INVENTORY_CONFIG_PATH='<myconfig>' photo-inventory`. You can add the `--restart always` Flag to automatically restart the container.