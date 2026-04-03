rmdir /s /q ".aws-sam"

call sam build --no-use-container

call sam deploy --profile=myawsprofile --force-upload --no-confirm-changeset
