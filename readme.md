### Photo Inventory Service
This Python Webapp is a small service that will:
- Show a description/text
- Show an image of the inventory
- Have the possibility to submit new inventory images for submission
- Have an admin interface to approve new images and update the inventory image


#### Getting Started
_Config:_
There is a config at the root level. You can use this or specify a custom config and overwrite the env var "PHOTO_INVENTORY_CONFIG_PATH". The following variables should be updated:

- ADMIN_PASS - the administration password used for sites such as accepting submissions. DO NOT USE THE DEFAULT PASSWORD.
- ACCESS_KEY - the AWS ACCESS KEY for the S3 Bucket
- SECRET_ACCESS_KEY - the SECRET ACCESS KEY for the S3 Bucket
- BUCKET_NAME - the AWS S3 Bucket Name where the photos should be stored
- DEBUG - true/false

_Bucket CORS:_ 
By default, your Bucket might not allow others to interact with it. You must update the CORS Settings (as this app uses presigned URLs) to the following: 
```
[
 {
    "AllowedHeaders": [
        "*"
    ],
    "AllowedMethods": [
        "GET",
        "HEAD",
        "POST"
    ],
    "AllowedOrigins": [
        "*"
    ],
    "ExposeHeaders": []
 }
]
```