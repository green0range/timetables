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


class Town:
    def __init__(self, name, population, coords, score):
        self.hour_of_train_departure = None
        self.want_to_travel = np.zeros(24)
        self.name = name
        self.population = int(population)
        self.coords = coords
        self.connections = []
        self.predecessor = None
        self.distance_to_predecessor = 0
        self.economic_partners = []
        self.last_date_want_to_travels_generated = None
        self.visitors = 0
        self.percentage_willing_to_use_public_transport = 0.1
        self.score = score
        self.year = 2020

    def get_latlgn(self):
        return self.coords

    def number_of_directions(self):
        return len(self.connections)

    def increase_percentage_willing(self, increase_amount, percentage=False):
        if percentage:
            self.percentage_willing_to_use_public_transport *= increase_amount
        else:
            self.percentage_willing_to_use_public_transport += increase_amount
        if self.percentage_willing_to_use_public_transport > 0.95:
            self.percentage_willing_to_use_public_transport = 0.95

    def generate_want_to_travels(self, rep_score, dow):
        """
        This should find the number of people who want to travel out of the city on any given day. I'm not quite sure
        what this will be and propose the following study:
            Go the exit highway of a city and count people in cars exiting the city for one hour.
            Multiply by the number of highways exiting the city.
            Multiply by 12 (because much fewer people will be travelling at night)
            Repeat in many cities.
            Plot against population and fit the curve to get a formula for number of people travelling each day.
            Flaws: variable travel times, airports, trains, buses (hard to count individuals in buses), people
            travelling out a few km and coming back (not actually travelling intercity).
        If anyone knows of a study like this, please encode the result in this method!
        Anyway, once we have the formula, we return that multiplied by the percentage of people willing to travel on
        public transport, with some added random flucations.
        param: rep_score: this is the reputation of the company and particular service.
        :return:
        """
        if self.score.year != self.year:
            if self.score.goals_achieved[self.year - 2020]:
                ''' If all targets are hit, the percentage willing to use public transport will reach 90% at 2050.
                    The idea behind this is that more people will be willing to use PT if they can see it is 
                    successful.
                    percentage_willing can also be increased by running successful ads, so it is caped at 95%'''
                self.percentage_willing_to_use_public_transport = np.minimum(self.percentage_willing_to_use_public_transport + 0.0163, 0.95)
            else:
                ''' Give a smaller increase so that it is possible to recover.'''
                self.percentage_willing_to_use_public_transport = np.minimum(
                    self.percentage_willing_to_use_public_transport + 0.005, 0.95)
            self.year = self.score.year
            self.population *= 1.02  # 2% population growth
        """0 = Monday, 1 = T, 2 = W, 3 = T, 4 = F, 5 = Saturday, 6 = Sunday"""
        if dow == 5 or dow == 6:
            daily_travel_weights = [2, 1, 1, 1, 1, 1, 1, 1, 2, 5, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 10, 10, 5]
        elif dow == 4:
            daily_travel_weights = [2, 1, 1, 2, 2, 5, 10, 50, 20, 10, 10, 10, 15, 10, 10, 30, 10, 40, 40, 40, 20, 10, 10, 5]
        else:
            daily_travel_weights = [1, 1, 1, 2, 2, 5, 10, 50, 20, 10, 10, 10, 15, 10, 10, 30, 10, 40, 40, 40, 20, 10, 5, 2]
        model = np.minimum(np.log(self.population**3)*np.sqrt(self.population), self.population*0.7)
        ''' This model is my guess. Smaller settlements have a relatively high proportion of travellers because they
            need to travel to a larger settlement for work, shopping etc, whereas the proportion of people traveling 
            lowers as the town gets larger because people can work and get stuff locally so only need to travel to 
            visit people go on holiday, less frequent business trips etc. '''
        variation = 0.3 * (random.random() - 1)  # variation between -0.25 and 0.25
        want_to_travel_all_modes = model + (variation * model)
        if 1 <= rep_score < 2:
            willing_bonus = 0.05
        elif 2 <= rep_score < 4:
            willing_bonus = 0.1
        elif 4 <= rep_score < 5:
            willing_bonus = 0.15
        elif 5 <= rep_score < 7:
            willing_bonus = 0.17
        elif 7 <= rep_score < 10:
            willing_bonus = 0.185
        elif rep_score >= 10:
            willing_bonus = 0.2
        else:
            willing_bonus = 0
        self.want_to_travel = (self.percentage_willing_to_use_public_transport + willing_bonus) * want_to_travel_all_modes
        """ Now account for the visitors that r currently in the town. All recorded visitors arrived by rail, so they
            are willing to travel back (or onwards) by rail. Some of them will be staying permanently, or not actually
            be a visitor and have just returned home, so a number of the visitors are discounted, then the rest are
            added to the want_to_travels. Here the number travelling onward is randomly chosen between 30% and 70% """
        self.want_to_travel += ((0.4 * random.random()) + 0.3) * self.visitors
        self.visitors = 0  # the rest will stay
        self.want_to_travel = self.split_to_list(self.want_to_travel, daily_travel_weights)

    @staticmethod
    def split_to_list(number, weights):
        pieces = number / np.sum(weights)
        result = np.zeros(len(weights))
        for i, w in enumerate(weights):
            result[i] = pieces * w
        return result

    def get_want_to_travels(self, date, time, rep_score=0, dow=0):
        """
        Each day, a new group of people who want to travel are generated, based on population size, with some random
        chance. The available travelers are those people, plus any positive count of visitors. When a person leaves
        the visitor count is decremented, and incremented when they arrive. The visitor count is allowed to go negative
        if people are leaving the town, it should always be close to zero as some people will return on the next train
        and increase it again. If abs(visitor) > 5% of population, then this is an indication the player has found an
        explort that must be nerfed.
        :param date:  The date the train is departing. People who want to travel is only updated daily, but the want to
        travels have a preferred hour that they want to travel in. (This is to encourage players to run trains multiple
        time day.)
        :return: number of people available to travel
        """
        if self.last_date_want_to_travels_generated is None:
            self.generate_want_to_travels(rep_score, dow)
            self.last_date_want_to_travels_generated = date
        elif self.last_date_want_to_travels_generated != date:
            self.generate_want_to_travels(rep_score, dow)
            self.last_date_want_to_travels_generated = date
            logger.debug(f"generated want to travels for date {date}")
        self.hour_of_train_departure = time.hour
        return self.want_to_travel[time.hour]

    def person_departed(self):
        if self.hour_of_train_departure is None:
            logger.error("Cannot have people departing without first checking how many people want to travel.")
            return
        self.want_to_travel[self.hour_of_train_departure] -= 1

    def person_arrived(self):
        self.visitors += 1

    def people_departed(self, num):
        if self.hour_of_train_departure is None:
            logger.error("Cannot have people departing without first checking how many people want to travel.")
            return
        self.want_to_travel[self.hour_of_train_departure] -= num

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
            # if p is endNode:
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
