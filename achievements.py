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
                             "Capital Connection": "Run a train between Wellington and Palmerston North",
                             "The far east": "Connect Gisbourne to your network",
                             "North to south": "Connect the most northern and southern towns using only 2 services",
                             "Picking up steam": "Transport your first 100,000 passengers",
                             "Express service": "Establish an express train which bypasses at least 5 towns.",
                             "Remembered Worlds": "Use the Stratford-Okahukura Line",
                             "Full steam ahead!": "Transport 100,000,000 passengers",
                             "We ran out of colours!": "Use the entire colour palette",
                             "Tongariro visitors": "Transport 100 people to National Park Village",
                             "Ski Ruapehu": "Transport 100 people to Ohakune during winter",
                             "Fake it till you make it": "Edit a service report",
                             "Rapid transit": "Create a service that runs every 15 minutes",
                             "Marketing guru": "Run an advertising campaign"
                             }

    def get_all_achievements(self):
        return self.achievements
