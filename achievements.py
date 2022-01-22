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
        pass
