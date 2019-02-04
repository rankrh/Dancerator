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
import click

# Defines Spotify API credentials
# Constants

def get_user_playlists(userid):
    # Gets playlist data from Spotify
    playlist_data = spotify.user_playlists(userid)
    playlist_names = dict()
    check_dups = list()

    return playlist_data

def select_playlist(playlist_data):
    playlist_names = dict()
    check_dups = list()

    # Creates dictionary of playlist name and uri
    for n in range(len(playlist_data['items'])):
        playlist_id = (playlist_data['items'][n]['uri'])
        playlist_name = playlist_data['items'][n]['name']
        if playlist_name in check_dups:
            playlist_name += ' - ' + str(check_dups.count(playlist_name) + 1)
        check_dups.append(playlist_name)
        playlist_names[playlist_name] = playlist_id

    # Prompts user to choose a playlist to order
    if len(playlist_names) > 0:
        print('Your Playlists Are:')
        print()
        for plist in playlist_names:
            print(plist)
        while True:
            print()
            choice = input('Which playlist would you like to order? ')
            # Checks for input
            if choice == '':
                return None
            # Checks if choice is in the dictionary
            elif choice in playlist_names:
                # If so, returns URI
                playlist = spotify.user_playlist(
                    username,
                    playlist_names[choice])
                # Prompts user for a different name
                text = (f"Default playlist name is '{choice} - Reordered'.  " +
                        "Hit ENTER to accept, or type a new name: ")
                name = input(text)
                # If no name give, uses default
                if len(name) == 0:
                    name = choice + ' - Reordered'

                return playlist, name
            else:
                print("Playlist {} not found.".format(choice))

def get_features(playlist):
    """ Gets track titles, URIs, and attributes from spotify and creates
    a pandas dataframe.

    Spotify's 'Acoustic Attributes' are data about tracks that reflect
    either definite traits about the track or probabilities that a track fits
    certain parameters.  This function inputs all of the availiable attributes
    into a pandas dataframe, but we are primarily interested in danceability,
    track duration, loudness, and tempo.  Danceability ranges from 0 to 1,
    1 being more danceable. Song duration is measured in milliseconds.
    Loudness measures song in dB, averaged across song and is typically
    between -60 and 0 dB.  Tempo is measured in BPM.

    Args:
        playlist(str): Spotify ID for a playlist

    Returns:
        tracks_df(pandas dataframe): Dataframe that holds track names,acoustic,
                                    features and uris for all the tracks in
                                    a given playlist
    """

    track_data = playlist['tracks']['items']
    playlist_name = playlist['name']

    # List that holds all track data before converting to a pandas dataframe
    tracks = list()
    # Loops through the information on the playlist
    # 'n' refers to the track position
    for n in range(len(track_data)):
        # Track names are not held in the same place as acoustic features,
        # which we are more interested in.
        track_name = track_data[n]['track']['name']
        # URI is held there, but we need to pull it out to look up
        # the acoustic attributes
        track_uri = track_data[n]['track']['uri']
        # A list of all of spotify's acoustic attributes for a track,
        # including 'danceability', 'tempo', etc.
        feats = spotify.audio_features(track_uri)[0]
        # Adds name and playlist name to the dict
        feats['name'] = track_name
        feats['playlist name'] = playlist_name
        tracks.append(feats)

    # Converts to a dataframe
    tracks_df = pd.DataFrame(tracks)

    return tracks_df

