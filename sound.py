import os
import random
from PyQt5 import QtMultimedia
from pydub import AudioSegment
import json

class Music:
    def __init__(self):
        """ There are 4 moods: happy, neutral, unhappy and dire. Happy should be played at the start of the game
            and when the player is on target in terms of pkms. Unhappy is for when the player is not quite on target
            and dire is for when the player is well below target. Neutral can be used as a transition.
            All songs are tagged with one of the moods and the music object will play songs from the current mood
            randomly until the mood is changed, then transition into songs from the new mood.

            Songs are packaged as mp3 because the file size is smaller, they are converted to wav so that they can
            be played by QT."""
        self.mood = "happy"
        self.playing = False
        self.playlist = []
        self.playlist_position = None
        self.mood_changed = False
        music_dir = os.path.join("assets", "music")
        with open(os.path.join(music_dir, "music_data.json"), encoding="utf-8") as f:
            self.music = json.load(f)
        if not self.music['enable_music']:
            return  # issue #13 workaround, disable mp3 conversion
        for key in self.music:
            if key != "enable_music":
                self.music[key]["path"] = os.path.join(music_dir, key)
                if not os.path.exists(self.music[key]["path"] + ".wav"):
                    if not os.path.exists(self.music[key]["path"] + ".mp3"):
                        print("Missing file, or incorrect name: " + self.music[key]["path"] + ".mp3")
                        print("Music will be disabled")
                        self.music["enable_music"] = False
                    else:
                        print("Converting mp3 file to wav... " + self.music[key]["path"] + ".mp3")
                        sound = AudioSegment.from_mp3(self.music[key]["path"] + ".mp3")
                        sound.export(self.music[key]["path"] + ".wav", format="wav")
                        print("done")
                if os.path.exists(self.music[key]["path"] + ".wav"):
                    self.music[key]["QSound"] = QtMultimedia.QSound(self.music[key]["path"] + ".wav")
                else:
                    del self.music[key]

    def change_mood(self, new_mood):
        if new_mood != self.mood:
            self.mood = new_mood
            self.mood_changed = True
            print(f"mood changed to {self.mood}")

    def make_playlist(self):
        self.playlist = []
        for key in self.music:
            if key != "enable_music":
                if self.music[key]["mood"] == self.mood:
                    self.playlist.append(self.music[key]["QSound"])
        random.shuffle(self.playlist)
        self.playlist_position = 0

    def on_tick(self):
        if not self.music["enable_music"]:
            return
        if not self.playing:
            if len(self.playlist) == 0:
                self.make_playlist()
            self.playlist[self.playlist_position].play()
            self.playing = True
            return
        if self.playlist[self.playlist_position].isFinished():
            self.playlist_position += 1
            if self.mood_changed:
                self.make_playlist()
            if self.playlist_position >= len(self.playlist):
                self.playlist_position = 0
                random.shuffle(self.playlist)
            self.playing = False
            return self.on_tick()
