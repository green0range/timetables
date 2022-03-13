class Hint:
    def __init__(self, text, check_key, check_value):
        self.done_check = False
        self.txt = text
        self.check_key = check_key
        self.check_value = check_value
        self.next = None

    def get_next(self):
        if self.next is None:
            if not self.done_check:
                self.txt = "Hint error, this is the last hint. \n"+self.txt
                self.done_check = True
            return self
        else:
            return self.next

    def set_next(self, next_hint):
        self.next = next_hint

    def getText(self):
        return self.txt

    def doCheck(self, check_dict):
        try:
            return check_dict[self.check_key] == self.check_value
        except KeyError:
            if not self.done_check:
                self.done_check = True
                self.txt = f"Hint error, did not find key {self.check_key}. Please make sure you send this key!\n{self.txt}"
            return False

class HintManager:
    def __init__(self):
        self.enabled = True
        self.hint_params = [["Let's schedule your first train: click New Route", "btn_new_route_is_toggled", True],
                            ["Now lets run a train between the economic capital and political capital. In the drop down labelled 'from', select Auckland.", "cmb_from_get_text", "Auckland"],
                            ["The next drop down is for the trains destination, select Wellington. Towns in this box are sorted by their distance from the departure town and will only show if the towns are linked by rail.", "cmb_to_get_text", "Wellington"],
                            ["The software finds the shortest route, you can put a tick next to any towns on the route to make the train stop at these towns along the way. Tick Hamilton, and any others you want.", "chk_hamilton_is_checked", True],
                            ["Now the returns check box automatically schedules a return train, if checked, the train will return to Auckland after reaching Wellington.", "timer", 7],
                            ["Next let's set the departure time to 7:30. Notice that the arrival time and return time adjust automatically because the trains will run at a set speed. Trains stop at stations for 10 minutes. Express trains do not stop at any stations except the departure and destination stations.", "departure_time_get_current_time", "07:30"],
                            ["The day of the week is also important for scheduling trains. Make this one a daily service, tick Saturday and Sunday.", 'saturday_and_sunday_is_checked', True],
                            ["Almost there, let's make the train set. Each engine can pull 10 cars. Setup 1 engine, 10 passenger cars and 0 sleeper cars.", "num_seat_cars", 10],
                            ["What's the price? Set the price for a seat ticket to $58 so that we are undercuting the intercity bus! (intercity bus is $59 as of 15-feb-2022)", "seat_price", 58],
                            ["All that's left to do is click confirm! ( ...and give it a cool name if you want :p )", "number_of_services", 1],
                            ["Awesome! You just created your first train service! See how the route map on the left updates to show where the service goes. Let's zoom in on it, click Te-Ika-A-Māui to see just the North Island.", "btn_north_island_is_checked", True],
                            ["Ah, we can see it from closer in! You can select whichever island your working on by click on their name, or click Aotearoa to see the whole Motu!", "timer", 7],
                            ["Let's check how your train is doing. See the route listing on the right? Click Service Report to see how many people are travelling on the train and what profit you're making from tickets.", "clicked_reports", True],
                            ["Each train has set costs to run, based on staffing and fuel requirements. You will earn variable income based on how many passengers you transport and which stops they get off at.", "timer", 7],
                            ["You will lose the game if you run out of money, or if you do not meet the service and passenger km requirements.", "timer", 7],
                            ["But it is hard of people to change their habits, you can convince more people to take your train but running an advertising campaign. Click the `promote` button to bring up the advertising menu.", "opened_promotions_menu", True],
                            ["Now you can select various campaigns, from T.V. to old posters! Let's try a big T.V. ad. to kick things off! Check the 6pm time slot, it is the most expensive and most effective as people like watching the news then.", "6pm_ad_time_selected", True],
                            ["Great, now you can promote a specific service, or the company. Promoting a specific service results in a bigger passenger increase, but only for that service. Promoting the company means all you trains get a more mild boost in passenger numbers.", "timer", 10],
                            ["Anyway, confirm your ad, then check back on the service report to see if you got any more passengers. Keep promoting your trains until they start to turn a profit.", "confirmed_ad", True],
                            ["Now setup at least 5 more route, anywhere you like.", "number_of_services", 5],
                            ["FIVE ROUTE! That's TWO more than actually exist (as of 15-feb-2022, counting: Te Huria, Capital Connection and Tranz Alpine).", "timer", 7],
                            ["Now you can delete a service if you really need to, but no one likes a service cut so make sure you never actually do this!", "timer", 7],
                            ["Great! You've completed the tutorial. Click the `Achievements` button to remind yourself of your objectives and see which optional achievements you can complete. Now get those trains going!", "never_true", True]]

        self.hint_params.reverse()
        next_h = None
        for i, hint in enumerate(self.hint_params):
            print(hint)
            h = Hint(hint[0], hint[1], hint[2])
            if i == len(self.hint_params)-1:
                self.current_hint = h
                self.current_hint.set_next(next_h)
            else:
                if i != 0:
                    h.set_next(next_h)
                next_h = h


    def get_text(self):
        return self.current_hint.getText()

    def setDisabled(self):
        self.enabled = False


    def next_hint(self):
        self.current_hint = self.current_hint.get_next()

    def check(self, check_dict):
        return self.current_hint.doCheck(check_dict)

