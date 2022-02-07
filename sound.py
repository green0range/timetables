from PyQt5.QtMultimedia import QSound


class Music:
    def __init__(self):
        self.a = QSound("assets/music/AcousticRock.wav")
        #self.a.play()

    def play(self):
        self.a.play()