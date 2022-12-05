import streamlit as st
import pandas as pd
import numpy as np
import requests
import spotipy
import pandas as pd
from spotipy.oauth2 import SpotifyOAuth
from spotipy.oauth2 import SpotifyClientCredentials
import random
from datetime import datetime
import time
import re

st.title('Welcome to Trip.fy')

st.write("You DRIVE, we ENTERTAIN!")

origin = st.text_input("Where will you start your journey?", value="", max_chars=100, key=None, type="default", help="insert the place where you want to start your journey", autocomplete=None, on_change=None, args=None, kwargs=None, placeholder="location where the music starts", disabled=False, label_visibility="visible")

destination = st.text_input("What's your destination?", value="", max_chars=100, key=None, type="default", help="insert the place where you want to end your journey", autocomplete=None, on_change=None, args=None, kwargs=None, placeholder="location where the music ends", disabled=False, label_visibility="visible")

st.date_input("Select the day to start your journey:", value=None, min_value=None, max_value=None, key=None, help=None, on_change=None, args=None, kwargs=None, disabled=False, label_visibility="visible")

st.time_input("Select the time are you plannig to start our journey?", value=None, key=None, help=None, on_change=None, args=None, kwargs=None, disabled=False, label_visibility="visible")

if len(destination)>0:
    api_key='AIzaSyAjirez2NRcM71g6q0S10lu2yndFNP6Vz8'
    url='https://maps.googleapis.com/maps/api/directions/json'
    params={"origin":"", "destination": "", "key": api_key, "departure_time": "now"}
    
    params["origin"] = origin
    params["destination"]=destination

    response=requests.get(url=url, params=params)

    data = response.json()
    data = data['routes'][0]['legs']

    patern = '[A-Z][a-z]+,'
    text = data[0]['end_address']
    destination_clean = re.findall(patern, text)[0].strip(',')
    print('1',destination_clean)
    if destination_clean == 'District':
        patern = '[A-Z][a-z]+ [A-Z][a-z]+,'
        text = data[0]['end_address']
        destination_clean = re.findall(patern, text)[0].strip(',').replace('District', '')
        print('2',destination_clean)

    final_distance = data[0]['distance']['text']
    final_duration = data[0]['duration']['text']

    st.write('distance : ', final_distance)
    st.write('duration : ', final_duration)


    stepsli = []
    for step in data[0]['steps']:
        stepsli.append({'duration': step['duration']['text'],
        'instruction' : step['html_instructions']})

    pat = '[A-Z{2}][0-9+]|[Tt]oll'
    string = 'go to A1 or toll'

    re.findall(pat, string)

    def roadtype(df):
        toll = re.findall(pat, df['instruction'])
        if len(toll) > 0:
            return 'Highway'
        else:
            return 'Urban'
            
    df = pd.DataFrame(stepsli)
    df['Type'] = df.apply(roadtype, axis=1)




    class RoadSegment:
        def __init__(self, timer, road_type):
            self.total_time=timer
            self.type=road_type
            
    def fix_hours(time):
        while time["minutes"]>60:
            time["hours"]+=1
            time["minutes"]-=60
        return time
        
    def count_time(time_string):
        treck_time={"hours":0, "minutes": 0}
        for time in time_string:
            if re.findall('hours*',time):
                d= re.split("hours*", time)
                treck_time["hours"]+=int(d[0])

                d= re.split("mins*", d[1])
                treck_time["minutes"]+=int(d[0])
            else:
                d= re.split("mins*", time)
                treck_time["minutes"]+=int(d[0])
        return fix_hours(treck_time)

    last_road=""
    tracker_counter=0
    df_counter=0
    tracker={}
    time_list= []

    for road_type in df["Type"]:
        if last_road=="":

            last_road=road_type
            time_list.append(df["duration"][df_counter])
            

        elif last_road!=road_type:
            
            tracker[tracker_counter]= RoadSegment(count_time(time_list), last_road)

            time_list = []
            time_list.append(df["duration"][df_counter])
            last_road=road_type
            tracker_counter+=1
            
        else:
            time_list.append(df["duration"][df_counter])

    
        df_counter+=1

    tracker[tracker_counter]= RoadSegment(count_time(time_list), last_road)
    
    final = []
    for tracked in tracker:
        hoursss = int(tracker[tracked].total_time['hours']) * 60
        minutesss = int(tracker[tracked].total_time['minutes']) 
        final.append({'time': hoursss+minutesss, "Road type" : tracker[tracked].type})
    
    final_df = pd.DataFrame(final)
    a = final_df.groupby('Road type').agg({'sum'}).values
    highwaytime = a[0][0]
    urbantime = a[1][0]
    totaltime = highwaytime + urbantime

    print(highwaytime, urbantime, totaltime)
    st.write(final_df)




###################################################### WEATHER FUNCTION ############################################

def get_dist(destiny):
    list_parish = pd.read_excel("list_freguesias.xlsx")
    capital = list_parish.loc[(list_parish["FREGUESIA"] == destiny) | (list_parish["Concelho"] == destiny), "Distrito"].values[0]
    print(capital)
    return capital.capitalize()

