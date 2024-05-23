import shutil
import sys

from googleapiclient.discovery import build
import json
import os
import re
import subprocess
import requests



#------------------------Variables----------------------------------------------
api_key = ''

#This is a few blacklisted video titles we dont want to deal with
blacklist = ['Deleted video', 'Private video']

#Lists and Dictionaries
video_dict = {}
video_titles = []
video_id = []
folder_id = []
archive_list = []
download_list = []

#------------------------Functions-------------------------------------------


#Checks if the API key is a valid working API key
def check_api_key(api_key):
    # Construct the URL for a test API request
    url = f"https://www.googleapis.com/youtube/v3/channels?key={api_key}&part=id&forUsername=GoogleDevelopers"

    # Make the API request
    response = requests.get(url)

    # Check if the response is successful (status code 200)
    if response.status_code == 200:
        print("Your API key seems to be valid!")
    else:
        print("There seems to be a problem with your API key. Please restart the script and try again.")
        sys.exit()

#This one handels everything related to API(setting, getting)
def handle_api():
    global api_key

    #The APPDATA Folder
    appdata_folder = os.getenv('APPDATA')
    #Constructs the full path to the file in the APPDATA folder
    folder_path = os.path.join(appdata_folder, "Youtube_api")
    #Adds the file to the folder
    file_path = os.path.join(folder_path, 'ytapi')

    # Create the directory if it doesn't exist
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)

    #Checks if the file exists if it does the reads its contents and saves it as the api_key variable
    if os.path.exists(file_path):
        with open(file_path, 'r') as file:
            api_key = file.read().strip()  # Use strip() to remove any leading/trailing whitespace

        check_api_key(api_key)
        return None

    #In case the file does not exits then it will asks the user for the api key and saves it in a new folder
    print('It appears you do not have any API key added yet!\nPlease type your api key and press enter.')
    api_key = input()
    check_api_key(api_key)

    with open(file_path, 'w') as file:
        file.write(api_key)

#This will gets the playlist url and gets the playlist id from it
def strip_playlist_url(url):
    #checks if its even an url, or its just the id itself
    if '=' in url:
        #finds the '=' in the url
        i = url.find('=')

        #if there are more than 2 '=' in the url
        if url.count('=') == 2:
            #when the url was copied using the share function then it will contain a few more chars at the end that we dont need
            return url.rsplit(url[i],-1)[1][:-3]
        else:
            #otherwise we will only need the second part of the split, which will perfectly contain the playlist ID
            return url.rsplit(url[i], -1)[1]
    else:
        #if it is it will just return it
        return url

#this is a debug function to print lists in a readable way
def print_list(list):
    print(json.dumps(list, indent=4, ensure_ascii=False))

#This will gets the playlist items, and places them in a list
def request_list(playlist_id):
    global video_titles,video_id

    #this will be used to get more then one page, since 1 request can only get 50 items, if their are more then that we will need to get one more page
    next_page_token = None

    # Loop until all pages are retrieved
    while True:
        request = youtube.playlistItems().list(
            part='snippet',
            playlistId=playlist_id,
            maxResults=50,
            pageToken=next_page_token
        )
        response = request.execute()

        #this will loop x amount of times, x is the amouth of items in the request
        for i in range(len(response['items'])):
            #gets the value of each title
            value = response['items'][i]['snippet']['title']
            #gets the value of each id
            key = response['items'][i]['snippet']['resourceId']['videoId']

            #if the values isnt in the black list it will places both of them into their own lists
            if (value not in blacklist):
                video_titles.append(value)
                video_id.append(key)

        # Check if there are more pages
        next_page_token = response.get("nextPageToken")
        if not next_page_token:
            break

#strip the unneeded characters from the titles
def strip_list_titles(list):
    #makes a temporary copy
    copy_titles = list.copy()
    # and a return list
    list = []

    for t in copy_titles:
        #this will take out every character that we dont need
        list.append(re.sub(r'[^\w\s\u4e00-\u9fff\u3040-\u30ff]', '', t))

    return list

#this will create a new list, that will contain the titles with their id, this is how they will be saved
def add_id_to_title():
    global video_id, video_titles

    ret_titles = []
    for t in range(len(video_id)):
        ret_titles.append(f'{video_titles[t]} -#{video_id[t]}')

    return ret_titles

