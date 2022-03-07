import datetime
import random

import numpy as np

class Promotion:
    def __init__(self, image):
        self.connection_towns = []
        self.start_date = None
        self.image = image
        self.date_expires = None
        self.target = None
        self.putsPosters = None
        self.promotion_type = "NOTSET"
        self.service_with_target = None
        self.services_to_reach_target = []
        self.effective_increase_bounds = [0, 0.001]
        self.total_additional_passenger = 0

    def report_back(self, additional_passenger):
        self.total_additional_passenger += int(additional_passenger)

    def add_print_media(self, service_to_promote, date, services, only_in_towns_serviced):
        if service_to_promote == 'Tranz-Passenger company (All services)':
            self.promotion_type = "promote-service"
            ''' If you only advertise in towns with services, then visitors to the town don't know about the train,
                so a (very small) amount of traffic is lost. '''
            if only_in_towns_serviced:
                self.effective_increase_bounds = [0, 0.08]
            else:
                self.effective_increase_bounds = [0, 0.1]  # a random passenger increase is chosen between bounds.
            for s in services:
                s.register_promotion(self)
            self.start_date = date
            len_of_promotion = 14  # 2 weeks
            self.date_expires = self.start_date + datetime.timedelta(days=len_of_promotion)
        else:
            for s in services:
                if s.get_name() == service_to_promote:
                    self.promotion_type = "promote-service"
                    if only_in_towns_serviced:
                        self.effective_increase_bounds = [0, 0.15]
                    else:
                        self.effective_increase_bounds = [0, 0.16]
                    s.register_promotion(self)
                    self.start_date = date
                    len_of_promotion = 14  # 2 weeks
                    self.date_expires = self.start_date + datetime.timedelta(days=len_of_promotion)
                    break

    def add_radio(self, service_to_promote, date, services, times):
        self.effective_increase_bounds = [0, 0]
        for t in times:
            """ The more popular radio times should increase the percentage more.
                Note radio is exactly half as effective as tv"""
            if t == 7:
                self.effective_increase_bounds[0] += 0.005
                self.effective_increase_bounds[1] += 0.07
            elif t == 18:
                self.effective_increase_bounds[0] += 0.01
                self.effective_increase_bounds[1] += 0.125
            elif t == 12:
                self.effective_increase_bounds[0] += 0.0025
                self.effective_increase_bounds[1] += 0.045
            elif t == 21:
                self.effective_increase_bounds[0] += 0.005
                self.effective_increase_bounds[1] += 0.1
        if service_to_promote == 'Tranz-Passenger company (All services)':
            self.promotion_type = "promote-service"
            for s in services:
                s.register_promotion(self)
            self.start_date = date
            len_of_promotion = 14  # 2 weeks
            self.date_expires = self.start_date + datetime.timedelta(days=len_of_promotion)
        else:
            for s in services:
                if s.get_name() == service_to_promote:
                    self.promotion_type = "promote-service"
                    """ Increase the effective increase bounds on top of the exist percentage, because we are targeting
                        a specific service so it is more effect in attracting passengers to that specific service,
                        but does not do anything for any other service."""
                    self.effective_increase_bounds += [0.015, 0.5]
                    s.register_promotion(self)
                    self.start_date = date
                    len_of_promotion = 14  # 2 weeks
                    self.date_expires = self.start_date + datetime.timedelta(days=len_of_promotion)
                    break

    def add_tv_ad(self, service_to_promote, date, services, times):
        self.effective_increase_bounds = [0, 0]
        for t in times:
            """ The more popular tv times should increase the percentage more."""
            if t == 7:
                self.effective_increase_bounds[0] += 0.01
                self.effective_increase_bounds[1] += 0.14
            elif t == 18:
                self.effective_increase_bounds[0] += 0.02
                self.effective_increase_bounds[1] += 0.25
            elif t == 12:
                self.effective_increase_bounds[0] += 0.005
                self.effective_increase_bounds[1] += 0.09
            elif t == 21:
                self.effective_increase_bounds[0] += 0.01
                self.effective_increase_bounds[1] += 0.2
        if service_to_promote == 'Tranz-Passenger company (All services)':
            self.promotion_type = "promote-service"
            for s in services:
                s.register_promotion(self)
            self.start_date = date
            len_of_promotion = 14  # 2 weeks
            self.date_expires = self.start_date + datetime.timedelta(days=len_of_promotion)
        else:
            for s in services:
                if s.get_name() == service_to_promote:
                    self.promotion_type = "promote-service"
                    """ Increase the effective increase bounds on top of the exist percentage, because we are targeting
                        a specific service so it is more effect in attracting passengers to that specific service,
                        but does not do anything for any other service."""
                    self.effective_increase_bounds += [0.03, 0.1]
                    s.register_promotion(self)
                    self.start_date = date
                    len_of_promotion = 14  # 2 weeks
                    self.date_expires = self.start_date + datetime.timedelta(days=len_of_promotion)
                    break

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
            self.promotion_type = "poster-service"
            for s in services:
                goes_at_night = False
                stops_in_ack = False
                stops_in_wlg = False
                daytime = [datetime.time(7), datetime.time(19)]
                for dep_t in s.departure_times:
                    if not daytime[0] <= dep_t.time() <= daytime[1]:
                        goes_at_night = True
                        for town in s.get_stations():
                            if town.get_name() == "Auckland":
                                stops_in_ack = True
                            if town.get_name() == "Wellington":
                                stops_in_wlg = True
                    if goes_at_night and stops_in_wlg and stops_in_ack:
                        s.register_promotion(self)
                        self.start_date = date
                        len_of_promotion = random.randint(4, 21)
                        self.date_expires = self.start_date + datetime.timedelta(days=len_of_promotion)
                        return "PASS"
            return "C Cannot find an overnight train between Wellington and Auckland!"
        elif target == "Christchurch-Invercargill (express only)":
            self.promotion_type = "poster-service"
            for s in services:
                stations = s.get_stations()
                if len(stations) == 2:
                    if stations[0].get_name() == "Christchurch" or stations[0].get_name() == "Invercargill":
                        if stations[1].get_name() == "Invercargill" or stations[1].get_name() == "Christchruch":
                            s.register_promotion(self)
                            self.start_date = date
                            len_of_promotion = random.randint(4, 21)
                            self.date_expires = self.start_date + datetime.timedelta(days=len_of_promotion)
                            return "PASS"
            return "C Cannot find an express service between Christchurch and Invercargill"
        else:
            if target == "everywhere":
                self.promotion_type = "promote-service"  # promotes the company, meaning all trains routes are promoted
                self.effective_increase_bounds = [0, 0.05]  # a random passenger increase is chosen between bounds.
                for s in services:
                    s.register_promotion(self)
                self.start_date = date
                len_of_promotion = random.randint(4, 21)
                self.date_expires = self.start_date + datetime.timedelta(days=len_of_promotion)
            else:
                self.promotion_type = "poster-target"
                for s in services:
                    for town in s.get_stations():
                        if target == town.get_name():
                            found_target = True
                            self.service_with_target = s
                        for town2 in putsPosters:
                            if town2 == town.get_name():
                                found_putsPosters += 1
                                if s not in self.services_to_reach_target and not s == self.service_with_target:
                                    self.services_to_reach_target.append(s)
                if self.service_with_target is None:
                    return "C No train travels to the promoted destination"
                """ The complication here is that we could require a connecting service. For example, train from
                    Christchurch to Greymouth then another train to Hokatika. This should still allow the promotion to
                    Hokatika even though 2 trains are needed to reach it. We need to store a list of services needed to
                    reach the target so that we can set the target of an individual line to the station the transfer is
                    needed."""
                doesnotconnect = []
                for s in self.services_to_reach_target:
                    """ Here we check that services with promotional posters actually connect to a service which reaches
                        the destination they are promoting."""
                    connects = False
                    for town in s.get_stations():
                        if town in self.service_with_target.get_stations():
                            connects = True
                            self.connection_towns.append(town)
                            if not town.get_name() in putsPosters:
                                putsPosters.append(town.get_name())  # we need to put a poster in the transfer station
                                found_putsPosters += 1  # so that the to_destination train has a pickup location.
                            break
                    if not connects:
                        doesnotconnect.append(s)
                print(putsPosters)
                for s in doesnotconnect:
                    self.services_to_reach_target.remove(s)
                    print(f"{s.get_name()} does not connects to target")
                if len(doesnotconnect) > 0:
                    """ This means we have deleted a service that doesn't connect so we have to re-check that there are
                        enough services that do connect. This could happen if there are two services leaving a station with
                        a promotional poster but only one of them connects to the services which takes the passenger to
                        the destination."""
                    found_putsPosters = 0
                    for s in self.services_to_reach_target:
                        for town in s.get_stations():
                            for town2 in putsPosters:
                                if town2 == town.get_name():
                                    found_putsPosters += 1
                if not found_target:
                    return "C No train to the target destination"
                if found_putsPosters < len(putsPosters):
                    return "C Trains leaving the stations where the posters are do not connect to the target destination"
                for s in self.services_to_reach_target:
                    s.register_promotion(self)
                self.service_with_target.register_promotion(self)
                self.start_date = date
                len_of_promotion = random.randint(4, 21)
                self.date_expires = self.start_date + datetime.timedelta(days=len_of_promotion)
                self.target = target
                self.putsPosters = putsPosters
        return "P"

    def get_type(self):
        return self.promotion_type

    def get_effective_increase_bounds(self):
        return self.effective_increase_bounds

    def check_expiry(self, game_time):
        if game_time > self.date_expires:
            self.image.display_new_achievement([f"Promotion Ended, approximately {int(self.total_additional_passenger)} extra passengers travelled \nbecause of the promotion."], dont_add_preamble=True)
            return True
        return False

    def get_lasting_effect(self):
        increase = self.total_additional_passenger / 100
        if increase > 1.5:
            increase = 1.5
        elif increase < 1:
            increase = 1
        return increase

    def get_target_name(self):
        return self.target

    def get_display_towns(self):
        return self.putsPosters

    def get_weights_increase(self, stations):
        """
        The registered service should call this function to check if the weights should be adjusted when calculating
        patronage.
        :param stations:
        :return:
        """
        if self.target is None:
            return None  # this method is only applicable to poster-target promotions
        puts_poster_index = []
        target_index = -1
        for i, town in enumerate(stations):
            if town.get_name() == self.target:
                target_index = i
            for town2 in self.putsPosters:
                if town2 == town.get_name():
                    puts_poster_index.append(i)
        if target_index == -1:
            for town in self.service_with_target.get_stations():
                for i, town2 in enumerate(stations):
                    if town == town2:
                        target_index = i
        return puts_poster_index, target_index