def destination_weather(transformed_destiny):
    url = "https://api.ipma.pt/open-data/distrits-islands.json"
    response = requests.get(url=url)
    ipma_loc =  pd.DataFrame(response.json())
    ipma_data = pd.json_normalize(ipma_loc["data"])
    ipma_df_loc = ipma_data[["globalIdLocal", "local"]]
    list_globalidloc = list(ipma_df_loc["globalIdLocal"].values)
    url2 = "http://api.ipma.pt/open-data/forecast/meteorology/cities/daily/"
    ipma_dict = {}
    for idloc in list_globalidloc:
        url =  url2 + str(idloc) + ".json"
        response = requests.get(url = url)
        ipma_dict[idloc] = response.json()
    ipma_df = pd.DataFrame(ipma_dict).T
    ipma_df.reset_index(inplace=True)
    to_bread_df = pd.json_normalize(ipma_df["data"])
    for i in range(len(to_bread_df.columns)-2):
        temp = pd.json_normalize(to_bread_df[i])
        ipma_df = pd.concat([ipma_df, temp], axis=1)
    ipma_clear = ipma_df.drop(columns=["country","data","predWindDir","idWeatherType","classWindSpeed","classPrecInt","dataUpdate","longitude","latitude","index","owner"])
    hoje = ipma_clear.iloc[:,:5]
    amanha = ipma_clear.iloc[:,[0,5,6,7,8]]
    depois_de_amanha = ipma_clear.iloc[:,[0,9,10,11,12]]
    vertical_concat = pd.concat([hoje, amanha, depois_de_amanha], axis=0)
    all_columns = pd.merge(vertical_concat, ipma_df_loc)
    clean_all_col = all_columns[['local','forecastDate', 'tMin', 'tMax', 'precipitaProb']]
    return clean_all_col.loc[clean_all_col['local'] == transformed_destiny]




if len(destination) > 0:
    transformed_destiny = get_dist(destination_clean.upper())
    print(transformed_destiny)
    st.write('Weather:', destination_weather(transformed_destiny))
# transformed_destiny = get_dist("PORTO DE MOS")
# destination_weather(transformed_destiny)


print(origin)
print(destination)

button =st.button("Create SPOTIFY playlist for this trip", key=None, help=None, on_click=None, args=None, kwargs=None, disabled=False)


################################################### SPOTIPY ######################################################


if button:
    secret_file_name = "spotify_creds.txt"

    secrets_dict = {}

    secret_file = open("spotify_creds.txt")

    for line in secret_file:
        key, val = line.split(":")
        secrets_dict[key] = val[:-1]

    secret_file.close()

    sp = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id=secrets_dict["Client ID"],
                                                client_secret=secrets_dict["Client Secret"],
                                                redirect_uri="https://localhost:8080/callback",
                                                scope=["user-library-read,playlist-modify-private,playlist-modify-public,user-read-playback-state,user-modify-playback-state"]))



    username = "1197792253"


    # gets the entire list of genres from Spotify
    genres = sp.recommendation_genre_seeds()



    # defines genre lists for each mood and picks five at random to create the playlist
    city_mood = ['acoustic',
    'ambient',
    'bluegrass',
    'blues',
    'bossanova',
    'chill',
    'classical',
    'piano',
    'r-n-b',
    'rainy-day',
    'soul'
    ]

    open_road_mood = [  'anime',
    'country',
    'folk',
    'funk',
    'groove',
    'happy',
    'holidays',
    'indie-pop',
    'k-pop',
    'party',
    'pop',
    'reggae',
    'rockabilly',
    'romance',
    'sertanejo',
    'show-tunes',
    'summer',
    'world-music'
    ]

    wake_up_mood = ['alt-rock',
    'death-metal',
    'deep-house',
    'electro',
    'electronic',
    'grindcore',
    'hard-rock',
    'heavy-metal',
    'metal',
    'metalcore',
    'power-pop',
    'progressive-house',
    'punk-rock',
    'samba',
    'techno',
    'work-out',
    ]

    wake_up_selection = random.choices(wake_up_mood, k=5)
    open_road_selection = random.choices(open_road_mood, k=5)
    city_selection = random.choices(city_mood, k=5)

    playlist_genre_selection = [city_selection, open_road_selection, wake_up_selection]
    playlist_titles = ["City Mood", "Open Road Mood", "Wake Up! Mood"]



    #gets the predicted time for each segment of the trip to limit the time of the corresponding playlist

    # FROM GOOGLE MAPS API
    # for tracked in tracker:
        
    
    max_dur = [urbantime, highwaytime, totaltime]

    max_duration = []

    for i in max_dur:
        h = int(i/60)
        m = int(i%60)
        max_duration.append(str(h)+":"+str(m))


    print(max_duration)

    max_duration_ms = []

    for i in max_duration:
        ts = datetime.strptime(i, '%H:%M')
        max_duration_ms.append(ts.hour * 3600000 + ts.minute * 60000)

    print(max_duration_ms)



    playlist_ids = []
    for i in range(len(playlist_genre_selection)):
        pl_title = playlist_titles[i]
        md = max_duration_ms[i]
        total_duration = 0
        recs = sp.recommendations(seed_genres=playlist_genre_selection[i], country='PT', limit=100)
        target_playlist = sp.user_playlist_create(username, name=pl_title)
        rec_id_list = []
        j = 0
        while total_duration < md:
            rec_id_list.append(recs["tracks"][j]["id"])
            total_duration += recs["tracks"][j]["duration_ms"]
            j += 1
        sp.playlist_add_items(target_playlist["id"], rec_id_list)
        playlist_ids.append(target_playlist["id"])

    try:
        device_list = sp.devices()

        sp.start_playback(device_id=device_list["devices"][0]["id"], context_uri="spotify:playlist:"+target_playlist["id"])
    except:
        print('nothing')