def sort_tempo(track_df, period):
    """ Returns an organized dataframe based on tempo.

    For dance playlists there should be a periodic range in tempos, with
    slow songs appearing roughly every ten songs.  This function splits the
    dataframe into sections of one period of this wave, then sorts them to
    create an overall periodicity in the dataframe with regard to tempo.

    Args:
        track_df(pandas dataframe): track data

    Returns:
        all_tracks(pandas dataframe): sorted based on track tempo
    """

    # Finds the number of distinct sections for the final playlist
    sections = (len(track_df) // period) + 1  # Equal to number of peaks

    # Sorts the dataframe lowest to highest in place by tempo
    track_df.sort_values(by='tempo', inplace=True)

    x = 0
    track_sections = [[]] * sections
    # Divides the dataframe into sections and stores each as a df in a list
    for n in range(sections):
        track_sections[n] = track_df.iloc[x::sections]
        x += 1

    sections_sorted = list()
    for section in track_sections:
        # Creates the wave form by splitting each section in half
        # and reversing one of them.  When re-combined, the result is a
        # single peak, with troughs at the first and last position.
        even = section.iloc[::2]
        odd = section.iloc[1::2]
        odd = odd.iloc[::-1]
        # Recombine ascending and descending lines.
        sections_sorted.append(pd.concat([even, odd]))

    # Recombine sections
    all_tracks = pd.concat(sections_sorted)
    all_tracks.reset_index(inplace=True)

    index_list = list()
    for x in range(len(all_tracks)):
        index_list.append(x // 10)
    all_tracks['tempo group'] = index_list

    return all_tracks

def sort_danceability(track_df, period):
    """ Edits the dataframe to include danceability as a metric, slowly
    decreasing as the playlist goes on.

    In general, the trend of the playlist should be from high danceability
    to low danceability, but the wave-like form of the tempo should be
    preserved as much as possible.  This function orders tracks at
    symmetrical parts of the wave in order from highest to lowest
    danceability.  While the tempo wave-form is partially destroyed in the
    process, the overall periodic variablity is maintained.

    Args:
        track_df(pandas dataframe): Dataframe of track attributes

    Returns:
        all_tracks(pandas dataframe): Updated dataframe based on danceability
    """

    # Divide list into sections based on position in playlist
    # Each peak, trough, and equivalent other wave sections are
    # grouped together
    sublists = list()
    for n in range(period):
        # Explicitly returns a copy to avoid SettingWithCopyWarning
        sublists.append(track_df[n::period].copy())

    # Order the sections based on danceability
    for lst in sublists:
        # Sort the sections, then preserve the order as a column
        lst.sort_values(by='danceability', ascending=False, inplace=True)
        lst['danceability group'] = [x for x in range(len(lst))]

    all_tracks = pd.concat(sublists)
    all_tracks.sort_values(by=['danceability group', 'tempo group'],
                        inplace=True)
    return all_tracks

def commit_playlist(playlist, userid, name):
    """ Creates a new playlist on the user's Spotify account with the
    ordered tracks as given.

    Args:
        playlist(pandas dataframe): ordered list of track attributes
        userid(string): unique Spotify ID number related to account

    Returns:
        Spotify playlist
        message(str): Reports status
    """
    # Gets uris as a df
    track_uris = playlist['uri']
    # Creates a new playlist on the user's account
    try:
        spotify.user_playlist_create(userid,
                                    name,
                                    public=False)
    except Exception as e:
        if debug:
            print(str(e))
        raise

    # Gets uri of just created playlist
    playlist_data = spotify.user_playlists(userid)
    playlist_id = None
    playlist_url = None

    for playlist_item in playlist_data['items']:
        if playlist_item['name'] == name:
        # Breaks loop after finding the first of the playlists and storing
        # the uri and url
        # There may be different playlists witht the same name, but
        # Spotify orders by date created, so the most recent one will be the
        # playlist just created.
            playlist_id = playlist_item['uri']
            playlist_url = playlist_item['external_urls']['spotify']
            break

    if playlist_id is not None:
        try:
            # Adds tracks to the playlist just created
            spotify.user_playlist_add_tracks(userid,
                                            playlist_id,
                                            [uri for uri in track_uris])
            # Prints track listing
            print('Playlist tracks are:')
            for n in playlist['name']:
                print(n)
            # Prints URL of playlist
            if playlist_url is not None:
                message = f"Your new playlist '{name}' can be found at: \n {playlist_url}"
                print(message)

        except Exception as e:
            if debug:
                print(str(e))
            raise


@click.command()
@click.argument('username')
@click.argument(
    'period',
    type=click.INT,
    default=10)
@click.argument(
    'client-id',
    type=click.STRING,
    default=os.environ['SPOTIFY_ID'])
@click.argument(
    'client_token',
    type=click.STRING,
    default=os.environ['SPOTIFY_SECRET'])
@click.argument(
    'redirect',
    type=click.STRING,
    default='http://localhost:8888/callback')
@click.option(
    '--trace/--no-trace',
    default=False,
    help="Enable low level tracing")
def dancerate(username, period, client_id, client_token, redirect, trace):
    SCOPE = ('user-library-modify ' 
         'playlist-modify-private ' 
         'playlist-read-private ' 
         'playlist-read-collaborative ')

    debug = trace

    # Attempts to authenticate
    token = util.prompt_for_user_token(
            username, SCOPE, 
            client_id=client_id,
            client_secret=client_token,
            redirect_uri=redirect)
    if token:
        spotify = spotipy.Spotify(auth=token)
    else:
        print("Can't get token for", username)
        return
    try:    
        userid = spotify.me()['id']
        playlist_data = get_user_playlists(userid)
        if playlist_data is None:
            print('Leaving Dancerator')
            return
        playlist = select_playlist(playlist_data)
        data = playlist[0]
        name = playlist[1]
        playlist = get_features(data)
        playlist = sort_tempo(playlist, period)
        playlist = sort_danceability(playlist, period)
        commit_playlist(playlist, userid, name)
    
    except Exception as e:
        if debug:
            print(str(e))
        print('Dancerator encountered an error.')
        return


if __name__ == '__main__':
    dancerate()