#Gets the id of the songs
def get_folder_id():
    global folder_titles, folder_id
    for title in folder_titles:
        temp_index = title.find('-#') + 2
        folder_id.append(title[temp_index:])

#Returns the full name the file by ID
def get_full_name(id):
    index_id = folder_id.index(id)

    return f'{folder_titles[index_id]}.mp3'

#----------------------Script--------------------------------------

#we get the playlist id
playlist_id = strip_playlist_url(sys.argv[1])

#sets up the api to be used
handle_api()

#sets up the youtube API connection
youtube = build('youtube', 'v3', developerKey=api_key)

#gets the lists
request_list(playlist_id)

video_titles = strip_list_titles(video_titles)
video_title_id = add_id_to_title()

#checks if the required folders are present, if not it will create them
if not os.path.exists('Songs'):
    os.makedirs('Songs')
    print('Songs folder created!')
if not os.path.exists('Archive'):
    os.makedirs('Archive')
    print('Archive folder created!')

#gets the file names from the folder
folder_titles = os.listdir('Songs')

for title in folder_titles:
    index_title = folder_titles.index(title)
    folder_titles[index_title] = title[:-4]

get_folder_id()

#makes a list of files that are not in the playlist, that it will need to download
for t in video_id:
    if t not in folder_id:
        download_list.append(t)

#print_list(download_list)
for d in download_list:
    try:
        index = video_id.index(d)
        command = f'yt-dlp.exe {d} --extract-audio --audio-format mp3 -o "Songs/{video_title_id[index]}.%(ext)s"'
        result = subprocess.run(command)
    except subprocess.CalledProcessError as e:
        print("Error:", e)

for id in folder_id:
    if id not in video_id:
        archive_list.append(id)


for i in range(len(archive_list)):
    name = get_full_name(archive_list[i])
    source = f'Songs/{name}'
    print(f'{name} is archived!')
    try:
        shutil.move(source,'Archive')
    except shutil.Error:
        print(f'Error: {name} is already archived!')





youtube.close()
import shutil
import sys

from googleapiclient.discovery import build
import json
import os
import re
import subprocess
import requests



#------------------------Variables----------------------------------------------
api_key = ''

#This is a few blacklisted video titles we dont want to deal with
blacklist = ['Deleted video', 'Private video']

#Lists and Dictionaries
video_dict = {}
video_titles = []
video_id = []
folder_id = []
archive_list = []
download_list = []

#------------------------Functions-------------------------------------------


#Checks if the API key is a valid working API key
def check_api_key(api_key):
    # Construct the URL for a test API request
    url = f"https://www.googleapis.com/youtube/v3/channels?key={api_key}&part=id&forUsername=GoogleDevelopers"

    # Make the API request
    response = requests.get(url)

    # Check if the response is successful (status code 200)
    if response.status_code == 200:
        print("Your API key seems to be valid!")
    else:
        print("There seems to be a problem with your API key. Please restart the script and try again.")
        sys.exit()

#This one handels everything related to API(setting, getting)
def handle_api():
    global api_key

    #The APPDATA Folder
    appdata_folder = os.getenv('APPDATA')
    #Constructs the full path to the file in the APPDATA folder
    folder_path = os.path.join(appdata_folder, "Youtube_api")
    #Adds the file to the folder
    file_path = os.path.join(folder_path, 'ytapi')

    # Create the directory if it doesn't exist
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)

    #Checks if the file exists if it does the reads its contents and saves it as the api_key variable
    if os.path.exists(file_path):
        with open(file_path, 'r') as file:
            api_key = file.read().strip()  # Use strip() to remove any leading/trailing whitespace

        check_api_key(api_key)
        return None

    #In case the file does not exits then it will asks the user for the api key and saves it in a new folder
    print('It appears you do not have any API key added yet!\nPlease type your api key and press enter.')
    api_key = input()
    check_api_key(api_key)

    with open(file_path, 'w') as file:
        file.write(api_key)

