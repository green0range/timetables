import datetime
import os

def get_objectives():
    path = os.path.join("assets", "objective")
    objectives = [0]*4
    with open(path, "r", encoding='utf-8') as f:
        objectives[0] = int(f.readline())
        objectives[1] = int(f.readline())
        objectives[2] = int(f.readline())
        objectives[3] = int(f.readline())
    return objectives

class Conditions:
    """Conditions are required to win the game / pass on to the next section"""

    def __init__(self):
        pass

    def do_checks(self, date, percent_connected, score):
        if date.year == 2030:
            return self.check_2030(date, percent_connected, score)
        elif date.year == 2050:
            return self.check_2050(date, percent_connected, score)
        else:
            return "P"

    def check_2030(self, date, percent_connected, score):
        if percent_connected >= 70:
            if score.get_lastyear_score() >= 300000000:
                return "P"
            else:
                return "F TRANSPORTED LESS THAN 300,000,000pkm/yr BY 2030"
        return "F LESS THAN 70% OF TOWNS CONNECTED BY 2030"

    def check_2050(self, date, percent_connected, score):
        if percent_connected >= 90:
            if score.get_lastyear_score() >= 600000000:
                return "W"
            else:
                return "F TRANSPORTED LESS THAN 600,000,000pkm/yr BY 2050"
        return "F LESS THAN 90% OF TOWNS CONNECTED BY 2050"


