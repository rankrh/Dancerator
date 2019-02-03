# -*- coding: utf-8 -*-
"""
Created on Sun Nov  4 16:44:11 2018

@author: Bob

This program takes a user-created Spotify playlist and orders it into an
optimal dancing playlist.  

The Spotify API includes track data including tempo, 'danceability',
 track length, and track loudness, among others.
"""

import spotipy
import spotipy.util as util
import pandas as pd
import os

# Defines Spotify API credentials
# Constants
SCOPE = ('user-library-modify ' 
         'playlist-modify-private ' 
         'playlist-read-private ' 
         'playlist-read-collaborative ')
CLIENT_ID = os.environ['SPOTIFY_ID']
SECRET = os.environ['SPOTIFY_SECRET']
REDIRECT = "http://localhost:8888/callback"

# User information
### Needs to be customizeable ###
username = input("Username: ")

# Creates and authenticates token 
token = util.prompt_for_user_token(
        username, SCOPE, 
        client_id=CLIENT_ID,
        client_secret=SECRET,
        redirect_uri=REDIRECT)

def main():
    print('Welcome to the Dancerator')
    print()
    
if __name__ == "__main__":
    spotify = spotipy.Spotify(auth=token)
    main()
    
# Finds the user ID - Note that this is an identifier unique from the username
userid = spotify.me()['id']

def get_playlists(userid):
    """Gets a list of all user playlists, then prompts user to choose which
    playlist they want to edit.
    
    Args:
        userid(str): Spotify User ID
    
    Returns:
        playlist URI
    """
    
    # Gets playlist data from Spotify
    playlist_data = spotify.user_playlists(userid)
    playlist_names = dict()
    
    # Creates dictionary of playlist name and uri
    for n in range(len(playlist_data['items'])):
        playlist_id = (playlist_data['items'][n]['uri'])
        playlist_name = playlist_data['items'][n]['name']
        playlist_names[playlist_name] = playlist_id
    
    if len(playlist_names) > 0:
        print('Your Playlists Are:')
        print()
        # Prints keys and asks user to pick a list
        for plist in playlist_names:
            print(plist)    
        while True:
            print()
            choice = input('Which playlist would you like to order? ')
            # Checks for input
            if choice == '':
                break
            # Checks if choice is in the dictionary
            elif choice in playlist_names:
                # If so, returns URI
                return playlist_names[choice]
            
            else:
                print('Error: Playlist not found.')

def get_features(playlist):
    """ Gets track titles, URIs, and attributes from spotify and creates 
    a dictionary.
    
    Args:
        playlist(dict): Spotify dictionary of playlist attributes
        
    Returns:
        dictionary
    """
    tracks = list()
    # Loops through the information on the playlist
    # 'n' refers to the track position
    for n in range(len(playlist['tracks']['items'])):
        # Finds track title and URI
        tracks.append({})
        track_name = playlist['tracks']['items'][n]['track']['name']
        track_uri = playlist['tracks']['items'][n]['track']['uri']
        tracks[n]['Name'] = track_name
        tracks[n]['URI'] = track_uri
        feats = spotify.audio_features(track_uri)[0]
 
        # Finds audio features for the tracks
        if 'danceability' in feats:
            # Danceability ranges from 0 to 1, 1 being more danceable       
            dance = feats['danceability']
            tracks[n]['Danceability'] = dance
        else:
            tracks[n]['Danceability'] = None
        if 'duration_ms' in feats:            
            # Song duration is measured in milliseconds
            length = feats['duration_ms']
            tracks[n]['Length'] = length
        else:
            tracks[n]['Length'] = None
        if 'loudness' in feats:
            # Loudness measures song in dB, averaged across song
            # and is typically between -60 and 0 dB
            loudness = feats['loudness']
            tracks[n]['Loudness'] = loudness
        else:
            tracks[n]['Loudness'] = None
        if 'tempo' in feats:    
            # Tempo is measured in BPM 
            tempo = feats['tempo']
            tracks[n]['Tempo'] = tempo
        else:
            tracks[n]['Loudness'] = None
        
    return pd.DataFrame(tracks)
    