#This will gets the playlist url and gets the playlist id from it
def strip_playlist_url(url):
    #checks if its even an url, or its just the id itself
    if '=' in url:
        #finds the '=' in the url
        i = url.find('=')

        #if there are more than 2 '=' in the url
        if url.count('=') == 2:
            #when the url was copied using the share function then it will contain a few more chars at the end that we dont need
            return url.rsplit(url[i],-1)[1][:-3]
        else:
            #otherwise we will only need the second part of the split, which will perfectly contain the playlist ID
            return url.rsplit(url[i], -1)[1]
    else:
        #if it is it will just return it
        return url

#this is a debug function to print lists in a readable way
def print_list(list):
    print(json.dumps(list, indent=4, ensure_ascii=False))

#This will gets the playlist items, and places them in a list
def request_list(playlist_id):
    global video_titles,video_id

    #this will be used to get more then one page, since 1 request can only get 50 items, if their are more then that we will need to get one more page
    next_page_token = None

    # Loop until all pages are retrieved
    while True:
        request = youtube.playlistItems().list(
            part='snippet',
            playlistId=playlist_id,
            maxResults=50,
            pageToken=next_page_token
        )
        response = request.execute()

        #this will loop x amount of times, x is the amouth of items in the request
        for i in range(len(response['items'])):
            #gets the value of each title
            value = response['items'][i]['snippet']['title']
            #gets the value of each id
            key = response['items'][i]['snippet']['resourceId']['videoId']

            #if the values isnt in the black list it will places both of them into their own lists
            if (value not in blacklist):
                video_titles.append(value)
                video_id.append(key)

        # Check if there are more pages
        next_page_token = response.get("nextPageToken")
        if not next_page_token:
            break

#strip the unneeded characters from the titles
def strip_list_titles(list):
    #makes a temporary copy
    copy_titles = list.copy()
    # and a return list
    list = []

    for t in copy_titles:
        #this will take out every character that we dont need
        list.append(re.sub(r'[^\w\s\u4e00-\u9fff\u3040-\u30ff]', '', t))

    return list

#this will create a new list, that will contain the titles with their id, this is how they will be saved
def add_id_to_title():
    global video_id, video_titles

    ret_titles = []
    for t in range(len(video_id)):
        ret_titles.append(f'{video_titles[t]} -#{video_id[t]}')

    return ret_titles

#Gets the id of the songs
def get_folder_id():
    global folder_titles, folder_id
    for title in folder_titles:
        temp_index = title.find('-#') + 2
        folder_id.append(title[temp_index:])

#Returns the full name the file by ID
def get_full_name(id):
    index_id = folder_id.index(id)

    return f'{folder_titles[index_id]}.mp3'

#----------------------Script--------------------------------------

#we get the playlist id
playlist_id = strip_playlist_url(sys.argv[1])

#sets up the api to be used
handle_api()

#sets up the youtube API connection
youtube = build('youtube', 'v3', developerKey=api_key)

#gets the lists
request_list(playlist_id)

video_titles = strip_list_titles(video_titles)
video_title_id = add_id_to_title()

#checks if the required folders are present, if not it will create them
if not os.path.exists('Songs'):
    os.makedirs('Songs')
    print('Songs folder created!')
if not os.path.exists('Archive'):
    os.makedirs('Archive')
    print('Archive folder created!')

#gets the file names from the folder
folder_titles = os.listdir('Songs')

for title in folder_titles:
    index_title = folder_titles.index(title)
    folder_titles[index_title] = title[:-4]

get_folder_id()

#makes a list of files that are not in the playlist, that it will need to download
for t in video_id:
    if t not in folder_id:
        download_list.append(t)

#print_list(download_list)
for d in download_list:
    try:
        index = video_id.index(d)
        command = f'yt-dlp.exe "https://www.youtube.com/watch?v={d}" --extract-audio --audio-format mp3 -o "Songs/{video_title_id[index]}.%(ext)s"'
        result = subprocess.run(command)
    except subprocess.CalledProcessError as e:
        print("Error:", e)

for id in folder_id:
    if id not in video_id:
        archive_list.append(id)


for i in range(len(archive_list)):
    name = get_full_name(archive_list[i])
    source = f'Songs/{name}'
    print(f'{name} is archived!')
    try:
        shutil.move(source,'Archive')
    except shutil.Error:
        print(f'Error: {name} is already archived!')





youtube.close()
