import datetime
import logging
import random
import sys
from copy import copy

import numpy as np
logging.basicConfig(stream=sys.stdout,
                    filemode="w",
                    format="%(levelname)s %(asctime)s - %(message)s",
                    level=logging.INFO)
logger = logging.getLogger()

class PatronageData:
    def __init__(self):
        """
        Calculating patronage is very expensive. This stores the patronage from each time it is calculated, so that
        sometimes we can just use a random selection of previous data.

        When a route is created, it will have an empty PatronageData (PD) object. Call PD.get_run_instance(), if it
        returns -1, you need to do a full calculation. It will always return -1 if there is no data, as data is added
        the chance of returning -1 will decrease, but never be quite 0, so some new data can always be added.

        if a reputation change occurs, call PD.update_reputation(new_reputation) and PD will adjust the weights placed
        on old data and be more likely to require recalculations

        The recalc method must send new data to PD.push_data(seat_on, seat_off, sleeper_on, sleeper_off, total_fares)
        """
        self.data = []
        self.return_data = []
        self.weights = []
        self.return_weights = []
        self.chance_of_recalc = 1
        self.company_reputation = 0.5
        self.seat_capacity = 0
        self.sleeper_capacity = 0

    def set_capacity(self, seat, sleeper):
        self.seat_capacity = seat
        self.sleeper_capacity = sleeper

    def update_reputation(self, reputation):
        if reputation != self.company_reputation:
            self.company_reputation = reputation
            ''' Prune the data so data from old reputation scores don't skew results '''
            try:
                self.data = self.data[len(self.data) - 10:]
                self.weights = self.weights[len(self.weights) - 10:]
                self.return_data = self.return_data[len(self.return_data) - 10:]
                self.return_weights = self.return_weights[len(self.return_weights) - 10:]
            except IndexError:  # if len(data) < 10, don't worry about it!
                pass
            for i in range(len(self.weights)):
                self.weights[i] /= 3  # sets all weights to 1/3rd of original value
            for i in range(len(self.return_weights)):
                self.return_weights[i] /= 3  # sets all weights to 1/3rd of original value
            self.chance_of_recalc += 0.7

    def get_run_instance(self, is_return, promos, stations):
        if self.chance_of_recalc >= 1:
            return -1
        if random.random() < self.chance_of_recalc:
            return -1
        try:
            pweights1 = np.zeros(len(stations))
            pweights2 = np.zeros(len(stations))
            num_ons = 1
            for p in promos:
                w1, target_index, num_ons = p.get_weights_increase(stations)
                pweights1 += w1
                pweights2[target_index] = 1
            if is_return:
                choice = random.choices(self.return_data, self.return_weights, k=1)[0]
            else:
                choice = random.choices(self.data, self.weights, k=1)[0]
                if len(promos) > 0:
                    seat_travelers = choice[1][target_index]
                    sleep_travelers = choice[3][target_index]
                    assert self.seat_capacity - seat_travelers > 0
                    traveler_increase_seat = np.minimum(seat_travelers*0.4, self.seat_capacity - seat_travelers)
                    traveler_increase_sleeper = np.minimum(sleep_travelers*0.4, self.sleeper_capacity - sleep_travelers)
                    seat_increase = np.round((pweights1*traveler_increase_seat)/num_ons, 0)
                    sleep_increase = np.round((pweights1*traveler_increase_sleeper)/num_ons, 0)
                    print(f"{seat_increase}, {sleep_increase}")
                    choice[0] = choice[0] + seat_increase
                    choice[2] = choice[2] + sleep_increase
                    choice[1] = choice[1] + pweights2 * np.sum(seat_increase)
                    choice[3] = choice[3] + pweights2 * np.sum(sleep_increase)
            logger.debug(f"PatronageData selected {choice}")
            return choice
        except IndexError:  # this error occurred in testing, but I don't know why
            return -1

    def push_data(self, seat_on, seat_off, sleeper_on, sleeper_off, total_fares, is_return):
        if is_return:
            self.return_data.append([seat_on, seat_off, sleeper_on, sleeper_off, total_fares])
            self.return_weights.append(1)
        else:
            self.data.append([seat_on, seat_off, sleeper_on, sleeper_off, total_fares])
            self.weights.append(1)
        self.chance_of_recalc = 0.95*self.chance_of_recalc
        if self.chance_of_recalc < 0.1:
            self.chance_of_recalc = 0.1  # 1 in 10 runs must use an original calculation.
        logger.debug(f"new chance of recalc is {self.chance_of_recalc}")

    def change_reputation(self):
        logger.warning("NOT IMPLEMENTED YET!")



