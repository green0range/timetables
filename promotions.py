import numpy as np

class Promotion:
    def __init__(self):
        self.start_date = None
        self.target = None
        self.putsPosters = None

    def add_poster_promotion(self, target, putsPosters, date, services):
        """
        The promotion will register with the service(s) it is applicable to so that not every service needs to be
        searched through on run to see if the promotion is applicable.
        :param target:
        :param putsPosters:
        :param date:
        :param services:
        :return:
        """
        found_target = False
        found_putsPosters = 0
        if target == "Auckland-Wellington (sleeper only)":
            return "C this poster is not implemented yet!"
        elif target == "Christchurch-Invercargill (express only)":
            return "C this poster is not implemented yet!"
        else:
            for s in services:
                for town in s.get_stations():
                    if target == town.get_name():
                        found_target = True
                        s.register_promotion(self)
                    for town2 in putsPosters:
                        if town2 == town.get_name():
                            found_putsPosters += 1
                            s.register_promotion(self)
            if not found_target:
                return "C YOU DO NOT HAVE A TRAIN TO THE TARGET LOCATION"
            if found_putsPosters < len(putsPosters):
                return "C YOU DO NOT HAVE TRAINS LEAVING ALL THE TOWNS IN WHICH YOU ARE PUTTING UP THE POSTERS"
            self.start_date = date
            self.target = target
            self.putsPosters = putsPosters
        return "P"

    def get_weights_increase(self, stations):
        """
        The registered service should call this function to check if the weights should be adjusted when calculating
        patronage.
        :param stations:
        :return:
        """
        if self.target is None:
            return None  # this method is only applicable to poster promotions
        new_weights1 = np.zeros(len(stations))
        new_weights2 = np.zeros(len(stations))
        for i, s in enumerate(stations):
            if s.get_name() == self.target:
                new_weights2[i] = 1
            for town in self.putsPosters:
                if s.get_name() == town:
                    new_weights1[i] = 1
        return new_weights1, new_weights2, len(self.putsPosters)

