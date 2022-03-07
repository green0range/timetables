import datetime
import logging
import random
import sys
from copy import copy
import uuid
import numpy as np

logging.basicConfig(stream=sys.stdout,
                    filemode="w",
                    format="%(levelname)s %(asctime)s - %(message)s",
                    level=logging.INFO)
logger = logging.getLogger()

class Service:
    def __init__(self, save_manager):
        self.time_service_was_run = []
        self.time_service_was_run_return = []
        self.number_sleep_passengers_all_time_return = []
        self.number_seat_passengers_all_time_return = []
        self.number_seat_passengers_all_time = []
        self.number_sleep_passengers_all_time = []
        self.distance_between_stations = None
        self.name = ""
        self.name = ""
        self.save_manager = save_manager
        self.confirmed = False
        self.my_uuid = uuid.uuid4()
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
        self.departure_times = []
        self.days = [False, False, False, False, False, False, False]
        self.config = [1, 0, 0, 0, 0]
        self.fares = [0, 0]
        self.average_speed = 90  # km/h
        self.editable = True
        self.passenger_confidence = 0  # 0 - 1, increases over time if everything runs, decreases if delays occur.
        # Note: for reports, the most recent journey is in array position 0
        self.passenger_numbers_report = []  # [[seat_onN, seat_offN, sleeper_onN, sleeper_offN], ... [seat_on1, ...]]
        self.passenger_numbers_report_return = []
        self.earnings_report = []  # [[profitN, datetime_of_journeyN], ... [profit1, ...]]
        self.earnings_report_return = []
        self.promotions = []
        self.has_connection = False

    def register_promotion(self, promo):
        self.promotions.append(promo)

    def is_connecting(self, terminal_stations, times_at_terminal_stations):
        """ This returns true if the given stations connect to the service.
            Connecting to the service is defined as follows:
                Service A and B are connecting if A and B have a matching terminal station AND both trains arrive at
                that matching station with a 15 minute time window (so that passengers can transfer trains.)
            Connecting services each get a 10% increase in passengers.
            It is assumed that terminal stations are the 'hub' stations, stations in the middle of the journey cannot
            form connections. This is mostly for programming simplicity."""
        my_terminal_stations = self.get_terminal_stations()
        match = None
        time_window = datetime.timedelta(minutes=15)
        for i in range(2):
            for j in range(2):
                if my_terminal_stations[i] == terminal_stations[j]:
                    match = [i, j]
                    break
            break
        if match is None:
            return False
        for t in self.departure_times:
            if match[0] == 1:
                t1 = (t + self.get_journey_length(0, len(self.stations) - 1))
            else:
                t1 = t
            for time2 in times_at_terminal_stations:
                if t1 - time_window <= time2[match[1]] <= t1 + time_window:
                    return True
        return False

    def get_terminal_stations(self):
        return [self.stations[0].get_name(), self.stations[len(self.stations) - 1].get_name()]

    def get_terminal_station_times(self):
        times = []
        for t in self.departure_times:
            times.append([t, (t + self.get_journey_length(0, len(self.stations) - 1))])
        return times

    def log_earnings_report(self, profit, time, is_return=False):
        if is_return:
            self.earnings_report_return.append([profit, time])
        else:
            self.earnings_report.append([profit, time])
        if len(self.earnings_report) > 20:
            txt = ""
            for item in self.earnings_report:
                txt += f"{item[0]},{item[1]}\n"
            self.save_manager.save_data(str(self.my_uuid)+"_e", txt, append_mode=True)
            self.earnings_report = []
        if len(self.earnings_report_return) > 20:
            txt = ""
            for item in self.earnings_report_return:
                txt += f"{item[0]},{item[1]}\n"
            self.save_manager.save_data(str(self.my_uuid)+"_er", txt, append_mode=True)
            self.earnings_report_return = []

    def log_passenger_numbers(self, numbers, is_return=False):
        if is_return:
            self.passenger_numbers_report_return.append(numbers)
        else:
            self.passenger_numbers_report.append(numbers)
        if len(self.passenger_numbers_report) > 20:  # [on_seat, off_seat, on_sleeper, off_sleeper]
            txt = ""
            for entry in self.passenger_numbers_report:
                for i, station_on_seat in enumerate(entry[0]):
                    if i == 0:
                        txt += str(station_on_seat)
                    else:
                        txt += "," + str(station_on_seat)
                txt += " "
                for i, station_off_seat in enumerate(entry[1]):
                    if i == 0:
                        txt += str(station_off_seat)
                    else:
                        txt += "," + str(station_off_seat)
                txt += " "
                for i, station_on_sleep in enumerate(entry[2]):
                    if i == 0:
                        txt += str(station_on_sleep)
                    else:
                        txt += "," + str(station_on_sleep)
                txt += " "
                for i, station_off_sleep in enumerate(entry[3]):
                    if i == 0:
                        txt += str(station_off_sleep)
                    else:
                        txt += "," + str(station_off_sleep)
                txt += "\n"
            # this will create collisions when trains are named the same
            self.save_manager.save_data(str(self.my_uuid), txt, append_mode=True)
            self.passenger_numbers_report = []
        if len(self.passenger_numbers_report_return) > 20:  # [on_seat, off_seat, on_sleeper, off_sleeper]
            txt = ""
            for entry in self.passenger_numbers_report_return:
                for i, station_on_seat in enumerate(entry[0]):
                    if i == 0:
                        txt += str(station_on_seat)
                    else:
                        txt += "," + str(station_on_seat)
                txt += " "
                for i, station_off_seat in enumerate(entry[1]):
                    if i == 0:
                        txt += str(station_off_seat)
                    else:
                        txt += "," + str(station_off_seat)
                txt += " "
                for i, station_on_sleep in enumerate(entry[2]):
                    if i == 0:
                        txt += str(station_on_sleep)
                    else:
                        txt += "," + str(station_on_sleep)
                txt += " "
                for i, station_off_sleep in enumerate(entry[3]):
                    if i == 0:
                        txt += str(station_off_sleep)
                    else:
                        txt += "," + str(station_off_sleep)
                txt += "\n"
            # this will create collisions when trains are named the same
            self.save_manager.save_data(str(self.my_uuid)+"_r", txt, append_mode=True)
            self.passenger_numbers_report_return = []

    def get_passenger_numbers_report(self, returns_report=False):
        if not returns_report:
            passenger_numbers = []
            pntxt = self.save_manager.load_data(str(self.my_uuid))
            if pntxt is not None:
                for line in pntxt.split("\n"):
                    try:
                        stations = line.split(" ")
                        run = []
                        for i, station in enumerate(stations):
                            on, off = station.split(",")
                            run.append([int(on), int(off)])
                        passenger_numbers.append(run)
                    except ValueError:
                        pass
            return passenger_numbers + self.passenger_numbers_report
        else:
            passenger_numbers_return = []
            pntxt = self.save_manager.load_data(str(self.my_uuid)+"_r")
            if pntxt is not None:
                for line in pntxt.split("\n"):
                    try:
                        stations = line.split(" ")
                        run = []
                        for i, station in enumerate(stations):
                            on, off = station.split(",")
                            run.append([int(on), int(off)])
                        passenger_numbers_return.append(run)
                    except ValueError:
                        pass
            return passenger_numbers_return + self.passenger_numbers_report_return

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
        self.distance_between_stations.reverse()
        self.stations_reversed = not self.stations_reversed

    def get_earnings_report(self, returns_report=False):
        if returns_report:
            earnings = []
            txt = self.save_manager.load_data(str(self.my_uuid) + "_er")
            if txt is not None:
                for line in txt.split("\n"):
                    try:
                        profit, date = line.split(",")
                        earnings.append([profit, date])
                    except ValueError:
                        pass
            return earnings + self.earnings_report_return
        else:
            earnings = []
            txt = self.save_manager.load_data(str(self.my_uuid) + "_e")
            if txt is not None:
                for line in txt.split("\n"):
                    try:
                        profit, date = line.split(",")
                        earnings.append([profit, date])
                    except ValueError:
                        pass
            return earnings + self.earnings_report

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
            sum += self.car_capacity[capacity] * car
        return sum

    def get_seated_capacity(self):
        return self.car_capacity["passenger car"] * self.config[1]

    def get_sleeper_capacity(self):
        return self.car_capacity["sleeper car"] * self.config[2]

    def get_up_front_cost(self):
        sum = 0
        for (key, car) in zip(self.up_front_costs, self.config):
            sum += self.up_front_costs[key] * car
        return sum

    def get_running_cost(self):
        num_cars_to_clean = np.sum(self.config[1:])
        hours_to_pay_for = self.get_journey_length(0, len(self.stations) - 1).total_seconds() / 3600
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
            time = datetime.timedelta(hours=(dist / self.average_speed))
            number_of_intermediate_stops = station2_index - 1  # subtract start and end stations
            time += datetime.timedelta(minutes=(number_of_intermediate_stops * 10))  # each stop is 10 minutes
            return time
        else:
            # the stations are invalid, return 10 minutes so that we don't crash
            logger.debug("Service has an invalid number of stations, this is likely because the gui is still updating")
            return datetime.timedelta(minutes=10)

    def get_arrival_time(self):
        return (self.departure_times[0] + self.get_journey_length(0, len(self.stations) - 1)).time().strftime("%H:%M")

    def get_return_time(self):
        return (self.departure_times[0] + 2 * self.get_journey_length(0, len(self.stations) - 1) + datetime.timedelta(
            minutes=10)).time().strftime("%H:%M")

    def get_estimated_revenue(self):
        percent_full = 0.7
        seat_capacity = percent_full * self.config[1] * self.car_capacity["passenger car"]
        sleeper_capacity = percent_full * self.config[2] * self.car_capacity["sleeper car"]
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
            """ Now pre-compute all the distances between stations as this is used a lot when the service is run."""
            self.distance_between_stations = []
            for i in range(len(self.stations)):
                if i == len(self.stations) - 1:
                    break
                d = self.stations[i].getDistanceToNode(self.stations[i+1])
                self.distance_between_stations.append(d)
            return "PASS"

    def get_ticket_price(self, num_stations_traveled, sleeper=False):
        """
        Finds the ticket price. Note a fixed cost is built in at 10% the full price, for people not travelling the full
        distance. Only people travelling the full distance pay the full price, passengers travelling part way pay a
        reduced fare proportional to how many stations they travel between plus the fixed cost.
        :param num_stations_traveled: int. arrival station index - departure station index. The number of stations traveled
        :param sleeper: bool. Is the passenger travelling on a sleeper carriage?
        :return: float. The price in NZD
        """
        fare_index = 0
        if sleeper:
            fare_index = 1
        fixed_cost = 0.1 * self.fares[fare_index]
        price_per_station = self.fares[fare_index] / len(self.stations)
        return np.minimum(fixed_cost + num_stations_traveled * price_per_station, self.fares[fare_index])

    def get_ticket_price_list(self, passenger_list, sleeper):
        """
        Gets the cost to go to all future stations in the run. designed to be used part way through the run,
        e.g. current station can be any station along the run.
        :param passenger_list: List of where passengers want to get off, from next station to end station.
                                Note, only the length of the list is actually important, as the method returns
                                a per person price.
        :param sleeper:  bool, is the passenger list a list of sleepers?
        :return: List of prices per person, from current station to listed station [i.e. index 0 is the price to
                    go to the next station, index N is the price to go to the end station.]
        """
        if passenger_list is None:
            return
        price_list = np.linspace(1, len(passenger_list), len(passenger_list))
        for i, dist in enumerate(price_list):
            price_list[i] = self.get_ticket_price(dist, sleeper=sleeper)
        return price_list

    def confirm_passengers(self, root_station_index, stations, potential_passengers, price_list, sleeper):
        """
        Not everyone who is interested in travelling by train will actually travel by train, this removes people if
        the price is too high, then returns a list of the remaining confirmed passengers.
        :param root_station: Town object, Where are all these passengers travelling from
        :param stations: list of Town objects, the stations that come after the root station in the journey
        :param potential_passengers: list of ints, the sum of the list want to leave the root station, and then each
                                        value at the i-th index represents how many want to get off at the i-th index.
        :param price_list:  List of prices the passengers will be charged if they confirm
        :param sleeper: bool, are the passengers sleepers or not?
        :return: List of confirmed passengers, in same formate as the potential passengers list.
        """
        if potential_passengers is None:
            return
        for i, (price, station) in enumerate(zip(price_list, stations)):
            distance = np.sum(self.distance_between_stations[root_station_index:root_station_index+i+1])
            alt_price = self.get_driving_cost(distance)
            if sleeper:
                alt_price += 100
            if price < alt_price:
                factor = 1
            else:
                if price * 1.25 < alt_price:
                    factor = 0.8
                elif price * 2 < alt_price:
                    factor = 0.5
                else:
                    factor = 0.25
            potential_passengers[i] *= factor
            potential_passengers[i] = np.round(potential_passengers[i], 0)
        return potential_passengers

    @staticmethod
    def split_to_list(number, weights, require_ints=False):
        denominator = np.maximum(np.sum(weights), 1)
        pieces = number / denominator
        result = np.zeros(len(weights))
        for i, w in enumerate(weights):
            result[i] = pieces * w
            if require_ints:
                result[i] = int(result[i])
        return result

    def remove_overbookings(self, capacity, confirmed_bookings_seat):
        """
        There may not be space for everyone on the train, if the train is overbooked, this method will remove the
        overbooked passengers from the passenger list.
        :param capacity:
        :param confirmed_bookings_seat:
        :return:
        """
        if confirmed_bookings_seat is None:
            return
        current_occupancy = np.zeros(len(self.stations))
        for i, on_station in enumerate(confirmed_bookings_seat):
            if on_station is None:
                return
            if current_occupancy[i] == capacity:
                confirmed_bookings_seat[i] = None
                # the train is full, we pass through the station without allowing any new passengers.
            elif np.sum(on_station) <= capacity - current_occupancy[i]:
                # The case where everyone can board the train
                current_occupancy = np.concatenate((current_occupancy[:i],
                                                   np.ones(len(self.stations) - i) * np.sum(on_station)))
                for j in range(0, len(on_station)):
                    # the predicted occupancy needs to decrease as people get off at their stops.
                    current_occupancy[i + j] -= on_station[j]
            else:
                # the train is not full, but there is not enough room for everyone who wants to join the train. We need
                # to select who gets a seat.
                number_overbooked = np.sum(on_station) - capacity - current_occupancy[i]
                # if people want to get the train but can't, they loose confidence in the service.
                self.passenger_confidence = np.maximum(self.passenger_confidence - (number_overbooked * 0.001), 0)
                people_to_remove = self.split_to_list(number_overbooked, on_station, require_ints=True)
                confirmed_bookings_seat[i] -= people_to_remove
                join_1 = current_occupancy[:i - 1]
                join_2 = np.ones(len(self.stations) - i) * np.sum(confirmed_bookings_seat[i])
                current_occupancy = np.concatenate((join_1, join_2))
                for j in range(0, len(on_station)):
                    # the predicted occupancy needs to decrease as people get off at their stops.
                    current_occupancy[i + j] -= on_station[j]
        return confirmed_bookings_seat

    def do_promotion(self, p):
        """
        Simulates a promotion.
        :param p: The promotion to sumulate.
        :return: on_indices (where extra passengers board), off_index (where extras disembark),
                 boost_amount (percentage of additional extra passengers). If a specific destination
                 is not targeted, set off_index=-1, then passenger volumes overall will be increased,
                 by the boost_amount, with on_indices and off_index be irrelevant.
        """
        on_indices, off_index, boost_amount = [], -1, 0
        if p.get_type() == "poster-target":
            boost_amount = (random.randint(0, 5)/20) * len(p.get_display_towns())
            for i, town in enumerate(self.stations):
                if p.get_target_name() == town.get_name():
                    off_index = i
                if town.get_name() in p.get_display_towns():
                    on_indices.append(i)
            if off_index == -1:
                """ This is the case where the passenger needs to take a connecting train to reach the target."""
                for i, ct in enumerate(self.stations):
                    if ct in p.connection_towns:
                        off_index = i
                        break
        if p.get_type() == "poster-service" or p.get_type() == "promote-service":
            bounds = p.get_effective_increase_bounds()
            boost_amount = (bounds[1] - bounds[0]) * random.random() + bounds[0]
        return on_indices, off_index, boost_amount


    def get_passengers(self, time, dow, reputation):
        """
        This is a rewrite of calculate_patronage started 18-feb-22.
        This simulates passenger demand and returns a list of passengers.
        It must execute very quickly. I do not want to rely on a cache,
        like the previous version. Multiprocessing may be required when more
        than X train lines are created.
        todo: * incorporate promotions [done 28 Feb]
              * incorporate economic partner bonus
              * different traffic for weekends [done 7 mar]
              * factor in reputation [done 6 mar, needs testing]
              * report back the passenger numbers / statistics
        :param time: The time the service leaves the first station
        :param dow: The day of the week
        :param reputation: The reputation of Tranz-Passenger
        :return: list of Passenger objects
        """
        rep_score = reputation * self.passenger_confidence
        night_start = [20, 21, 22, 23, 0]
        night_end = [1, 2, 3, 4, 5, 6]
        last_station = len(self.stations) - 1
        night_train = False
        if time.time().hour in night_start or (time + self.get_journey_length(0, last_station)).time().hour in night_end:
            if self.get_journey_length(0, last_station) >= datetime.timedelta(hours=4):
                night_train = True
        '''Above I define a night train to have a journey length greater than 4 hours
           and leave between 10pm and 12am, and arrive between 1am and 6am. All these 
           requirements must be satisfied for passengers to buy a sleeper ticket.'''
        destination_pop = np.zeros(len(self.stations))
        destination_ttimes = np.zeros(len(self.stations))
        promotion_data = [[]] * len(self.promotions)
        """ Compute passenger increases due to promotions"""
        for i, p in enumerate(self.promotions):
            on_indices, off_index, boost_amount = self.do_promotion(p)
            promotion_data[i] = [on_indices, off_index, boost_amount]
        """ Every iteration of this loop corresponds to the train arriving at a new station and picking up and letting
            off passengers."""
        for i, town in enumerate(self.stations):
            destination_pop[i] = town.population
            if i != 0:
                destination_ttimes[i] = self.get_journey_length(i-1, i).total_seconds()
        confirmed_bookings_seat = [None] * (len(self.stations) - 1)
        confirmed_bookings_sleep = [None] * (len(self.stations) - 1)
        passengers_before_promotion = 0
        have_a_target_promotion = False
        potential_retain_rate = 1
        overall_potential_increase_promotion = 0
        for i, town in enumerate(self.stations):
            if i == len(self.stations) -1:
                break  # no need to generate onward destinations if we are at the last station
            potential_passengers = town.get_want_to_travels(time.date(), time.time(), rep_score=rep_score, dow=dow)
            potential_passengers /= town.number_of_directions()
            """ p[0] is a list of indices for which extra people will be boarding the train due to a promotion,
                p[2] is the percentage of extra passengers, p[1] is the index they will leave the train"""
            extras_disembarking = []
            extras_disembarking_index = []
            for p in promotion_data:
                if p[1] == -1:
                    increase_from_promotions = np.round(p[2] * potential_passengers)
                    overall_potential_increase_promotion += increase_from_promotions
                    potential_passengers += increase_from_promotions
                elif i in p[0]:
                    have_a_target_promotion = True
                    increase_from_promotions = np.round(p[2] * potential_passengers)
                    extras_disembarking.append(increase_from_promotions)
                    extras_disembarking_index.append(p[1])
            destination_weights = destination_pop[i+1:] + 1/(destination_ttimes[i+1:] - (np.ones(len(self.stations) - i - 1) * sum(destination_ttimes[:i])))
            if night_train:
                potential_sleep = np.round((2 / 3) * potential_passengers, 0)
                potential_seat = np.round(potential_passengers / 3, 0)
                sleep_destinations = self.split_to_list(potential_sleep, destination_weights)
                seat_destinations = self.split_to_list(potential_seat, destination_weights)
            else:
                seat_destinations = self.split_to_list(potential_passengers, destination_weights)
                sleep_destinations = None
            seat_ticket_price_list = self.get_ticket_price_list(seat_destinations, False)
            sleep_ticket_price_list = self.get_ticket_price_list(sleep_destinations, True)
            """ We now have a list of prices and a list of how many people want to travel to which stations. Next,
                we compare the price to driving to find how many will actually buy a ticket."""
            confirmed_bookings_seat[i] = self.confirm_passengers(i, self.stations[i+1:], seat_destinations, seat_ticket_price_list, False)
            confirmed_bookings_sleep[i] = self.confirm_passengers(i, self.stations[i+1:], sleep_destinations, sleep_ticket_price_list, True)
            potential_retain_rate += sum(confirmed_bookings_seat[i])/potential_passengers
            if len(self.promotions) > 0 and have_a_target_promotion:
                passengers_before_promotion += np.sum(confirmed_bookings_seat[i])
                if night_train:
                    passengers_before_promotion += np.sum(confirmed_bookings_sleep[i])
            """ Add in extras due to promotions """
            for j in range(len(extras_disembarking)):
                if night_train:
                    seat_disembark = np.round((2 / 3) * extras_disembarking[j], 0)
                    sleep_disembark = np.round((1 / 3) * extras_disembarking[j], 0)
                    confirmed_bookings_sleep[i][extras_disembarking_index[j] - i - 1] += sleep_disembark
                else:
                    seat_disembark = extras_disembarking[j]
                confirmed_bookings_seat[i][extras_disembarking_index[j] - i - 1] += seat_disembark
        potential_retain_rate /= len(self.stations)
        """ Now we need to check that there is space for everyone on the train and that it is not over-booked."""
        capacity_seat = self.car_capacity['passenger car'] * self.config[1]
        capacity_sleep = self.car_capacity['sleeper car'] * self.config[2]
        seat_passengers = self.remove_overbookings(capacity_seat, confirmed_bookings_seat)
        sleep_passengers = self.remove_overbookings(capacity_sleep, confirmed_bookings_sleep)
        total_seat = 0
        for station in seat_passengers:
            total_seat += np.sum(station)
        if self.stations_reversed:
            self.number_seat_passengers_all_time_return.append(total_seat)
        else:
            self.number_seat_passengers_all_time.append(total_seat)
        """ We need to report additional passengers back to the promotion so the player can gauge how success it was.
            However this is not particularly exact, and should be displayed with an *approximately* clause"""
        if len(self.promotions) > 0:
            if have_a_target_promotion:
                passengers_after_promotion = 0
                for i in range(len(seat_passengers)):
                    passengers_after_promotion += np.sum(seat_passengers[i])
                    if night_train:
                        passengers_after_promotion += np.sum(sleep_passengers[i])
                promotion_passenger_total = passengers_after_promotion - passengers_before_promotion
                if promotion_passenger_total < 0:
                    promotion_passenger_total = 0  # this is the case where the train was overbooked to start with.
                for p in self.promotions:
                    p.report_back(promotion_passenger_total/len(self.promotions))
            else:
                for p in self.promotions:
                    p.report_back(potential_retain_rate * overall_potential_increase_promotion)
        self.passenger_confidence = np.minimum(1, self.passenger_confidence + 0.01)
        return seat_passengers, sleep_passengers

    def score_passengers(self, seat_p, sleep_p):
        """
        This calculates the passenger km score
        :param seat_p:
        :param sleep_p:
        :return:
        """
        score = 0
        for i in range(len(seat_p)):
            distances = self.distance_between_stations[i:]
            for j in range(len(seat_p[i])):
                d = np.sum(distances[:j])
                score += d * seat_p[i][j]
                if sleep_p is not None and sleep_p[i] is not None:
                    score += d * sleep_p[i][j]
        return score

    def ticket_passengers(self, seat_p, sleep_p):
        ticket_revenue = 0
        for i in range(len(seat_p)):
            for j in range(len(seat_p[i])):
                ticket_revenue += self.get_ticket_price(j - i) * seat_p[i][j]
                if sleep_p is not None and sleep_p[i] is not None:
                    ticket_revenue += self.get_ticket_price(j - i, sleeper=True) * sleep_p[i][j]
        return ticket_revenue

    def run_these_services(self, services_to_run, day_of_week, score, company_reputation, date):
        profit = 0
        returning_services = []
        for service in services_to_run:
            service = datetime.datetime.combine(date, service.time())
            if not self.stations_reversed:
                self.time_service_was_run.append(service)
            seat_passengers, sleep_passengers = self.get_passengers(service, day_of_week, company_reputation)
            score.put_on_buffer(self.score_passengers(seat_passengers, sleep_passengers))
            profit += self.ticket_passengers(seat_passengers, sleep_passengers)
            profit -= self.calculate_gst(profit)
            profit -= self.calculate_cost()
            profit -= self.calculate_tax(profit)
            if self.returns and not self.stations_reversed:
                time_of_run = service + self.get_journey_length(0, len(self.stations)-1) + datetime.timedelta(minutes=10)
                self.time_service_was_run_return.append(time_of_run)
                returning_services.append(time_of_run)
        if len(returning_services) > 0:
            self.reverse_stations()
            self.run_these_services(returning_services, day_of_week, score, company_reputation, date)
            self.reverse_stations()
        return profit

    def run(self, increment, time, wallet, score, company_reputation):
        """
        Runs the train all the train services between time_0 and time_1, note this is called after the time is
        incremented so t_0 is time-increment to get back to pre-incremented time.
        :param increment: The amount the time was incremented
        :param time: The current time (after increment)
        :return:
        """
        if not self.confirmed:
            return "P"  # if the service is unconfirmed, it does not run.
        time_0 = time - increment
        time_1 = time
        t = time_0
        for p in self.promotions:
            if p.check_expiry(time_1):
                increase = p.get_lasting_effect()
                for town in self.stations:
                    town.increase_percentage_willing(increase, percentage=True)
                self.promotions.remove(p)
        while t < time_1:
            if self.days[t.weekday()]:  # if this is a day in which the train is scheduled
                first_departure = None
                for i, dep_time in enumerate(self.departure_times):
                    if t.time() <= dep_time.time():
                        first_departure = i
                        logger.debug("found first departure")
                        break
                if first_departure is None:
                    # time is already later than all the departures, so not runs today. Reset to 00:00 on next day
                    t += datetime.timedelta(days=1)
                    t -= datetime.timedelta(hours=t.time().hour, minutes=t.time().minute, seconds=t.time().second,
                                            microseconds=t.time().microsecond)
                    # returns to start of while loop
                else:
                    profit = self.run_these_services(self.departure_times[first_departure:], t.weekday(), score, company_reputation, t.date())
                    if wallet.addsubtract(profit, time.strftime("%d/%m/%y"), details=f"running cost of {self.name}"):
                        score.push_buffer()
                        return "P"
                    else:
                        return f"F You went bankrupt while trying to run the service {self.get_name()}"
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
        """ Estimates the cost of doing the trip by car, so that passengers have a base point to compare prices
            The congestion charge is meant to make trains more competitive near urban centres, it is a bit of
            a one-size-fits-all method."""
        petrol_price = 1.98  # todo: slowly inflate prices
        km_per_litre = 15
        congestion_charge = 5
        if distance < 20:
            return (distance / km_per_litre) * petrol_price + congestion_charge
        return (distance / km_per_litre) * petrol_price

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

    def calculate_gst(self, amount):
        return amount * 0.15

    def calculate_cost(self):
        return self.get_running_cost()

    def calculate_tax(self, profit):
        if profit > 0:
            return profit * 0.33
        else:
            return 0
