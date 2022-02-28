import json
import os

import numpy as np
from PIL import Image, ImageQt, ImageDraw, ImageFont
import time
import datetime
import logging
logger = logging.Logger(name="main")
logger.setLevel(logging.DEBUG)
import achievements

class Score:
    """ The game is scored using passenger kilometres. 1 passenger kilometres means 1 passenger was transported 1 km.
        2 passenger km mean either 1 passenger was transported 2 km, or 2 passengers transported 1 km, etc.

        The goal of the game get 100,000,000 passenger kilometres before 2050, with the allocated budget."""
    def __init__(self):
        self.current_pkm = 0.0
        self.highscores = []  # this should be loaded and saved with player's name etc. maybe online scores?
        self.year = 2020
        self.previous_pkms = [0.0]
        self.goals = [100000, 400000, 3200000, 12800000, 38400000, 76800000, 153600000, 199680000, 259584000, 300000000,
                      360000000, 396000000, 435600000, 457380000, 480249000, 504261450, 529474522, 555948248, 583745661,
                      612932944, 643579591, 675758570, 709546499, 745023824, 782275015, 821388766, 862458204, 905581114,
                      950860170, 1000000000]
        self.goals_achieved = [False] * len(self.goals)
        self.buffer = 0

    def increase(self, amount):
        self.current_pkm += amount

    def put_on_buffer(self, amount):
        """ This exists so that a run can be simulated and the pkms tentatively added, before the accounting
            is confirmed. Once accounting is confirmed, the service just has to push the buffer with needing to
            store the pkms."""
        self.buffer += amount

    def push_buffer(self):
        self.increase(self.buffer)
        self.buffer = 0

    def get_score(self):
        return np.round(self.current_pkm, 0)

    def get_lastyear_score(self):
        index = self.year - 2020
        return np.round(self.previous_pkms[index], 0)

    def update_time(self, time):
        if time.year != self.year:
            assert time.year == self.year + 1  # the year must not increase by more than 1 at a time
            self.year = time.year
            if self.current_pkm >= self.goals[self.year - 2020]:
                self.goals_achieved[self.year - 2020] = True
            self.previous_pkms.append(self.current_pkm)
            self.current_pkm = 0.0


class Wallet:
    def __init__(self, starting_amount=5e10):
        self.file = None
        self.money = starting_amount
        self.overdraft = 0
        self.overdraft_interest_rate = 0.1
        self.account_records = []
        self.save_manager = None

    def get_balance(self):
        return np.round(self.money, 2)

    def addsubtract(self, amount, datestr, details="No transaction details recorded"):
        if len(self.account_records) > 20:  # stop using too much memory
            self.save_records()
        if amount > 0:
            return self.deposit(amount, details, datestr)
        elif amount < 0:
            return self.withdraw(amount, details, datestr)  # note the negative withdrawal error will be corrected in the withdraw method
        else:
            return True  # no money to add so no transaction

    def withdraw(self, amount, details, date):
        amount = np.abs(amount)  # if you want to withdraw a negative amount, use a deposit!
        if self.money + self.overdraft >= amount:
            self.money -= amount
            self.account_records.append([date, "withdrawal", amount, details])
            return True  # withdrawal successful
        else:
            return False  # withdrawal failed

    def deposit(self, amount, details, date):
        amount = np.abs(amount)  # if you want to deposit a negative amount, use a withdrawal!
        self.money += amount
        self.account_records.append([date, "deposit", amount, details])
        return True

    def get_records(self):
        file_records = []
        if os.path.exists(self.file):
            with open(self.file, "r") as f:
                records = f.readlines()
            for record in records:
                file_records.append(record.strip(" \n").split(","))
        return file_records + self.account_records

    def set_save_dir(self, sm):
        self.save_manager = sm

    def save_records(self):
        txt = ""
        for entry in self.account_records:
            txt += f"{entry[0]}, {entry[1]}, {entry[2]}, {entry[3]}\n"
        del self.account_records
        self.account_records = []
        self.save_manager.save_data("monies.csv", txt, append_mode=True)

class ServiceColours:
    def __init__(self):
        self.current_number = 0
        self.colours = [(36,160,167),
                        (8,194,157),
                        (78,208,122),
                        (238,222,120),
                        (238, 120, 120),
                        (13,73,70),
                        (34,108,81),
                        (255,145,77),
                        (170,50,50),
                        (109,109,109),
                        (150, 45, 62),
                        (151, 156, 156),
                        (52, 136, 153),
                        (136, 247, 226),
                        (68, 212, 146),
                        (245, 235, 103),
                        (255, 161, 92),
                        (250, 35, 62)
                        ]
        self.routes = []

    def get_colour_number(self, route):
        self.routes.append(route)
        a = self.current_number
        self.current_number += 1
        return a

    def remove(self, route):
        for i in range(len(self.routes)):
            if self.routes[i] is route:
                self.routes[i] = "DEFUNCT"


def get_sort_key(t):
    return t.population