class Achievements:
    """Achievements are optional, but provide goals and challenges to players"""

    def __init__(self):
        self.achievements = {"Service to the republic": "Establish a service which stops in Whangamōmona",
                             "MOAR TRACTION": "Use two engines in one of your trains",
                             "Sleeping service": "Establish and overnight service",
                             "Through the mountains": "Connect the east and west coast across the Southern Alps",
                             "A True Coaster": "Run a train that stays entirely on the West Coast",
                             "SUPERCITY": "Run a train that stops in Auckland",
                             "Capital Connection": "Run a train between Wellington and Palmerston North",
                             "The far east": "Connect Gisbourne to your network",
                             "North to south": "Connect the most northern and southern towns using only 2 services",
                             "Express service": "Establish an express train which bypasses at least 5 towns.",
                             "Remembered Worlds": "Use the Stratford-Okahukura Line",
                             "We ran out of colours!": "Use the entire colour palette",
                             "Rapid transit": "Create a service that runs every 15 minutes",
                             "Share with your MP": "Write a lovely letter to your member of parliment explaining why we need more investment in rail. We can't tell if you actually did it or not, so we'll just cross it off and pretend you have. Who am I kidding, this is just a political message pretending to be a (pretty bad) video game anyway."
                             }
        self.completed_achievements = ["Share with your MP"]
        self.east_coast = ["Christchurch", "Invercargill", "Edendale", "Gore", "Balclutha", "Milton", "Mosgiel",
                      "Dunedin", "Waikouaiti", "Palmerston", "Ōamaru", "Timaru", "Ashburton", "Rolleston",
                      "Rangiora", "Amberley", "Waipara", "Arthur's Pass Village", "Springfield", "Darfield",
                      "Kaikōura", "Blenheim", "Picton", "Seddon"]
        self.west_coast = ["Greymouth", "Moana", "Ōtira", "Westport", "Īnangahue", "Reefton", "Ahaura", "Ikamatua",
                      "Kūmara", "Hokitika"]
        self.known_services = []

    def get_all_achievements(self):
        return self.achievements

    def get_completed_achievements(self, list_of_services):
        """
        Finds all completed achievements, regardless of whether they have been reported before.
        :param list_of_services: service or list of services to check achievements against
        :return: list of keys for which the achievement has been completed.
        """
        completed = []
        for key in self.achievements:
            if key in self.completed_achievements:
                completed.append(key)
            elif self.check_achievement_complete(key, list_of_services):
                completed.append(key)
        self.completed_achievements = completed
        return completed

    def check_for_new_achievement(self, service):
        """
        Find newly completed achievements, that have never been reported before.
        :param service: service (or list of) which may have completed a new achievement
        :return: list of newly completed services.
        """
        if service not in self.known_services:
            self.known_services.append(service)  # we need a full list for achievements that are context dependent
        new = []
        for key in self.achievements:
            if key in self.completed_achievements:
                pass
            elif self.check_achievement_complete(key, service):
                new.append(key)
                self.completed_achievements.append(key)
        return new



    def check_achievement_complete(self, achievement_name, service):
        """
        Checks if the given achievement has been completed.
        :param achievement_name: str: name of achievement / key in the self.achievements dict
        :param service: list of services, or single service. Checks if the service(s) forefill the requirements
                        of the achievement.
        :return: boolean: True if achievement is completed
        """
        if not type(service) is list:
            service = [service]
        if achievement_name == "Service to the republic":
            for s in service:
                for town in s.get_stations():
                    if town.get_name() == "Whangamōmona":
                        return True
        elif achievement_name == "MOAR TRACTION":
            for s in service:
                if s.config[0] == 2:
                    return True
        elif achievement_name == "Sleeping service":
            daytime = [datetime.time(7), datetime.time(19)]
            for s in service:
                if s.config[2] > 0:
                    for dt in s.departure_times:
                        if not daytime[0] <= dt.time() <= daytime[1]:
                            return True
        elif achievement_name == "Through the mountains":
            for s in service:
                stops_in_east = False
                stops_in_west = False
                for town in s.get_stations():
                    if town.get_name() in self.east_coast:
                        stops_in_east = True
                    elif town.get_name() in self.west_coast:
                        stops_in_west = True
                if stops_in_east and stops_in_west:
                    return True
        elif achievement_name == "A True Coaster":
            for s in service:
                stops_in_east = False
                stops_in_west = False
                for town in s.get_stations():
                    if town.get_name() in self.east_coast:
                        stops_in_east = True
                    elif town.get_name() in self.west_coast:
                        stops_in_west = True
                if stops_in_west and not stops_in_east:
                    return True
        elif achievement_name == "SUPERCITY":
            for s in service:
                for town in s.get_stations():
                    if town.get_name() == "Auckland":
                        return True
        elif achievement_name == "Capital Connection":
            for s in service:
                goes_to_wellington = False
                goes_to_palmy = False
                for town in s.get_stations():
                    if town.get_name() == "Wellington":
                        goes_to_wellington = True
                    if town.get_name() == "Palmerston North":
                        goes_to_palmy = True
                if goes_to_palmy and goes_to_wellington:
                    return True
        elif achievement_name == "The far east":
            """By must connect back to your network, I mean
                it must connect to one other line that is not the Gisbourne line"""
            gizy_line = None
            for s in service:
                for station in s.get_stations():
                    if station.get_name() == "Gisbourne":
                        gizy_line = s
                        break
            if gizy_line is not None:
                for s in service:
                    if not s is gizy_line:
                        for station in s.get_stations():
                            for station2 in gizy_line.get_stations():
                                if station == station2:
                                    return True
        elif achievement_name == "North to south":
            north_is = False
            south_is = False
            for s in self.known_services:
                picton = False
                invers = False
                wellington = False
                hikurangi = False
                for station in s.get_stations():
                    if station.get_name() == "Picton":
                        picton = True
                    if station.get_name() == "Invercargill":
                        invers = True
                    if station.get_name() == "Wellington":
                        wellington = True
                    if station.get_name() == "Hikurangi":
                        hikurangi = True
                if picton and invers:
                    south_is = True
                if wellington and hikurangi:
                    north_is = True
            if north_is and south_is:
                return True
        elif achievement_name == "Express service":
            for s in service:
                stations = s.get_stations()
                if len(stations) == 2 and len(stations[0].getNodesOnPath(stations[1])) > 5:
                    return True
        elif achievement_name == "Remembered Worlds":
            for s in service:
                stations = s.get_stations()
                """ We need all the towns along the line - even the ones where the train doesn't stop."""
                all_towns = stations[0].getNodesOnPath(stations[len(stations)-1])
                for town in all_towns:
                    if town.get_name() == "Whangamōmona":
                        return True
        elif achievement_name == "We ran out of colours!":
            if len(self.known_services) > 17:
                """ All the colours are hard-coded in the style sheet. There are 18, if we run out, it will just use
                    a default colour (probably white) for the route."""
                return True
        elif achievement_name == "Rapid transit":
            for s in service:
                if len(s.departure_times) >= 2:
                    if s.departure_times[1] - s.departure_times[2] <= datetime.timedelta(minutes=15):
                        return True
        return False