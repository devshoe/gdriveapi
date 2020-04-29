#!/usr/loca/bin/python3
from __future__ import print_function

import argparse
import io
import os
import sys
from time import sleep

from googleapiclient import discovery, http
from httplib2 import Http
from oauth2client import client, file, tools

API_CREDENTIALS_FILENAME = os.path.abspath("")+"/api.json"
USER_CREDENTIALS_FILENAME = os.path.abspath("")+"/user.json"


parser = argparse.ArgumentParser()
parser.add_argument("-s", "--search", required=False)
parser.add_argument("-d", "--download", required=False)
parser.add_argument("-qd", "--quickdownload", required=False)
parser.add_argument("-r", "--remove", required=False)
parser.add_argument("-u", "--upload", required=False)
parser.add_argument("-f", "--folder", action="store_true", required=False)


def get_credentials():
    """Login flow. Automatically runs login flow if no user.json file."""
    if "api.json" not in os.listdir():
        print(f"Please get api credentials as json file from https://console.cloud.google.com/apis/credentials/oauthclient and store as {API_CREDENTIALS_FILENAME}")
        exit(0)

    existing_user_info = file.Storage(USER_CREDENTIALS_FILENAME).get()

    if not existing_user_info or existing_user_info.invalid:
        sys.argv.insert(1, "--noauth_local_webserver") #command line login
        flow = client.flow_from_clientsecrets(API_CREDENTIALS_FILENAME, scope='https://www.googleapis.com/auth/drive')
        user_info = tools.run_flow(flow, file.Storage(USER_CREDENTIALS_FILENAME))
        sys.argv.pop(1)
        return user_info

    return existing_user_info

DRIVE = discovery.build('drive', 'v3', credentials=get_credentials())
ROOT_ID = DRIVE.files().get(fileId="root").execute()["id"]

def search(filename="", by="all", query=None):
    """Only by """
    pagesize = 50
    if not query:
        query = f"name contains '{filename.split(' ')[0]}' "

        if " " in filename:
            for x in filename.split(" ")[1:]: query += f"and name contains '{x}'"
    query += " and trashed=false"    
    results= DRIVE.files().list(q=query, pageSize=pagesize, fields="files(id, name, mimeType, parents)").execute()["files"]
    final = []

    for result in results: 
        if "fo" in by: #all folders no files
            if "folder" in result["mimeType"]: final.append(result)
        elif "fi" in by: #all files no folders
            if "folder" not in result["mimeType"]: final.append(result)
        elif "all" in by: #everything
            final.append(result)
        else: #custom data type
            if by in result["mimeType"]: final.append(result)
    return final

def pathInfo(path):
    ogpath = path
    path = path.split("/")
    match = {"id":ROOT_ID}
    for folderName in path: 
        for possibleMatch in search(query=f"name='{folderName}'",by="folder" if "." not in folderName else "files"):
            if match["id"] == possibleMatch["parents"][-1]: match = possibleMatch
    return match

def filesInFolderById(folderId):
    """Utility function"""
    return DRIVE.files().list(q=f"'{folderId}' in parents").execute()["files"]

def filesInFolder(folderName):
    """Utility function to search by folder name and return files"""
    return DRIVE.files().list(q=f"'{search(folderName, 'folder')[0]['id']}' in parents").execute()["files"]


def downloadById(fileID, outputName):
    chunkable_bytes_python_object = io.BytesIO() #handles all chunking and downloads
    unexecuted_request = DRIVE.files().get_media(fileId=fileID) 
    downloader = http.MediaIoBaseDownload(chunkable_bytes_python_object, unexecuted_request)
    print("Downloading: "+outputName)
    while True:
        state, completion_flag = downloader.next_chunk()
        print(f"{outputName}:{state.progress() * 100}% Completed")
        if completion_flag: break

    with open(outputName, "wb") as f:f.write(chunkable_bytes_python_object.getbuffer())

def download(path, savepath=os.path.abspath('downloads')):
    """
    ONLY ABSOLUTE PATHS ALLOWED reeeee but ez like normal from root data/stuff/etc if etc
    is a file, itll download file if folder itll download folder ezpz
    """
    ogpath = path
    path = path.split("/")
    if savepath: savepath = os.path.abspath(savepath)

    match = {"id":ROOT_ID}
    for folderName in path: 
        for possibleMatch in search(query=f"name='{folderName}'",by="folder" if "." not in folderName else "files"):
            if match["id"] == possibleMatch["parents"][-1]: match = possibleMatch
    #search complete

    if "folder" in match["mimeType"]: #if path terminates in a folder
        try:os.mkdir(match["name"] if not savepath else savepath+"/"+match["name"])
        except:pass #exists

        files = search(query=f"'{match['id']}' in parents")

        for f in files:
            if "folder" in f["mimeType"]:#folder containing folder
                print("Subfolder inside folder:", path[-1])
                download(ogpath+"/"+f["name"], path[-1] if not savepath else savepath+"/"+path[-1]) 

            else:

                print("Downloading lowest level file:", savepath+"/"+f["name"])
                downloadById(f["id"], savepath+"/"+f"/{path[-1]}/"+f["name"])
    else:
        downloadById(match["id"], match["name"]) #if its a file

def quickDownload(searchStr): 
    searchRes = search(searchStr, "file")[0]
    print(searchRes)
    downloadById(searchRes["id"], searchRes["name"])

def upload(filePath, parentID=None):
    """recursively makes 1:1 copy maintaining file hierarchy in root, if single file simply copies to root. ignore parentid, for recursion"""
    filePath = os.path.abspath(filePath)
    if os.path.isfile(filePath):
        file_metadata = {'name': filePath.split("/")[-1]}
        if parentID: file_metadata.update({"parents":[parentID]})
        media = http.MediaFileUpload(filePath)
        f = DRIVE.files().create(body=file_metadata, media_body=media, fields='id').execute()
        return
    else:
        #create empty folder
        folder_metadata = {
            'name': filePath.split("/")[-1],
            'mimeType': 'application/vnd.google-apps.folder',
                }
        if parentID: folder_metadata.update({"parents":[parentID]})
        folderID = DRIVE.files().create(body=folder_metadata, fields='id').execute().get("id")
        for f in os.listdir(filePath): 
            print(f)
            upload(os.path.abspath(filePath+"/"+f), parentID = folderID)
        return

def delete(filename, trashed=False):
    filename = search(filename)[0]
    if trashed:
        #broken in v3
        # empty_file = file().setTrashed(True)
        DRIVE.files().update(filename["id"], setTrashed=True).execute()
        print(f"Trashed {filename['name']}")
    else:

        ip = input(f"Delete {'folder' if 'folder' in filename['mimeType'] else 'file'} {filename['name']} permanently?")
        if ip.lower() in ["y", "yes", "ye"]:
            DRIVE.files().delete(fileId=filename["id"]).execute()
            print(f"Deleted {filename['name']}")




if __name__ == "__main__":
    parsedArgs = parser.parse_args()
    if parsedArgs.search: print(search(parsedArgs.search))
    if parsedArgs.download: download(parsedArgs.download)
    if parsedArgs.upload: upload(parsedArgs.upload)
    if parsedArgs.remove: delete(parsedArgs.remove)
    if parsedArgs.quickdownload: quickDownload(parsedArgs.quickdownload)
    pass