class Map:
    def __init__(self, width, height, towns, wallet, score, colours):
        with open(os.path.join("assets", "coastline_data.json"), "r", encoding='utf-8') as f:
            self.coastline_data = json.load(f)
        self.map_image = None
        self.map_image_needs_update = True
        self.img = Image.new("RGBA", (width, height), color=(255, 255, 255, 255))
        self.game_time = datetime.datetime.strptime("01012020 0000", "%d%m%Y %H%M")
        self.tick_rate = 0.99
        self.wallet = wallet  # we need a pointer to the wallet to know what acc balance to display
        self.score = score
        self.colours = colours
        self.time_increment = datetime.timedelta(days=1)
        self.connection_ids = []
        self.connection_colours = []
        self.town_draw_name = []
        self.town_draw_name_complete = False
        self.achievement_display_text = ""
        self.achievement_display_counter = 0
        self.legend_key = []
        self.legend_colour = []
        '''These represent the bounding latitude and longutiude of the area of the world we want to
            draw. Needs to be altered for each country
            
            todo: externalise bounding boxes to a file which is loaded so versions can be made for other countries'''
        self.bounding_box_aotearoa = [166, 178.6, -47, -34]
        self.bounding_box_te_waipounamu = [166, 175, -47, -40.4]
        self.bounding_box_te_ika = [173, 178.6, -41.5, -34]
        self.percent_connected = 0.0
        self.current_bounding_box = self.bounding_box_aotearoa
        self.towns = towns
        self.towns.sort(reverse=True, key=get_sort_key)
        self.report_mode = False
        self.redraw()
        self.about_to_skip_year = False
        self.previous_time_increment = None
        self.win_conditions = achievements.Conditions()

    def skip_year(self):
        new_year = self.game_time.year + 1
        self.previous_time_increment = self.time_increment
        self.time_increment = datetime.datetime.strptime(f"01-01-{new_year} 00:00", "%d-%m-%Y %H:%M") - self.game_time
        self.about_to_skip_year = True
        return new_year


    def update_connection_ids(self):
        """ This creates connection ids (of form `Dunedin-Mosgiel` etc) used to identify which colours to
                    use when drawing links between towns."""
        self.connection_ids = []
        self.connection_colours = []
        for (col, route) in zip(self.colours.colours, self.colours.routes):
            if route != "DEFUNCT":
                startNode = route.stations[0]
                endNode = route.stations[len(route.stations) - 1]
                path = startNode.getNodesOnPath(endNode)
                for i in range(1, len(path)):
                    self.connection_ids.append(path[i - 1].get_name() + '-' + path[i].get_name())
                    self.connection_colours.append(col)
        self.map_image_needs_update = True
        self.redraw()

    def load_wallet_score(self, wallet, score):
        """This is for reloading the wallet and score after unpickling them"""
        self.wallet = wallet
        self.score = score

    def change_bounding_box(self, id):
        if id == "north":
            self.current_bounding_box = self.bounding_box_te_ika
        elif id == "south":
            self.current_bounding_box = self.bounding_box_te_waipounamu
        elif id == "nz":
            self.current_bounding_box = self.bounding_box_aotearoa
        self.map_image_needs_update = True

    def convert_latlgn_to_xy(self, latlgn):
        deltaX = self.current_bounding_box[1] - self.current_bounding_box[0]
        deltaY = self.current_bounding_box[3] - self.current_bounding_box[2]
        x = self.img.width * (latlgn[1] - self.current_bounding_box[0]) / deltaX
        y = self.img.height * (1 - (latlgn[0] - self.current_bounding_box[2]) / deltaY)
        return x, y

    def update_percent_connected(self, fraction):
        self.percent_connected = fraction * 100

    def get_increment(self):
        return self.time_increment

    def get_time(self):
        return self.game_time

    def change_speed(self, state):
        if state:
            self.time_increment = datetime.timedelta(days=(18250 / (3600 * self.tick_rate)))
        else:
            self.time_increment = datetime.timedelta(days=1)

    def get_connection_colour(self, connection_id):
        connection_reversed = connection_id.split("-")[1] + "-" + connection_id.split("-")[0]
        colours_for_this_connection = []
        for (conn, col) in zip(self.connection_ids, self.connection_colours):
            if connection_id == conn:
                colours_for_this_connection.append(col)
            if connection_reversed == conn:
                colours_for_this_connection.append(col)
        if len(colours_for_this_connection) == 0:
            return None
        else:
            return colours_for_this_connection

    def add_legend(self, key, colour):
        if not key in self.legend_key:
            self.legend_key.append(key)
            self.legend_colour.append(colour)

    def draw_coastlines(self):
        coastline_map = Image.new("RGBA", (self.img.width, self.img.height), color=(255, 255, 255, 0))
        draw_map = ImageDraw.Draw(coastline_map)
        for island in self.coastline_data:
            for i in range(1, len(self.coastline_data[island])):
                coord1 = self.coastline_data[island][i]
                coord0 = self.coastline_data[island][i-1]
                x0, y0 = self.convert_latlgn_to_xy(coord0)
                x1, y1 = self.convert_latlgn_to_xy(coord1)
                draw_map.line((x0, y0, x1, y1), fill=(41, 182, 246), width=1)
        return coastline_map


    def redraw(self):
        t = self.game_time.strftime("%d/%m/%Y, %H:%M")
        money = "${:,}".format(self.wallet.get_balance())
        score = "{:,} pkm this year, {:,} pkm last year".format(self.score.get_score(), self.score.get_lastyear_score())
        percent_connected = "{:.1f} % towns serviced".format(self.percent_connected)
        font = ImageFont.truetype(os.path.join('assets', 'fonts', 'Raleway-Medium.ttf'), 12)
        font2 = ImageFont.truetype(os.path.join('assets', 'fonts', 'Arvo-Bold.ttf'), 14)
        if self.map_image_needs_update:
            coastline_map = self.draw_coastlines()
            self.map_image_needs_update = False
            self.map_image = Image.new("RGBA", (self.img.width, self.img.height), color=(255, 255, 255, 0))
            Image.Image.paste(self.map_image, coastline_map)
            draw_map = ImageDraw.Draw(self.map_image)
            for town in self.towns:
                x, y = self.convert_latlgn_to_xy(town.get_latlgn())
                draw_map.ellipse((x - 2, y - 2, x + 2, y + 2), fill=(200, 200, 200), outline=(0, 0, 0))
                '''If there are nearby towns, we only draw the text for the most populus town.'''
                if not self.town_draw_name_complete:
                    should_add = True
                    for town2 in self.town_draw_name:
                        x2, y2 = self.convert_latlgn_to_xy(town2.get_latlgn())
                        w, h = font.getsize(town.get_name())
                        if x-w-10 < x2 < x+w+10 and y-h/2-10 < y2 < y+h/2+10:
                            should_add = False
                    if should_add:
                        self.town_draw_name.append(town)
                for conn in town.connections:
                    connection_id = town.get_name() + '-' + conn[0].get_name()
                    x2, y2 = self.convert_latlgn_to_xy(conn[0].get_latlgn())
                    line_colour = self.get_connection_colour(connection_id)
                    if line_colour is None:
                        draw_map.line((x, y, x2, y2), fill=(200,200,200), width=1)
                        self.add_legend("Unused track", (200, 200, 200))
                    else:
                        """So we should get the normal vector and draw a colourline at intevals spaced along the normal vecto"""
                        connection_vector = np.array([x-x2, y-y2])
                        normal_vector = np.array([1, -connection_vector[0]/connection_vector[1]])
                        normal_vector /= np.linalg.norm(normal_vector)  # normalise the vector
                        normal_vector *= 3  # we want to 3 pixels between each coloured connection line.
                        for i, colour in enumerate(line_colour):
                            draw_map.line((x + i*normal_vector[0], y + i*normal_vector[1], x2 + i*normal_vector[0],
                                           y2 + i*normal_vector[1]), fill=colour, width=2)
            for town in self.town_draw_name:
                x, y = self.convert_latlgn_to_xy(town.get_latlgn())
                w, h = font.getsize(town.get_name())
                draw_map.text((x, y-h/2), town.get_name(), font=font, fill=(0, 0, 0, 255))
            for i, (key, colour) in enumerate(zip(self.legend_key, self.legend_colour)):
                draw_map.text((100,300+(i*30)), key, font=font, fill=(0, 0, 0, 255))
                draw_map.rectangle((90,300+(i*30) - 2, 98, 300+(i*30) + 2), colour)
            self.town_draw_name_complete = True  # it will only generate the list (expensive) on first run
        self.img = Image.new("RGBA", (self.img.width, self.img.height), color=(255, 255, 255, 0))
        Image.Image.paste(self.img, self.map_image)
        draw = ImageDraw.Draw(self.img)
        draw.text((100,50), t, font=font2, fill=(0, 0, 0, 255))
        draw.text((300,50), money, font=font2, fill=(0, 0, 0, 255))
        draw.text((100, 100), score, font=font2, fill=(0,0,0,255))
        draw.text((100, 150), percent_connected, font=font2, fill=(0, 0, 0, 255))
        if self.achievement_display_counter > 0:
            draw.text((int(self.img.width/2)-100, self.img.height - 100), self.achievement_display_text, font=font2, fill=(0, 0, 0, 255))

    def display_new_achievement(self, achieves, dont_add_preamble=False):
        if len(achieves) > 0:
            self.achievement_display_text = ""
            for ach in achieves:
                if dont_add_preamble:
                    self.achievement_display_text += ach + "\n"
                else:
                    self.achievement_display_text += "Achievement Completed: " + ach + "\n"
            self.redraw()
            self.achievement_display_counter = 8

    def update_time(self, tick_rate):
        self.game_time += self.time_increment
        if self.about_to_skip_year:
            self.about_to_skip_year = False
            self.time_increment = self.previous_time_increment
        self.redraw()
        self.score.update_time(self.game_time)
        if self.achievement_display_counter > 0:
            self.achievement_display_counter -= 1
        return self.win_conditions.do_checks(self.game_time, self.percent_connected, self.score)

    def get_image_qt(self):
        return ImageQt.toqimage(self.img)