class Service:
    def __init__(self):
        self.name = ""
        self.confirmed = False
        self.pd = PatronageData()
        # my upfront costs are based on this: https://www.linkedin.com/pulse/case-overnight-sleeper-train-between-auckland-wellington-nicolas-reid/
        self.up_front_costs = {"engine": 2.5e6,
                                "passenger car": 1e6,
                                "sleeper car": 1.2e6,
                                "open air": 1e6,
                               "baggage car": 0.75e6}
        # my running costs are a bit of a guess.
        self.running_costs = {"driver": 40,  # $/hr  x2 if there are two engines
                              "ticket inspector": 30,  # $/hr
                              "cleaning": 25,  # $ per car to clean
                              "major station fees": 1000,  # for services such as ticketing and security
                              "minor station fees": 50,  # station in a town of less than 10,000 people
                              "maintenance": 2000}
        self.car_capacity = {"engine": 0,
                             "passenger car": 54,
                             "sleeper car": 16,
                             "open air": 0,
                             "baggage": 0}
        self.stations = []
        self.stations_reversed = False
        self.returns = False
        # note: departure_time is datetime object with date 1900-01-01 for compatibility with timedelta.
        # Always ignore date and just use time.
        self.departure_times = []
        self.days = [False, False, False, False, False, False, False]
        self.config = [1, 0, 0, 0, 0]
        self.fares = [0, 0]
        self.average_speed = 90  #km/h
        self.editable = True
        self.passenger_confidence = 0  # 0 - 1, increases over time if everything runs, decreases if delays occur.
        # Note: for reports, the most recent journey is in array position 0
        self.passenger_numbers_report = []  # [[seat_onN, seat_offN, sleeper_onN, sleeper_offN], ... [seat_on1, ...]]
        self.passenger_numbers_report_return = []
        self.earnings_report = []  # [[profitN, datetime_of_journeyN], ... [profit1, ...]]
        self.earnings_report_return = []
        self.promotions = []

    def register_promotion(self, promo):
        self.promotions.append(promo)

    def get_passenger_numbers_report(self, returns_report=False):
        if returns_report:
            return self.passenger_numbers_report_return
        return self.passenger_numbers_report

    def get_stations(self):
        """ This must always return the stations in the correct order, even if they are reversed internally!"""
        if self.stations_reversed:
            my_return = copy(self.stations)
            my_return.reverse()
            return my_return
        else:
            return copy(self.stations)

    def reverse_stations(self):
        """ Important: do not use self.stations.reverse(), use this method, because we need to set a reversed
            flag so that if another object wants to get the stations, we know what order to give them in, even
            if they are currently reversed."""
        self.stations.reverse()
        self.stations_reversed = not self.stations_reversed

    def get_earnings_report(self, returns_report=False):
        if returns_report:
            return self.earnings_report_return
        return self.earnings_report

    def update(self, stations, returns, departure_times, days, config, fares):
        if self.editable:
            self.stations = stations
            self.returns = returns
            self.departure_times = departure_times
            self.days = days
            self.config = config
            self.fares = fares
        else:
            logger.warning("Service: Tried to edit an uneditable service.")

    def get_capacity(self):
        sum = 0
        for (capacity, car) in zip(self.car_capacity, self.config):
            sum += self.car_capacity[capacity]*car
        return sum

    def get_seated_capacity(self):
        return self.car_capacity["passenger car"]*self.config[1]

    def get_sleeper_capacity(self):
        return self.car_capacity["sleeper car"]*self.config[2]

    def get_up_front_cost(self):
        sum = 0
        for (key, car) in zip(self.up_front_costs, self.config):
            sum += self.up_front_costs[key] * car
        return sum

    def get_running_cost(self):
        num_cars_to_clean = np.sum(self.config[1:])
        hours_to_pay_for = self.get_journey_length(0, len(self.stations)-1).total_seconds()/3600
        cost = self.config[0] * self.running_costs['driver'] * hours_to_pay_for
        cost += self.running_costs['ticket inspector'] * hours_to_pay_for
        cost += num_cars_to_clean * self.running_costs['cleaning']
        for station in self.stations:
            if station.population > 10000:
                cost += self.running_costs['major station fees']
            else:
                cost += self.running_costs['minor station fees']
        cost += self.running_costs['maintenance']
        return np.round(cost, 2)

    def get_journey_length(self, station1_index, station2_index):
        """
        Get the (time) length of the journey between 2 stations. Intermediate stations are factored in as a 10-minute
         stopover.
        :param station1_index: index of the first station
        :param station2_index: index of the second station (must be larger than station1_index)
        :return:
        """
        if station1_index > station2_index:
            tmp = station1_index
            station1_index = station2_index
            station2_index = tmp
        if len(self.stations) > 1:
            assert station2_index > station1_index
            dist = self.stations[station1_index].getDistanceToNode(self.stations[station2_index])
            time = datetime.timedelta(hours=(dist/self.average_speed))
            number_of_intermediate_stops = station2_index - 1  # subtract start and end stations
            time += datetime.timedelta(minutes=(number_of_intermediate_stops*10))  # each stop is 10 minutes
            return time
        else:
            # the stations are invalid, return 10 minutes so that we don't crash
            logger.debug("Service has an invalid number of stations, this is likely because the gui is still updating")
            return datetime.timedelta(minutes=10)

    def get_arrival_time(self):
        return (self.departure_times[0] + self.get_journey_length(0, len(self.stations)-1)).time().strftime("%H:%M")

    def get_return_time(self):
        return (self.departure_times[0] + 2*self.get_journey_length(0, len(self.stations)-1) + datetime.timedelta(minutes=10)).time().strftime("%H:%M")

    def get_estimated_revenue(self):
        percent_full = 0.7
        seat_capacity = percent_full*self.config[1]*self.car_capacity["passenger car"]
        sleeper_capacity = percent_full*self.config[2]*self.car_capacity["sleeper car"]
        revenue_per_run = seat_capacity * self.fares[0] + sleeper_capacity * self.fares[1]
        return revenue_per_run

    def get_estimated_profit(self):
        return self.get_estimated_revenue() - self.get_running_cost()

    def get_name(self):
        return self.name

    def create_name(self):
        try:
            if len(self.stations) > 2:
                if self.returns:
                    return f"Train between {self.stations[0].get_name()} and {self.stations[len(self.stations) - 1].get_name()}"
                else:
                    return f"Train from {self.stations[0].get_name()} to {self.stations[len(self.stations) - 1].get_name()}"
            else:
                if self.returns:
                    return f"Express between {self.stations[0].get_name()} and {self.stations[len(self.stations) - 1].get_name()}"
                else:
                    return f"Express from {self.stations[0].get_name()} to {self.stations[len(self.stations) - 1].get_name()}"
        except IndexError:
            return "Untitled train"

    def confirm_service(self, name, wallet, date):
        """ All services start as unconfirmed, so that the user can test route, alter carriages, etc.
            This method """
        if not wallet.addsubtract(-self.get_up_front_cost(), date, details=f"Setup costs of {name}"):
            return "C NOT ENOUGH MONEY"
        else:
            self.editable = False
            self.confirmed = True
            self.name = name
            if self.name == "":
                self.name = self.create_name()
            self.passenger_confidence = 0.1 + random.random() * (0.3 - 0.1)  # start at random between 10% and 30%
            self.pd.set_capacity(self.car_capacity['passenger car']*self.config[1], self.car_capacity['sleeper car']*self.config[2])
            return "PASS"

    def run(self, increment, time, wallet, score, company_reputation):
        """
        Runs the train all the train services between time_0 and time_1, note this is called after the time is
        incremented so t_0 is time-increment to get back to pre-incremented time.
        :param increment: The amount the time was incremented
        :param time: The current time (after increment)
        :return:
        """
        self.pd.update_reputation(company_reputation)
        if not self.confirmed:
            return "P"  # if the service is unconfirmed, it does not run.
        time_0 = time - increment
        time_1 = time
        t = time_0
        while t < time_1:
            if self.days[t.weekday()]:
                first_departure = None
                for i, dt in enumerate(self.departure_times):
                    if t.time() <= dt.time():
                        first_departure = i
                        logger.debug("found first departure")
                        break
                if first_departure is None:
                    # time is already later than all the departures, so not runs today. Reset to 00:00 on next day
                    t += datetime.timedelta(days=1)
                    t -= datetime.timedelta(hours=t.time().hour, minutes=t.time().minute, seconds=t.time().second, microseconds=t.time().microsecond)
                else:
                    for i in range(first_departure, len(self.departure_times)):
                        ''' Calculating patronage is computationally expensive, so we do it for the first week of the
                            service running and record the results, then '''
                        run_instance = self.pd.get_run_instance(False, self.promotions, self.get_stations())
                        if run_instance == -1:
                            profit = self.calculate_patronage(self.departure_times[i].time(), t.weekday(), score, time_0.date(), company_reputation)
                        else:
                            profit = run_instance[4]
                            self.passenger_numbers_report.insert(0, run_instance[:4])
                            for j, town in enumerate(self.stations):
                                town.people_arrived(run_instance[1][j]+run_instance[3][j])
                                town.people_departed(run_instance[0][j]+run_instance[2][j])
                        profit -= self.calculate_gst(profit)
                        profit -= self.calculate_cost()
                        profit -= self.calculate_tax(profit)
                        self.earnings_report.insert(0, [profit, datetime.datetime.combine(time.date(),
                                                                                          self.departure_times[i].time())])
                        if len(self.earnings_report) > 10:
                            self.earnings_report = self.earnings_report[:5]
                        if wallet.addsubtract(profit, time.strftime("%d/%m/%y"), details=f"running cost of {self.name}"):
                            logger.debug(f"ran service {self.name} at {self.departure_times[i].time()} for ${profit}")
                        else:
                            return "F SERVICE COULD NOT RUN BECAUSE YOU COULDN'T AFFORD TO PAY THE STAFF!"
                        # now we need to do the return trip:
                        if self.returns:
                            self.reverse_stations()
                            return_time = self.departure_times[i]
                            return_time += self.get_journey_length(0, len(self.stations)-1)
                            return_time += datetime.timedelta(minutes=10)
                            run_instance = self.pd.get_run_instance(True, self.promotions, self.get_stations())
                            if run_instance == -1:
                                profit = self.calculate_patronage(return_time.time(), t.weekday(), score,
                                                                  time_0.date(), company_reputation, is_return=True)
                            else:
                                for j, town in enumerate(self.stations):
                                    town.people_arrived(run_instance[1][j] + run_instance[3][j])
                                    town.people_departed(run_instance[0][j] + run_instance[2][j])
                                profit = run_instance[4]
                                self.passenger_numbers_report_return.insert(0, run_instance[:4])
                            profit -= self.calculate_gst(profit)
                            profit -= self.calculate_cost()
                            profit -= self.calculate_tax(profit)
                            self.earnings_report_return.insert(0, [profit, datetime.datetime.combine(time.date(),
                                                                                              return_time.time())])
                            if len(self.earnings_report_return) > 10:
                                self.earnings_report_return = self.earnings_report_return[:5]
                            if wallet.addsubtract(profit, time.strftime("%d/%m/%y"), details=f"running cost of {self.name}"):
                                logger.debug(f"ran return service {self.name} at {self.departure_times[i].time()} for ${profit}")
                            else:
                                return "F SERVICE COULD NOT RUN BECAUSE YOU COULDN'T AFFORD TO PAY THE STAFF!"
                            self.reverse_stations()  # put them back to normal
                    # done all the runs for today, move on to the next day
                    t += datetime.timedelta(days=1)
                    t -= datetime.timedelta(hours=t.time().hour, minutes=t.time().minute, seconds=t.time().second,
                                            microseconds=t.time().microsecond)
            else:
                # Advance 1 day, but set time to midnight such that we don't miss morning runs.
                t += datetime.timedelta(days=1)
                t -= datetime.timedelta(hours=t.time().hour, minutes=t.time().minute, seconds=t.time().second,
                                        microseconds=t.time().microsecond)
        return "P"

    def get_driving_cost(self, distance):
        """ Estimates the cost of doing the trip by car, so that passengers have a base point to compare prices"""
        petrol_price = 1.98  # todo: slowly inflate prices
        km_per_litre = 15
        return (distance/km_per_litre) * petrol_price

    def price_sensitivity(self, train_cost, i, j, sleeper):
        """ Now we need to factor in the price, it should broadly implement this:
                1. if the price is lower than driving, everyone who wants to travel by train will do so
                2. if the price is close to that of driving, most people who want to take the train will do so
                3. if the price is far more than that of driving, only the people who need to take the train
                (because they can't access a car) will take the train
                4. if the price is far more than that of driving but the train offers tourist attractions such
                as an open air view car, then the people who need to take it (3) will take it, plus a `tourist
                bonus`, an additional 10% chance of keeping the passenger.
            Note, to get the price of driving, we need to know the destination, so we do this after the
            destinations have been selected and subtract off any passenger who doesn't come because it is
            too expensive.
            :param train_cost: cost of the train ticket (float)
            :param i: index of the departure station (int)
            :param j: index of the arrival station (int)
            :param sleeper: boolean, is the passenger a sleeper?
            :return: True if the passenger will take the train, False if not"""
        # track distance is not the same as road distance, but it should be similar. I do not to store a data structure
        # for all the roads as well as the railways!
        # This is an approximation anyway
        distance = self.stations[i].getDistanceToNode(self.stations[j])
        driving_cost = self.get_driving_cost(distance)
        if sleeper:
            driving_cost += 80  # factor in the cost of a hotel/motel, since this is an overnight trip!
        if driving_cost < train_cost:
            if driving_cost * 2 < train_cost:  # case 3
                if self.config[3] > 0 and not sleeper:  # case 4 - the tourist train (Sleepers don't care about
                    chance = 0.4  # open air viewing, they are asleep!)
                else:
                    chance = 0.3
                if random.random() < chance:  # 30 % chance of the keeping the passenger
                    return True
                else:
                    return False
            else:  # case 2
                if random.random() < 0.8:  # 80 % chance of keeping the passenger
                    return True
                else:
                    return False  # lose the passenger
        else:  # case 1
            return True

    def calculate_patronage(self, time, dow, score, date, reputation, is_return=False):
        """
        Calculates the number of passengers on a particular journey, and returns the total profit from fares.
        To do this we calculate the number of people who want to travel by train, boost that number depending on
        rush hour, passenger confidence, etc, calculate where they will get off, calculate their price and decide if
        they will keep the ticket by comparing that with the price of driving.

        Note, we only calculate patronage for sleeper cars if the train leaves during the night. This is an
        oversimplification as people working a night shift may want to rent a sleeper room and travel during daytime,
        but is far simpler then guess-estimating what percentage of passengers are night shift workers.

        :param time: time the service is running
        :param dow: day of week the service is running
        :return:
        """
        acceptable_commute_time = datetime.timedelta(hours=0.5)
        # Why does timedelta not work with a time object!?
        rush_hours = [datetime.datetime.strptime("8", "%H"), datetime.datetime.strptime("17", "%H")]
        daytime = [datetime.time(7), datetime.time(19)]
        weekend = [5, 6]
        # first find out if we are in a rush hour
        in_rush_hour = False
        if dow not in weekend:  # no rush hours on a weekend
            for rh in rush_hours:
                if rh.time() <= time <= (rh + datetime.timedelta(hours=1)).time():
                    in_rush_hour = True
                    break
        town_pops = np.zeros(len(self.stations))
        """ The boost_factor is used to increase passenger numbers in cases of rush hours, quick service, or
            high passenger confidence in the service."""
        boost_factor = np.ones(len(self.stations))
        reputation_boost = np.ones(len(self.stations)) * (0.15 * random.random() + 0.1) * reputation
        boost_factor += reputation_boost
        for i, town in enumerate(self.stations):
            town_pops[i] = town.population
            for ep in town.economic_partners:
                for j in range(len(self.stations)):
                    if ep is self.stations[j]:
                        if self.get_journey_length(i, j) <= acceptable_commute_time:
                            if in_rush_hour:
                                boost_factor[j] += 0.06
                            else:
                                boost_factor[j] += 0.04
                        else:
                            if in_rush_hour:
                                boost_factor[j] += 0.04
                            else:
                                boost_factor[j] += 0.02
        """First we simulate demand by find how many want on, and where they want to get off. They we check that the
            train has the capacity to carry them and let them on in first on first served basis."""
        on_seat = np.zeros(len(self.stations))
        off_seat = np.zeros(len(self.stations))
        on_sleeper = np.zeros(len(self.stations))
        off_sleeper = np.zeros(len(self.stations))
        current_seated_passengers = 0
        current_sleepers = 0
        total_fares = 0
        price_per_station_past_seated = self.fares[0]/len(self.stations)
        for i, townpop in enumerate(town_pops):
            current_seated_passengers -= off_seat[i]
            # determines how many people are getting on at this station and where they are getting off
            if i != len(town_pops)-1:
                want_to_travel_seated = np.round(self.stations[i].get_want_to_travels(date) * boost_factor[i], 0)
                # If it is nighttime, the demand shifts to sleeper cars
                if not daytime[0] <= time <= daytime[1]:
                    want_to_travel_sleeping = np.round((2/3) * want_to_travel_seated, 0)
                    want_to_travel_seated = np.round(want_to_travel_seated/3, 0)
                if self.get_seated_capacity() - current_seated_passengers > want_to_travel_seated:
                    on_seat[i] = want_to_travel_seated
                    current_seated_passengers += want_to_travel_seated
                else:
                    on_seat[i] = self.get_seated_capacity() - current_seated_passengers  # use all available capacity
                    current_seated_passengers = self.get_seated_capacity()  # train is full
                if not daytime[0] <= time <= daytime[1] and self.get_sleeper_capacity() - current_sleepers > want_to_travel_sleeping:
                    on_sleeper[i] = want_to_travel_sleeping
                    current_sleepers += want_to_travel_sleeping
                elif not daytime[0] <= time <= daytime[1]:
                    on_sleeper[i] = self.get_sleeper_capacity() - current_sleepers
                    current_sleepers = self.get_sleeper_capacity()
                if not daytime[0] <= time <= daytime[1]:  # calculate destinations for sleepers, if at night
                    travel_times = np.ones(len(town_pops) - i - 1)
                    for j in range(i + 1, len(self.stations)):
                        travel_times[j - i - 1] = self.get_journey_length(i, j).seconds
                    weight = town_pops[i + 1:] / 100 + travel_times  # longer travel times are good for sleepers because
                    logger.debug(f"seat weights:{weight}")  # it means they can get more sleep.
                    destinations_sleeper = random.choices(np.linspace(i + 1, len(town_pops) - 1, len(town_pops) - 1 - i),
                                                  weights=weight, k=int(on_sleeper[i]))
                    for dest in destinations_sleeper:
                        train_cost = self.fares[1]
                        if self.price_sensitivity(train_cost, i, int(dest), True):
                            score.increase(self.stations[i].getDistanceToNode(self.stations[int(dest)]))
                            off_sleeper[int(dest)] += 1
                            total_fares += train_cost
                        else:
                            on_sleeper[i] -= 1
                """ The weights should be a combo of population (more people want to travel to more populus place) and
                    the travel time. (less people are willing to travel if it takes too long)"""
                travel_times = np.ones(len(town_pops) - i - 1)
                for j in range(i+1, len(self.stations)):
                    travel_times[j-i-1] = self.get_journey_length(i, j).seconds
                weight = town_pops[i+1:]/100 + (100*3600) / travel_times  # might need tweaking
                logger.debug(f"seat weights:{weight}")
                destinations = random.choices(np.linspace(i+1, len(town_pops)-1, len(town_pops)-1-i), weights=weight, k=int(on_seat[i]))
                for dest in destinations:
                    # not scaling based on trip length for sleepers because nobody can `take over` their bed the way
                    # someone can `take over` a seat when someone leaves.
                    train_cost = (int(dest) - i + 1) * price_per_station_past_seated
                    if self.price_sensitivity(train_cost, i, int(dest), False):
                        score.increase(self.stations[i].getDistanceToNode(self.stations[int(dest)]))
                        off_seat[int(dest)] += 1
                        total_fares += train_cost
                    else:
                        on_seat[i] -= 1
        if is_return:
            self.passenger_numbers_report_return.insert(0, [on_seat, off_seat, on_sleeper, off_sleeper])
        else:
            self.passenger_numbers_report.insert(0, [on_seat, off_seat, on_sleeper, off_sleeper])
        if len(self.passenger_numbers_report) > 10:  # this is to avoid a memory leak. todo: log to file, so that we keep all records.
            self.passenger_numbers_report = self.passenger_numbers_report[:5]
            self.passenger_numbers_report_return = self.passenger_numbers_report_return[:5]
        self.pd.push_data(on_seat, off_seat, on_sleeper, off_sleeper, total_fares, is_return)
        # select destination probs from remaining stations with prop proportaional to population
        # assign passenger numbers on and off at each town
        # increase passenger numbers by boost factor if going between economic partners
        """ This is quite a complicated system so I want to have lots of checks!"""
        do_checks = True
        if do_checks:
            assert off_seat[0] == 0  # nobody can get off at the first stop because nobody is on the train yet
            assert on_seat[len(on_seat) - 1] == 0  # nobody on at the last stop. (Returns run a new instance)
            assert np.sum(on_seat) == np.sum(off_seat)  # all passengers must leave the train at a station
            for i in range(len(on_seat)):  # cannot have more passengers than capacity on at any one time
                assert np.sum(on_seat[:i]) - np.sum(off_seat[:i]) <= self.get_seated_capacity()
        return total_fares

    def calculate_gst(self, amount):
        return amount * 0.15

    def calculate_cost(self):
        return self.get_running_cost()

    def calculate_tax(self, profit):
        if profit > 0:
            return profit * 0.33
        else:
            return 0


