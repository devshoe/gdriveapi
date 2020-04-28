# googledriveapi
ezpz
* call download(path) to download single file/folder [whatever it terminates in]
* call upload(path) to upload single file/folder [whatever it terminates in]
* call delete(search_string) to delete single file [not pathed, it runs search for search string] PERMANENT DELETION
* call search(string, by="all") to search for stuff. the by field takes either all to return any match, files for files, folders for folders and anything else will be searched for in mimeType for ex mp4 etc

# command line
* -u path for uploading
* -d path for downloading
* -r searchstring for deleting (remove) with confirmation DOES NOT TRASH
* -s searchstring to return info about string

to get api creds
"https://console.cloud.google.com/apis/credentials/oauthclient" -> other 
download the json file and store it as api.json
from here on things will just work

to run from command line u can like chmod +x it and move it to /usr/local/bin or something in ur PATH
