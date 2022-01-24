import datetime

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
            if score.get_lastyear_score() >= 2000000000:
                return "P"
            else:
                return "F TRANSPORTED LESS THAN 20,000,000,000pkm/yr BY 2030"
        return "F LESS THAN 70% OF TOWNS CONNECTED BY 2030"

    def check_2050(self, date, percent_connected, score):
        if percent_connected >= 90:
            if score.get_lastyear_score() >= 5000000000:
                return "W"
            else:
                return "F TRANSPORTED LESS THAN 50,000,000,000pkm/yr BY 2050"
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
                             "[na]Capital Connection": "Run a train between Wellington and Palmerston North",
                             "[na]The far east": "Connect Gisbourne to your network",
                             "[na]North to south": "Connect the most northern and southern towns using only 2 services",
                             "[na]Picking up steam": "Transport your first 100,000 passengers",
                             "[na]Express service": "Establish an express train which bypasses at least 5 towns.",
                             "[na]Remembered Worlds": "Use the Stratford-Okahukura Line",
                             "[na]Full steam ahead!": "Transport 100,000,000 passengers",
                             "[na]We ran out of colours!": "Use the entire colour palette",
                             "[na]Tongariro visitors": "Transport 100 people to National Park Village",
                             "[na]Ski Ruapehu": "Transport 100 people to Ohakune during winter",
                             "[na]Fake it till you make it": "Edit a service report",
                             "[na]Rapid transit": "Create a service that runs every 15 minutes",
                             "[na]Marketing guru": "Run an advertising campaign",
                             "Information": "[na] means `not attainable` because it isn't full programmed yet!"
                             }
        self.completed_achievements = []

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
            east_coast = ["Christchurch", "Invercargill", "Edendale", "Gore", "Balclutha", "Milton", "Mosgiel",
                          "Dunedin", "Waikouaiti", "Palmerston", "Ōamaru", "Timaru", "Ashburton", "Rolleston",
                          "Rangiora", "Amberley", "Waipara", "Arthur's Pass Village", "Springfield", "Darfield",
                          "Kaikōura", "Blenheim", "Picton", "Seddon"]
            west_coast = ["Greymouth", "Moana", "Ōtira", "Westport", "Īnangahue", "Reefton", "Ahaura", "Ikamatua",
                          "Kūmara", "Hokitika"]
            for s in service:
                stops_in_east = False
                stops_in_west = False
                for town in s.get_stations():
                    if town.get_name() in east_coast:
                        stops_in_east = True
                    elif town.get_name() in west_coast:
                        stops_in_west = True
                if stops_in_east and stops_in_west:
                    return True
        elif achievement_name == "A True Coaster":
            east_coast = ["Christchurch", "Invercargill", "Edendale", "Gore", "Balclutha", "Milton", "Mosgiel",
                          "Dunedin", "Waikouaiti", "Palmerston", "Ōamaru", "Timaru", "Ashburton", "Rolleston",
                          "Rangiora", "Amberley", "Waipara", "Arthur's Pass Village", "Springfield", "Darfield",
                          "Kaikōura", "Blenheim", "Picton", "Seddon"]
            west_coast = ["Greymouth", "Moana", "Ōtira", "Westport", "Īnangahue", "Reefton", "Ahaura", "Ikamatua",
                          "Kūmara", "Hokitika"]
            for s in service:
                stops_in_east = False
                stops_in_west = False
                for town in s.get_stations():
                    if town.get_name() in east_coast:
                        stops_in_east = True
                    elif town.get_name() in west_coast:
                        stops_in_west = True
                if stops_in_west and not stops_in_east:
                    return True
        elif achievement_name == "SUPERCITY":
            for s in service:
                for town in s.get_stations():
                    if town.get_name() == "Auckland":
                        return True
        return False