class Town:
    def __init__(self, name, population, coords):
        self.want_to_travel = 0
        self.name = name
        self.population = int(population)
        self.coords = coords
        self.connections = []
        self.predecessor = None
        self.distance_to_predecessor = 0
        self.economic_partners = []
        self.last_date_want_to_travels_generated = None
        self.visitors = 0

    def get_latlgn(self):
        return self.coords

    def generate_want_to_travels(self):
        hi = 0.6 * np.sqrt(self.population)
        lo = 0.35 * np.sqrt(self.population)
        self.want_to_travel = int(np.round(lo + random.random() * (hi - lo), 0))

    def get_want_to_travels(self, date):
        """
        Each day, a new group of people who want to travel are generated, based on population size, with some random
        chance. The available travelers are those people, plus any positive count of visitors. When a person leaves
        the visitor count is decremented, and incremented when they arrive. The visitor count is allowed to go negative
        if people are leaving the town, it should always be close to zero as some people will return on the next train
        and increase it again. If abs(visitor) > 5% of population, then this is an indication the player has found an
        explort that must be nerfed.
        :param date:  The date the train is departing. People who want to travel is only updated daily.
        :return: number of people available to travel
        """
        if self.last_date_want_to_travels_generated is None:
            self.generate_want_to_travels()
            self.last_date_want_to_travels_generated = date
        elif self.last_date_want_to_travels_generated != date:
            self.generate_want_to_travels()
            self.last_date_want_to_travels_generated = date
            logger.debug(f"generated want to travels for date {date}")
        visitors_onward_travel = 0
        if self.visitors > 0:
            visitors_onward_travel = int(np.round(random.random() * self.visitors, 0))
        return self.want_to_travel + visitors_onward_travel

    def person_departed(self):
        self.visitors -= 1

    def person_arrived(self):
        self.visitors += 1

    def people_departed(self, num):
        self.visitors -= num

    def people_arrived(self, num):
        self.visitors += num

    def add_economic_partner(self, partner):
        """
        When calculating patronage, a boost is given to journey's between economic partners
        :param partner: town object that shares economic ties to self.
        :return: None
        """
        if partner not in self.economic_partners:
            self.economic_partners.append(partner)
            partner.add_economic_partner(self)

    def bfs_trace_predecessor(self, node, sum_distance=False):
        path = []
        current_node = node
        d_sum = 0
        while current_node.predecessor is not None:
            path.append(current_node)
            d_sum += current_node.distance_to_predecessor
            current_node = current_node.predecessor
        path.append(current_node)
        path.reverse()
        if sum_distance:
            return d_sum
        return path

    def bfs_reset(self, nodes):
        for node in nodes:
            node.predecessor = None
            node.distance_to_predecessor = 0

    def add_link(self, link, distance):
        for c in self.connections:
            if link == c[0]:
                return  # stop method because connection already exists.
        self.connections.append([link, distance])
        link.add_link(self, distance)  # creates reciprocal

    def getAllNodes(self):
        """
        Lists all the nodes connected on the same tree. Uses a breadth-first search
        with no goal to visit each node, then returns the list of visited nodes.
        :return:  List of all nodes connected to self.
        """
        visited = [self]
        q = [self]
        while len(q) > 0:
            p = q.pop(0)
            #if p is endNode:
            #    return p
            for c in p.connections:
                if c[0] not in visited:
                    visited.append(c[0])
                    q.append(c[0])
        return visited

    def getDistanceToNode(self, endNode):
        ''' Modified Breadth first search which records distance between nodes.'''
        visited = [self]
        q = [self]
        while len(q) > 0:
            p = q.pop(0)
            if p is endNode:
                d = self.bfs_trace_predecessor(p, sum_distance=True)
                self.bfs_reset(visited)
                return d
            for c in p.connections:
                if c[0] not in visited:
                    visited.append(c[0])
                    c[0].predecessor = p
                    c[0].distance_to_predecessor = c[1]
                    q.append(c[0])
        self.bfs_reset(visited)
        return 0  # cannot find any path between current node and endpoint

    def getNodesOnPath(self, endNode):
        """
        Uses a breadth first search
        :param endNode:
        :return:
        """
        visited = [self]
        q = [self]
        while len(q) > 0:
            p = q.pop(0)
            if p is endNode:
                path = self.bfs_trace_predecessor(p)
                self.bfs_reset(visited)
                return path
            for c in p.connections:
                if c[0] not in visited:
                    visited.append(c[0])
                    c[0].predecessor = p
                    q.append(c[0])
        self.bfs_reset(visited)
        return []  # cannot find any path between current node and endpoint


    def get_name(self):
        return self.name
