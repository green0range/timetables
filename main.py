import os
import random
import sys
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5 import uic
import numpy as np
import datetime
import json
from matplotlib import pyplot
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas

import achievements
import gscreen
import promotions
import saves
from towns import Town
from service import Service
import hints
import logging
import clipboard
import webbrowser
logger = logging.Logger(name="main")
import sound

mlogger = logging.getLogger('matplotlib')
mlogger.setLevel(logging.WARNING)


def alphabet_sort(item):
    return item.get_name()


class MainWindow(QtWidgets.QMainWindow):

    def __init__(self, scr_size, *args, **kwargs):
        """ A lot of boilerplate stuff here"""
        super().__init__(*args, **kwargs)
        self.hint_timer = 0
        self.hint_dict = {"clicked_reports": False,
                          "never_true": False,
                          "opened_promotions_menu": False,
                          "6pm_ad_time_selected": False,
                          "confirmed_ad": False}
        self.screen_size = scr_size
        self.music = sound.Music()
        self.showFullScreen()  # the map image size is set based on the startup screen size, so don't resize!
        self.intermediate_towns = []
        self.towns = []
        self.score = gscreen.Score()
        self.create_towns()  # loads the town data from a json file
        uic.loadUi('main_window.ui', self)  # loads the ui from Qt Designer
        self.wallet = gscreen.Wallet()
        self.mode_show_map = True
        self.gr_left = QtWidgets.QGridLayout(self.frm_map)
        self.gr_left.setAlignment(QtCore.Qt.AlignTop)
        self.map_image = None
        self.hints = hints.HintManager()
        ''' get some fonts'''
        font_id1 = QtGui.QFontDatabase.addApplicationFont(os.path.abspath(os.path.join('assets', 'fonts', 'Arvo-Bold.ttf')))
        font_id2 = QtGui.QFontDatabase.addApplicationFont(
            os.path.abspath(os.path.join('assets', 'fonts', 'RobotoMono-VariableFont_wght.ttf')))
        self.title_font = QtGui.QFontDatabase.applicationFontFamilies(font_id1)[0]
        self.message_font = QtGui.QFontDatabase.applicationFontFamilies(font_id2)[0]
        ''' Now we are connecting signals with slots'''
        self.btn_new_route.clicked.connect(self.clicked_new_route)
        self.frm_new_route.setVisible(False)
        self.gr_intermediate_stops = QtWidgets.QGridLayout(self.frm_intermediate_stops)
        self.frmscrl_route_select = QtWidgets.QFrame()
        self.frmscrl_route_select.setMinimumHeight(200)
        self.gr_list_of_routes = QtWidgets.QGridLayout(self.frmscrl_route_select)
        self.gr_list_of_routes.setAlignment(QtCore.Qt.AlignTop)
        self.scr_route_select.setWidget(self.frmscrl_route_select)
        self.colours = gscreen.ServiceColours()
        self.towns.sort(key=alphabet_sort)
        for town in self.towns:
            self.cmb_from.addItem(town.get_name())
        self.cmb_from_selection_changed(self.cmb_from.currentText())
        self.cmb_from.currentTextChanged.connect(self.cmb_from_selection_changed)
        self.cmb_to.currentTextChanged.connect(self.cmb_to_selection_changed)
        ''' Image stuff '''
        pix_engine = QtGui.QPixmap()
        pix_engine.load("assets/engine_thb.png")
        self.lbl_engine.setPixmap(pix_engine)
        pix_passenger = QtGui.QPixmap()
        pix_passenger.load("assets/passenger_thb.png")
        self.lbl_passenger_car.setPixmap(pix_passenger)
        pix_sleeper = QtGui.QPixmap()
        pix_sleeper.load("assets/sleeper_thm.png")
        self.lbl_sleeper.setPixmap(pix_sleeper)
        # map image
        self.img_map = gscreen.Map(int(self.screen_size.width()*0.5), self.screen_size.height(), self.towns, self.wallet, self.score, self.colours)
        self.update_map_image()
        ''' Services are train services between two towns (with possible intermediate stops). The service Objects holds
            all information about a service, such as what the carriage setup is etc. The service object starts as
            `unconfirmed` meaning the train doesn't actually run until the status is changed to `confirmed`
            One unconfirmed service always exists on the tail of the self.services, which is the one altered by the
            route/service planner menu'''
        self.save_manager = saves.SaveManager()
        self.services = [Service(self.save_manager)]
        self.unconfirmed_service = self.services[0]
        self.fill_intermediate_towns(self.get_town_by_name(self.cmb_from.currentText()),
                                     self.get_town_by_name(self.cmb_to.currentText()))
        '''More boilerplate signal connection, to update the unconfirmed service whenever a change is made.'''
        self.ckb_return.stateChanged.connect(self.update_unconfirmed_service)
        self.departure_time_edit.timeChanged.connect(self.update_unconfirmed_service)
        self.ckb_run_every_x_hour.stateChanged.connect(self.update_unconfirmed_service)
        self.dbl_run_every_x_hour.valueChanged.connect(self.update_unconfirmed_service)
        self.ckb_mon.stateChanged.connect(self.update_unconfirmed_service)
        self.ckb_tue.stateChanged.connect(self.update_unconfirmed_service)
        self.ckb_wed.stateChanged.connect(self.update_unconfirmed_service)
        self.ckb_thu.stateChanged.connect(self.update_unconfirmed_service)
        self.ckb_fri.stateChanged.connect(self.update_unconfirmed_service)
        self.ckb_sat.stateChanged.connect(self.update_unconfirmed_service)
        self.ckb_sun.stateChanged.connect(self.update_unconfirmed_service)
        self.sb_engines.valueChanged.connect(self.update_unconfirmed_service)
        self.sb_passenger_car.valueChanged.connect(self.update_unconfirmed_service)
        self.sb_sleeper_car.valueChanged.connect(self.update_unconfirmed_service)
        #self.sb_open_air.valueChanged.connect(self.update_unconfirmed_service)
        #self.sb_baggage.valueChanged.connect(self.update_unconfirmed_service)
        self.dsb_sleeper_fare.valueChanged.connect(self.update_unconfirmed_service)
        self.dsb_seat_fare.valueChanged.connect(self.update_unconfirmed_service)
        self.btn_confirm.clicked.connect(self.click_confirm_new_route)
        self.timer = QtCore.QTimer()
        self.tick_rate = 1  # number of updates every second
        self.timer.setInterval(int(self.tick_rate*1000))
        self.timer.setTimerType(QtCore.Qt.CoarseTimer)
        self.timer.timeout.connect(self.tick)
        self.btn_toggle_speed.clicked.connect(self.img_map.change_speed)
        self.btn_bounding_nz.clicked.connect(lambda: self.set_view("nz"))
        self.btn_bounding_n.clicked.connect(lambda: self.set_view("north"))
        self.btn_bounding_s.clicked.connect(lambda: self.set_view("south"))
        self.achievements = achievements.Achievements()
        self.btn_achievements.clicked.connect(self.display_achievements)
        self.towns_with_services = []  # this allows tracking progress to have 90% towns connected.
        self.show_menu()
        self.btn_exit.clicked.connect(self.save_and_exit)
        self.company_reputation = 0.5
        self.btn_disable_hint.clicked.connect(self.hints.setDisabled)
        self.fr_hint.setVisible(False)

    def set_view(self, id):
        """
        For selecting which island to show on the map screen
        :param id: either nz, north or south
        :return: None
        """
        self.img_map.change_bounding_box(id)
        self.img_map.redraw()
        self.update_map_image()
        if id == "nz":
            self.btn_bounding_nz.setChecked(True)
            self.btn_bounding_n.setChecked(False)
            self.btn_bounding_s.setChecked(False)
        elif id == "north":
            self.btn_bounding_nz.setChecked(False)
            self.btn_bounding_n.setChecked(True)
            self.btn_bounding_s.setChecked(False)
        elif id == "south":
            self.btn_bounding_nz.setChecked(False)
            self.btn_bounding_n.setChecked(False)
            self.btn_bounding_s.setChecked(True)

    def display_achievements(self):
        """
        Shows all the achievements on the left panel (instead of the default map). Achievements that are complete
        will have their title crossed out to indicate they are done
        :return: None
        """
        ach_all = self.achievements.get_all_achievements()
        ach_done = self.achievements.get_completed_achievements(self.services[:len(self.services)-1])
        self.close_report()
        if self.mode_show_map:
            self.mode_show_map = False
            if self.map_image is not None:
                self.gr_left.removeWidget(self.map_image)
                self.map_image = None
        for key in ach_all:
            lbl = QtWidgets.QLabel(f"<h4>{key}</h4>")
            if key in ach_done:
                lbl.setText(f"<s><h4>{key}</h4></s>")
            lbl_descript = QtWidgets.QLabel(ach_all[key])
            lbl_descript.setFont(QtGui.QFont(self.message_font, 10))
            self.gr_left.addWidget(lbl)
            self.gr_left.addWidget(lbl_descript)
        objectives = achievements.get_objectives()
        if self.img_map.get_time().year >= 2030:
            txt_reminder = "<h4>Reminder:<h4> Achievements are nice and all but your compulsory objectives are\n" \
                           f" 1. <s>Connect {objectives[0]}% of towns by 2030</s>\n 2. Connect {objectives[1]}% of towns by 2050\n" \
                           f"3. <s>Transport {objectives[2]}pkm in 2029</s>\n 4. Transport {objectives[3]}pkm in 2049"
        else:
            txt_reminder = "<h4>Reminder:<h4> Achievements are nice and all but your compulsory objectives are\n" \
                            f" 1. Connect {objectives[0]}% of towns by 2030\n 2. Connect {objectives[1]}% of towns by 2050\n" \
                            f" 3. Transport {objectives[2]}pkm in 2029\n 4. Transport {objectives[3]}pkm in 2049"
        lbl_reminder = QtWidgets.QLabel(txt_reminder)
        lbl_reminder.setWordWrap(True)
        lbl_reminder.setFont(QtGui.QFont(self.message_font, 10))
        self.gr_left.addWidget(lbl_reminder)
        btn_close = QtWidgets.QPushButton("Close")
        btn_close.clicked.connect(self.close_report)
        self.gr_left.addWidget(btn_close)

    def start_game(self, rb1, rb2, rb3, difficulty):
        """
        Starts the game. This method is called when the start game button is pressed on the menu screen. It
        sets the save slot, enables all the buttons, removes the menu from the screen and starts the game
        timer.
        :param: rb1: the radio button that indicates if slot 1 is selected.
        :param: rb2: the radio button that indicates if slot 2 is selected.
        :param: rb3: the radio button that indicates if slot 3 is selected.
        :return: None
        """
        # this locks the size of the left frame, because resizing in a video game looks tacky, and QT likes to
        # automatically resize things.
        frm_l_size = self.frm_left.size()
        self.frm_left.setMaximumSize(frm_l_size)
        self.frm_left.setMinimumSize(frm_l_size)
        if difficulty == "Unlimited Money":
            self.wallet.money = 99999999999999
        self.btn_bounding_nz.setChecked(True)
        slot = None
        if rb1.isChecked():
            slot = 1
        elif rb2.isChecked():
            slot = 2
        elif rb3.isChecked():
            slot = 3
        self.save_manager.set_save_slot(slot)
        self.wallet.set_save_dir(self.save_manager)
        load_data = self.save_manager.load()
        if load_data is not None:  # returns None if there is no save in the slot
            logger.info("Loading game state from file")
            self.wallet, self.score, self.towns, self.services, self.img_map = load_data
            self.unconfirmed_service = self.services[len(self.services)-1]
            self.img_map.load_wallet_score(self.wallet, self.score)
            for i, service in enumerate(self.services):
                if i == len(self.services)-1:
                    self.unconfirmed_service = service
                else:
                    for town in service.stations:
                        if town not in self.towns_with_services:
                            self.towns_with_services.append(town)
                    self.update_services_panel(service)
            self.img_map.update_percent_connected(len(self.towns_with_services) / len(self.towns))
        self.timer.start()
        self.btn_new_route.setEnabled(True)
        self.btn_pause.setEnabled(True)
        self.btn_toggle_speed.setEnabled(True)
        self.btn_bounding_nz.setEnabled(True)
        self.btn_bounding_n.setEnabled(True)
        self.btn_bounding_s.setEnabled(True)
        self.btn_achievements.setEnabled(True)
        self.fr_hint.setVisible(True)
        self.close_report()

    def delete_save(self, slot, radiobutton):
        self.save_manager.delete_save(slot)
        radiobutton.setText(f"Slot {slot} - new")

    def save_and_exit(self):
        if self.save_manager.save_slot is not None:
            self.save_manager.save(self.wallet, self.score, self.towns, self.services, self.img_map)
        self.close()

    def get_emissions_plot(self):
        """
        Makes the emissions plot seen in the introduction email on the menu screen.
        :return: None
        """
        with open(os.path.join("assets", "emissions_data.json"), encoding='utf-8') as f:
            data = json.load(f)
        labels = []
        x = []
        explode = []
        for key in data:
            if key != "units" and key != "source":
                labels.append(key)
                x.append(data[key])
                if key == "Transport":
                    explode.append(0.1)
                else:
                    explode.append(0)
        pyplot.rcParams.update({'font.size': 5})
        fig1, ax1 = pyplot.subplots(figsize=(4, 1.5), dpi=130)
        canvas = FigureCanvas(fig1)
        ax1.pie(x, explode=explode, labels=labels)
        ax1.axis('equal')
        canvas.draw()
        width, height = canvas.get_width_height()
        im = QtGui.QImage(canvas.buffer_rgba(), width, height, QtGui.QImage.Format_ARGB32)
        return QtGui.QPixmap.fromImage(im)

    def share(self, btn, message, original_text):
        """
        Copies a message to the clipboard. It changes the button to read "copied to clipboard" then changes the
        text back to the original 1-second later.
        :param btn: button that called this function
        :param message: message to copy
        :param original_text: the original text of the button (what it will be set back to)
        :return: None
        """
        clipboard.copy(message)
        btn.setText("Copied to clipboard")
        t = QtCore.QTimer()
        t.singleShot(1000, lambda: btn.setText(original_text))


    def show_menu(self):
        """
        Shows the start of game menu, where the user can select which save slot to use and see the instructions
        Note: this reuses the report_widgets array
        :return: None
        """
        if self.mode_show_map:
            self.mode_show_map = False
            if self.map_image is not None:
                self.gr_left.removeWidget(self.map_image)
                self.map_image = None
        frm_menu = QtWidgets.QFrame()
        frm_menu.setMinimumSize(int(self.screen_size.width()*0.5) - 50, self.screen_size.height() - 50)
        gr_frm_menu = QtWidgets.QGridLayout(frm_menu)
        #gr_frm_menu.setAlignment(QtCore.Qt.AlignTop)
        scroll_area = QtWidgets.QScrollArea()
        scroll_area.setWidget(frm_menu)
        scroll_area.setObjectName("a")
        lbl_title = QtWidgets.QLabel("TIMETABLES! \n(The train scheduling game)")
        lbl_title.setFont(QtGui.QFont(self.title_font, 20))
        rb_slot1 = QtWidgets.QRadioButton("Slot 1 - "+self.save_manager.get_save_time(1))
        rb_slot1.setChecked(True)
        rb_slot2 = QtWidgets.QRadioButton("Slot 2 - "+self.save_manager.get_save_time(2))
        rb_slot3 = QtWidgets.QRadioButton("Slot 3 - "+self.save_manager.get_save_time(3))
        btn_slot1_clear = QtWidgets.QPushButton("Delete Saved Data")
        btn_slot1_clear.clicked.connect(lambda: self.delete_save(1, rb_slot1))
        btn_slot2_clear = QtWidgets.QPushButton("Delete Saved Data")
        btn_slot2_clear.clicked.connect(lambda: self.delete_save(2, rb_slot2))
        btn_slot3_clear = QtWidgets.QPushButton("Delete Saved Data")
        btn_slot3_clear.clicked.connect(lambda: self.delete_save(3, rb_slot3))
        with open(os.path.join("assets", "welcome_email.txt"), "r", encoding='utf-8') as f:
            intro_txt1, intro_txt2 = f.read().split("^")  # this is where the plot goes
        lbl_message1 = QtWidgets.QLabel(intro_txt1)
        lbl_message1.setFont(QtGui.QFont(self.message_font, 8))
        lbl_message1.setWordWrap(True)
        lbl_plot = QtWidgets.QLabel("")
        lbl_plot.setPixmap(self.get_emissions_plot())
        a = intro_txt2.split("*")
        o = achievements.get_objectives()
        intro_txt2 = a[0] + str(o[0]) + a[1] + str(o[1]) + a[2] + str(o[2]) + a[3] + str(o[3]) + a[4]
        lbl_message2 = QtWidgets.QLabel(intro_txt2)
        lbl_message2.setFont(QtGui.QFont(self.message_font, 8))
        lbl_message2.setWordWrap(True)
        cmb_difficulty = QtWidgets.QComboBox()
        cmb_difficulty.addItems(["Normal Difficulty", "Unlimited Money"])
        btn_begin = QtWidgets.QPushButton("Start Game")
        btn_begin.clicked.connect(lambda: self.start_game(rb_slot1, rb_slot2, rb_slot3, cmb_difficulty.currentText()))
        ''' If release, this will go to a highscores webpage, but for now I will use it to get feedback'''
        btn_highscore = QtWidgets.QPushButton("Send Feedback")
        btn_highscore.clicked.connect(lambda: webbrowser.open("https://docs.google.com/forms/d/e/1FAIpQLSdnpQeyxYQPsScqqeVxJuE9IL74KrecaWQhIOkMUz5ov5wKCA/viewform?usp=sf_link"))
        btn_share = QtWidgets.QPushButton("Share with friend")
        share_text = "Hey friend! I'm playing a game about scheduling trains, you should get it too! https://timetablesgame.nz"
        btn_share.clicked.connect(lambda: self.share(btn_share, share_text, "Share with friend"))
        share_mp_text = """Dear Member of Parliament,

I'm writing to tell you about a political video game I think you should try. It is about scheduling trains to avoid the worst effects of climate change.
I think you could use it for both some light entertainment and as a first step in informing public transport policy!

You can find out more about it at https://timetablesgame.nz"""
        btn_share_mp = QtWidgets.QPushButton("Share with your MP")
        btn_share_mp.clicked.connect(lambda: self.share(btn_share_mp, share_mp_text, "Share with your MP"))
        gr_frm_menu.addWidget(lbl_title, 0, 0)
        gr_frm_menu.addWidget(rb_slot1, 1, 0)
        gr_frm_menu.addWidget(rb_slot2, 2, 0)
        gr_frm_menu.addWidget(rb_slot3, 3, 0)
        gr_frm_menu.addWidget(btn_slot1_clear, 1, 1)
        gr_frm_menu.addWidget(btn_slot2_clear, 2, 1)
        gr_frm_menu.addWidget(btn_slot3_clear, 3, 1)
        gr_frm_menu.addWidget(rb_slot2, 2, 0)
        gr_frm_menu.addWidget(rb_slot3, 3, 0)
        gr_frm_menu.addWidget(lbl_message1, 4, 0, 1, 2)
        gr_frm_menu.addWidget(lbl_plot,  5, 0, 1, 2)
        gr_frm_menu.addWidget(lbl_message2, 6, 0, 1, 2)
        gr_frm_menu.addWidget(cmb_difficulty, 7, 0, 1, 2)
        gr_frm_menu.addWidget(btn_begin, 8, 0)
        gr_frm_menu.addWidget(btn_highscore, 8, 1)
        gr_frm_menu.addWidget(btn_share, 9, 0)
        gr_frm_menu.addWidget(btn_share_mp, 9, 1)
        self.gr_left.addWidget(scroll_area, 1, 0)

    def show_win_screen(self):
        """
        This screen should be shown when the player wins the game (gets to 2050 and passes all the checks)
        :return: None
        """
        self.timer.stop()  # halt game progress
        if self.mode_show_map:
            self.mode_show_map = False
            if self.map_image is not None:
                self.gr_left.removeWidget(self.map_image)
                self.map_image = None
        lbl_game_over = QtWidgets.QLabel("SUCCESS!")
        lbl_game_over.setFont(QtGui.QFont(self.title_font, 20))
        lbl = QtWidgets.QLabel("You won! Ngā mihi nui for building our public transport network!")
        btn = QtWidgets.QPushButton("Close")
        btn.clicked.connect(self.close)
        self.gr_left.addWidget(lbl_game_over)
        self.gr_left.addWidget(lbl)
        self.gr_left.addWidget(btn)

    def show_fail_screen(self, message):
        """
        This screen should be shown if the player fails to meet the 2030 or 2050 requirements or if they run go
        bankrupt.
        :param message: The reason the failed the game - this is shown to the play
        :return: None
        """
        self.timer.stop()  # halt game progress
        if self.mode_show_map:
            self.mode_show_map = False
            if self.map_image is not None:
                self.gr_left.removeWidget(self.map_image)
                self.map_image = None
        lbl_game_over = QtWidgets.QLabel("GAME OVER!")
        lbl_game_over.setFont(QtGui.QFont(self.title_font, 20))
        lbl = QtWidgets.QLabel(message)
        btn = QtWidgets.QPushButton("Close")
        btn.clicked.connect(self.close)
        self.gr_left.addWidget(lbl_game_over)
        self.gr_left.addWidget(lbl)
        self.gr_left.addWidget(btn)

    def show_caution(self, message):
        """
        Shows a warning to the player, e.g. if they can't afford a new train then use this to show a "not enough money"
        screen. Unlike the fail and win screens, the player can dismiss the message and it doesn't effect the game.
        :param message: message to show the player
        :return: None
        """
        if self.mode_show_map:
            self.mode_show_map = False
            if self.map_image is not None:
                self.gr_left.removeWidget(self.map_image)
                self.map_image = None
        lbl = QtWidgets.QLabel(message[2:])
        btn = QtWidgets.QPushButton("Close")
        btn.clicked.connect(self.close_report)
        self.gr_left.addWidget(lbl)
        self.gr_left.addWidget(btn)

    def tick(self):
        """
        This is called every second and updates the map, tests for win conditions, and runs all the services that
        occured in the last second (which is 1 day in game-time if not on fast-mode)
        :return:
        """
        self.music.on_tick()
        if not self.btn_pause.isChecked():
            win = self.img_map.update_time(self.tick_rate)
            """win will be of form [P/W/F] REASON where P = PASS/PROCEED (do nothing), W = WIN, F = FAIL
                There is also the code C = CAUTION, used when the player is unable to afford a new service."""
            if win[0] == "W":
                self.show_win_screen()
            elif win[0] == "F":
                self.show_fail_screen(win[2:])
            for service in self.services:
                response = service.run(self.img_map.get_increment(), self.img_map.get_time(), self.wallet, self.score, self.company_reputation)
                if response[0] == "F":
                    self.show_fail_screen(response[2:])
            if self.hints.enabled:
                self.hint_dict["btn_new_route_is_toggled"] = self.btn_new_route.isChecked()
                self.hint_dict["cmb_from_get_text"] = self.cmb_from.currentText()
                self.hint_dict["cmb_to_get_text"] = self.cmb_to.currentText()
                self.hint_dict['timer'] = self.hint_timer
                self.hint_dict['number_of_services'] = len(self.services) - 1
                self.hint_dict['departure_time_get_current_time'] = self.departure_time_edit.time().toString("hh:mm")
                self.hint_dict['saturday_and_sunday_is_checked'] = (self.ckb_sat.isChecked() and self.ckb_sun.isChecked())
                self.hint_dict['num_seat_cars'] = self.sb_passenger_car.value()
                self.hint_dict['seat_price'] = self.dsb_seat_fare.value()
                self.hint_dict['btn_north_island_is_checked'] = self.btn_bounding_n.isChecked()
                try:
                    self.hint_dict["chk_hamilton_is_checked"]
                except KeyError:
                    self.hint_dict['chk_hamilton_is_checked'] = False
                self.hint_timer += 1
                self.lbl_hint.setText(self.hints.get_text())
                if self.hints.check(self.hint_dict):
                    self.hints.next_hint()
                    self.hint_timer = 0
        self.update_map_image()

    def update_map_image(self):
        """
        This gets the map image from gscreen.Map and sets it to self.map_image
        :return: None
        """
        if self.mode_show_map:
            if self.map_image is None:
                self.map_image = QtWidgets.QLabel("")
                self.gr_left.addWidget(self.map_image)
                self.map_image.show()
            qim = self.img_map.get_image_qt()
            pix_map_img = QtGui.QPixmap.fromImage(qim)
            self.map_image.setPixmap(pix_map_img)

    def update_unconfirmed_service(self):
        """
        This methods is called whenever something in the New Route panel is changed. It updates the work-in-progress
        service to reflect the changes. It then called the method update_service_dependant_widgets
        :return:
        """
        total_car_allowed = self.sb_engines.value() * 10
        self.sb_sleeper_car.setMaximum(total_car_allowed - self.sb_passenger_car.value())
        self.sb_passenger_car.setMaximum(total_car_allowed - self.sb_sleeper_car.value())
        stations = []
        for station in self.intermediate_towns:
            if station.isChecked():
                if station.text() == "Hamilton":
                    self.hint_dict['chk_hamilton_is_checked'] = True
                stations.append(self.get_town_by_name(station.text()))
        returns = self.ckb_return.isChecked()
        fmt = "%H:%M"
        departure_times = [datetime.datetime.strptime(self.departure_time_edit.time().toString("HH:mm"), fmt)]
        if self.ckb_run_every_x_hour.isChecked():
            start_time = departure_times[0]
            day = start_time.day
            while start_time.day == day:
                start_time += datetime.timedelta(hours=self.dbl_run_every_x_hour.value())
                departure_times.append(start_time)
            departure_times.pop()
        days = [self.ckb_mon.isChecked(), self.ckb_tue.isChecked(), self.ckb_wed.isChecked(), self.ckb_thu.isChecked(),
                self.ckb_fri.isChecked(), self.ckb_sat.isChecked(), self.ckb_sun.isChecked()]
        config = [self.sb_engines.value(), self.sb_passenger_car.value(), self.sb_sleeper_car.value(),
                  0, 0]
        fares = [self.dsb_seat_fare.value(), self.dsb_sleeper_fare.value()]
        self.unconfirmed_service.update(stations, returns, departure_times, days, config, fares)
        self.update_service_dependant_widgets()
        self.txt_service_name.setPlaceholderText(self.unconfirmed_service.create_name())

    def update_service_dependant_widgets(self):
        self.lbl_feedback_1.setText(f"This train will be able to carry a maximum of {self.unconfirmed_service.get_capacity()} passengers, cost ${self.unconfirmed_service.get_up_front_cost()} to build and ${self.unconfirmed_service.get_running_cost()}/journey to run")
        self.lbl_feedback_2.setText(f"Expected Revenue per journey at 70% full is ${np.round(self.unconfirmed_service.get_estimated_revenue(),2)}, giving an expected profit of ${np.round(self.unconfirmed_service.get_estimated_profit(),2)} before tax")
        self.lcd_arrival_time.display(self.unconfirmed_service.get_arrival_time())
        self.lcd_return_time.display(self.unconfirmed_service.get_return_time())

    def create_towns(self):
        """
        This imports the towns.json file and sets up the towns tree structure. It is called on __init__
        :return: None
        """
        file = "towns.json"
        with open(file, "r", encoding='utf-8') as f:
            towns_data = json.load(f)
        connections = []
        for town in towns_data:
            name = town
            connections.append(towns_data[name]['connections'])
            population = towns_data[name]['population']
            location = towns_data[name]['location']
            new_town = Town(name, population, location, self.score)
            self.towns.append(new_town)
        for conns, town in zip(connections, self.towns):
            for conn in conns:
                if conn[0] != "":
                    try:
                        town.add_link(self.get_town_by_name(conn[0]), float(conn[1]))
                    except:
                        print(conn[0])
        for town in towns_data:
            try:
                self.get_town_by_name(town).add_economic_partner(self.get_town_by_name(towns_data[town]["economic "
                                                                                                        + "partner"]))
            except KeyError:
                pass  # not all towns have economic partners and this is OK!

    def get_town_by_name(self, name):
        """
        Returns the town object associated with the given name. E.g. get_town_by_name("Ōtaki") will return the
        towns.Town object representing Ōtaki
        :param name: name of town (case and macro sensitive)
        :return: towns.Town object representing the named town or None if not found.
        """
        for town in self.towns:
            if town.get_name() == name:
                return town

    def fill_intermediate_towns(self, departure_town, arrival_town):
        """
        This finds all towns on a train line between two endpoint towns and places them on the intermediate stops
        panel. The endpoint towns are also placed on the panel pre-ticked and non-changeable.
        :param departure_town: 1st endpoint
        :param arrival_town: 2nd endpoint
        :return: None
        """
        path = departure_town.getNodesOnPath(arrival_town)
        for town in self.intermediate_towns:
            self.gr_intermediate_stops.removeWidget(town)
            town.destroy()
        self.intermediate_towns = []
        j = 0
        i = 0
        for node in path:
            i += 1
            if i > 5:
                i = 0
                j += 1
            ckb = QtWidgets.QCheckBox(node.get_name(), parent=self.frm_intermediate_stops)
            ckb.stateChanged.connect(self.update_unconfirmed_service)
            self.gr_intermediate_stops.addWidget(ckb, j, i)
            if node is departure_town or node is arrival_town:
                ckb.setChecked(True)
                ckb.setEnabled(False)
            ckb.show()
            self.intermediate_towns.append(ckb)
        self.update_unconfirmed_service()

    def cmb_from_selection_changed(self, text):
        """
        Called when the combo-box for the departure town is changed. When this happens we need to reassess which towns
        can be connected to the departure town and update the arrival town combo-box.
        :param text: text of the combo box, which is just the name of the town
        :return: None
        """
        for town in self.towns:
            if town.get_name() == text:
                all_connected = town.getAllNodes()
                all_connected.remove(town)
                self.cmb_to.clear()
                for ac in all_connected:
                    self.cmb_to.addItem(ac.get_name())

    def cmb_to_selection_changed(self, text):
        if text != "":  # while the updates occurs it sometimes trigger this with empty text.
            self.fill_intermediate_towns(self.get_town_by_name(self.cmb_from.currentText()), self.get_town_by_name(text))

    def clicked_new_route(self, toggled):
        self.frm_new_route.setVisible(toggled)

    def close_report(self):
        """
        Delete everything from the left panel, then sets the flag to show the map (which is the default for when nothing
        else is using the panel.
        :return: None
        """
        for i in reversed(range(self.gr_left.count())):
            self.gr_left.itemAt(i).widget().setParent(None)
        self.mode_show_map = True
        self.update_map_image()

    def fill_report_table(self, table, stations, passenger_numbers, earnings):
        col_num = len(passenger_numbers[0][0])
        current_row = 0
        for i, station in enumerate(stations):
            table.setItem(current_row, 0, QtWidgets.QTableWidgetItem("Time"))
            table.setItem(current_row, 1, QtWidgets.QTableWidgetItem("Profit"))
            table.setItem(current_row, i + 2, QtWidgets.QTableWidgetItem(station.get_name()))
        current_row += 1
        for (numbers, earn) in zip(passenger_numbers, earnings):
            table.setItem(current_row, 0, QtWidgets.QTableWidgetItem(earn[1]))
            table.setItem(current_row, 1, QtWidgets.QTableWidgetItem(f"{earn[0]}nz$"))
            table.setItem(current_row, 2, QtWidgets.QTableWidgetItem("Departures: (seat/sleep)"))
            table.setSpan(current_row, 2, 1, col_num)
            current_row += 1
            for i in range(len(numbers[0])):
                table.setItem(current_row, i + 2,
                              QtWidgets.QTableWidgetItem(f"{int(numbers[0][i])}/{int(numbers[2][i])}"))
            current_row += 1
            table.setItem(current_row, 2, QtWidgets.QTableWidgetItem("Arrivals: (seat/sleep)"))
            table.setSpan(current_row, 2, 1, col_num)
            current_row += 1
            for i in range(len(numbers[1])):
                table.setItem(current_row, i + 2,
                              QtWidgets.QTableWidgetItem(f"{int(numbers[1][i])}/{int(numbers[3][i])}"))
            current_row += 1

    def plot_profit(self, profit, date, lims=None):
        fig1, ax1 = pyplot.subplots(figsize=(3, 3.3), dpi=130)
        canvas = FigureCanvas(fig1)
        ax1.plot(date, profit)
        ax1.set_title("Profit / Loss")
        ax1.set_xlabel("date")
        ax1.tick_params(rotation=90)
        ax1.xaxis.set_major_locator(pyplot.MaxNLocator(20))
        if lims is not None:
            ax1.set_ylim(lims)
        pyplot.subplots_adjust(bottom=0.5)
        ax1.set_ylabel("Profit, $")
        canvas.draw()
        width, height = canvas.get_width_height()
        im = QtGui.QImage(canvas.buffer_rgba(), width, height, QtGui.QImage.Format_ARGB32)
        pyplot.close(fig1)
        return QtGui.QPixmap.fromImage(im)

    def plot_ridership(self, seat, sleep, date, title='Ridership', lims=None):
        fig1, ax1 = pyplot.subplots(figsize=(3, 3.3), dpi=130)
        canvas = FigureCanvas(fig1)
        ax1.plot(date, seat)
        try:
            ax1.plot(date, sleep)
        except:
            pass
        ax1.set_title(title)
        ax1.set_xlabel("date")
        ax1.set_ylabel("Number of people")
        ax1.xaxis.set_major_locator(pyplot.MaxNLocator(20))
        if lims is not None:
            ax1.set_ylim(lims)
        ax1.tick_params(rotation=90)
        pyplot.subplots_adjust(bottom=0.5)
        canvas.draw()
        width, height = canvas.get_width_height()
        im = QtGui.QImage(canvas.buffer_rgba(), width, height, QtGui.QImage.Format_ARGB32)
        pyplot.close(fig1)
        return QtGui.QPixmap.fromImage(im)

    def display_report(self, service):
        self.hint_dict['clicked_reports'] = True
        self.close_report()
        if self.mode_show_map:
            self.mode_show_map = False
            if self.map_image is not None:
                self.gr_left.removeWidget(self.map_image)
                self.map_image = None
        seat_numbers = service.number_seat_passengers_all_time
        seat_numbers_return = service.number_seat_passengers_all_time_return
        date = [""]*len(service.time_service_was_run)
        for i in range(len(date)):
            date[i] = service.time_service_was_run[i].strftime("%a %d %b '%y")
        profit = service.profit_all_time
        profit_return = service.profit_all_time_return
        sleep_numbers = service.number_sleep_passengers_all_time
        sleep_numbers_return = service.number_seat_passengers_all_time_return
        lbl_title = QtWidgets.QLabel(f"Service Report for {service.get_name()}")
        lbl_title.setFont(QtGui.QFont(self.title_font, 16))
        """ Generate some information about the train service."""
        information = f"Train information: \nConfiguration: {service.config[0]} Engine(s), {service.config[1]} Passenger cars, "
        information += f"{service.config[2]} Sleeper cars \nTotal Capacity: {service.get_capacity()} Passengers\n"
        information += f"Ticket prices: ${service.fares[0]} for seat, ${service.fares[1]} for sleepers\n"
        list_times = ""
        for i, time in enumerate(service.departure_times):
            if i == len(service.departure_times)-1:
                list_times += time.strftime("%H:%M")
            else:
                list_times += time.strftime("%H:%M") + ", "
        information += f"Departs {service.stations[0].get_name()} at {list_times}\n"
        s = service.get_journey_length(0, len(service.stations)-1).total_seconds()
        hours, remainder = divmod(s, 3600)
        minutes, seconds = divmod(remainder, 60)
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        runs_on_days = []
        for i in range(len(service.days)):
            if service.days[i]:
                runs_on_days.append(days[i])
        runs_on_days_text = ""
        if len(days) == 1:
            runs_on_days_text = days[0]
        else:
            for i, day in enumerate(runs_on_days):
                if i == len(runs_on_days) - 1:
                    runs_on_days_text += "and " + day
                    break
                runs_on_days_text += day + ", "
        information += f"Train runs on {runs_on_days_text}"
        information += f"Arrives at {service.stations[len(service.stations)-1].get_name()} after {hours} hrs, {minutes} mins\n"
        stops = ""
        for i, station in enumerate(service.stations):
            if i == len(service.stations) - 1:
                stops += "and " + station.get_name()
                break
            stops += station.get_name() + ", "
        information += f"Train stops at {stops}\n"
        if service.returns:
            information += f"Train returns to {service.stations[0].get_name()} along the same route"
        else:
            information += f"Train has no return journey"
        lbl_info = QtWidgets.QLabel(information)
        if len(seat_numbers) == 0:
            self.gr_left.addWidget(lbl_title, 0, 0)
            lbl_404 = QtWidgets.QLabel("404.\nNot found :(\n\nMaybe the train hasn't made its first journey yet?\n\nTrains only run at their scheduled time. Check the game is not paused \nand wait for the game time to reach the next scheduled time.")
            lbl_404.setFont(QtGui.QFont(self.message_font, 14))
            self.gr_left.addWidget(lbl_404, 1, 0)
            close = QtWidgets.QPushButton("Close")
            close.clicked.connect(self.close_report)
            self.gr_left.addWidget(close, 4, 0, 1, 2)
            return
        self.gr_left.addWidget(lbl_title, 0, 0, 1, 2)
        self.gr_left.addWidget(lbl_info, 1, 0, 1, 2)
        lbl_passengers_all_time = QtWidgets.QLabel()
        limit_passenger = (0, service.get_capacity()+10)
        max_income = service.car_capacity['passenger car'] * service.config[1] * service.fares[0]
        max_income += service.car_capacity['sleeper car'] * service.config[2] * service.fares[1]
        max_income -= service.get_running_cost()
        limit_money = (-1 * service.get_running_cost(), max_income)
        lbl_passengers_all_time.setPixmap(self.plot_ridership(seat_numbers, sleep_numbers, date, lims=limit_passenger))
        self.gr_left.addWidget(lbl_passengers_all_time, 2, 0)
        lbl_profit = QtWidgets.QLabel()
        lbl_profit.setPixmap(self.plot_profit(profit, date, lims=limit_money))
        self.gr_left.addWidget(lbl_profit, 2, 1)
        if service.returns:
            lbl_passengers_all_time_return = QtWidgets.QLabel()
            lbl_passengers_all_time_return.setPixmap(self.plot_ridership(seat_numbers_return, sleep_numbers_return, date, title="Ridership of returning train", lims=limit_passenger))
            self.gr_left.addWidget(lbl_passengers_all_time_return, 3, 0)
            lbl_profit_return = QtWidgets.QLabel()
            lbl_profit_return.setPixmap(self.plot_profit(profit_return, date, lims=limit_money))
            self.gr_left.addWidget(lbl_profit_return, 3, 1)
        close = QtWidgets.QPushButton("Close")
        close.clicked.connect(self.close_report)
        self.gr_left.addWidget(close, 10, 0, 1, 2)
        '''
        col_num = len(passenger_numbers[0][0])
        self.gr_left.addWidget(lbl_title, 0, 0, 1, 2)
        lbl_profit_plot = QtWidgets.QLabel()
        lbl_profit_plot.setPixmap(self.plot_profit(earnings))
        lbl_ridership_plot = QtWidgets.QLabel()
        lbl_ridership_plot.setPixmap(self.plot_ridership(passenger_numbers, earnings))
        lbl_raw_data = QtWidgets.QLabel("Raw data:")
        self.gr_left.addWidget(lbl_raw_data, 2, 0)
        self.gr_left.addWidget(lbl_profit_plot, 1, 0)
        self.gr_left.addWidget(lbl_ridership_plot, 1, 1)
        table = QtWidgets.QTableWidget(5*len(passenger_numbers), col_num+2)
        self.gr_left.addWidget(table, 3, 0, 1, 2)
        if service.returns:
            lbl_titler = QtWidgets.QLabel(f"The returning train")
            lbl_titler.setFont(QtGui.QFont(self.title_font, 16))
            passenger_numbers_return = service.get_passenger_numbers_report(returns_report=True)
            earnings_return = service.get_earnings_report(returns_report=True)
            table_return = QtWidgets.QTableWidget(5 * len(passenger_numbers), col_num + 2)
            self.gr_left.addWidget(table_return, 7, 0, 1, 2)
            stations = service.get_stations()
            stations.reverse()
            lbl_profit_plot = QtWidgets.QLabel()
            lbl_profit_plot.setPixmap(self.plot_profit(earnings_return))
            lbl_ridership_plot = QtWidgets.QLabel()
            lbl_ridership_plot.setPixmap(self.plot_ridership(passenger_numbers_return, earnings_return))
            lbl_raw_data = QtWidgets.QLabel("Raw data:")
            self.gr_left.addWidget(lbl_raw_data, 6, 0)
            self.gr_left.addWidget(lbl_profit_plot, 5, 0)
            self.gr_left.addWidget(lbl_ridership_plot, 5, 1)
            self.gr_left.addWidget(lbl_titler, 4, 0, 1, 2)
            self.fill_report_table(table_return, stations, passenger_numbers_return, earnings_return)
        close = QtWidgets.QPushButton("Close")
        close.clicked.connect(self.close_report)
        self.gr_left.addWidget(close, 10, 0, 1, 2)
        self.fill_report_table(table, service.get_stations(), passenger_numbers, earnings)
        '''

    def delete_service(self, service, widgets):
        """
        Removes a train service
        :param service: the service to remove (service.Service object)
        :param widgets: the qtwidget representing that service in the list of services panel
        :return: None
        """
        self.company_reputation -=1
        widgets[0].removeWidget(widgets[1])
        widgets[0].removeWidget(widgets[2])
        widgets[0].removeWidget(widgets[3])
        self.gr_list_of_routes.removeWidget(widgets[0].parentWidget())
        self.colours.remove(service)
        # we have to completely redo, because if we just delete to towns that this service services, then we may miss
        # a town that is also serviced by another route.
        for i, candidate in enumerate(self.services):
            if candidate is service:
                self.services.pop(i)
                self.img_map.update_connection_ids()
                break
        self.towns_with_services = []
        for i, service in enumerate(self.services):
            if i == len(self.services) - 1:
                pass
            else:
                for town in service.stations:
                    if town not in self.towns_with_services:
                        self.towns_with_services.append(town)
        self.img_map.update_percent_connected(len(self.towns_with_services) / len(self.towns))

    def marketing(self, service):
        """
        Shows the marketing screen, so that the user can make promotes for a particular service, or for train transport
        generally. Types of marketing should be: TV ads, social media ads, posters, print ads.
        :param service: The service to adverise
        :return:
        """
        self.close_report()
        if self.mode_show_map:
            self.mode_show_map = False
            if self.map_image is not None:
                self.gr_left.removeWidget(self.map_image)
                self.map_image = None
        lbl_title = QtWidgets.QLabel("Promote your train services")
        lbl_title.setFont(QtGui.QFont(self.title_font, 20))
        lbl1 = QtWidgets.QLabel("Campaign type:")
        scr_campaign_options = QtWidgets.QScrollArea()
        scr_campaign_options.setMinimumSize(700, 500)
        grscr_campaign_options = QtWidgets.QGridLayout(scr_campaign_options)
        grscr_campaign_options.setAlignment(QtCore.Qt.AlignTop)
        cmb_campaign = QtWidgets.QComboBox()
        cmb_campaign.addItems(["Television Advertisement",
                               "Radio Advertisement", "Print Media Advertisement", "Nostalgic New Zealand Railways poster"])
        cmb_campaign.currentTextChanged.connect(lambda: self.marketing_select_campaign(cmb_campaign, grscr_campaign_options))
        self.gr_left.addWidget(lbl_title, 0, 0, 1, 2)
        self.gr_left.addWidget(lbl1, 1, 0)
        self.gr_left.addWidget(cmb_campaign, 1, 1)
        self.gr_left.addWidget(scr_campaign_options, 2, 0, 1, 2)
        self.marketing_select_campaign(cmb_campaign, grscr_campaign_options)

    def marketing_poster_selection_change(self, img_lbl, image_path, lbl_descript, new_descript):
        image = QtGui.QImage(image_path)
        img_lbl.setPixmap(QtGui.QPixmap.fromImage(image))
        lbl_descript.setText(new_descript)

    def _6pm_ad_time_checked(self):
        self.hint_dict['6pm_ad_time_selected'] = True

    def marketing_select_campaign(self, cmb_campaign, grid):
        self.hint_dict['opened_promotions_menu'] = True
        btn_close = QtWidgets.QPushButton("Close")
        btn_close.clicked.connect(self.close_report)
        btn_buy_campaign = QtWidgets.QPushButton("Buy Advertisement Campaign")
        for i in reversed(range(grid.count())):
            grid.itemAt(i).widget().setParent(None)
        ad_info = {}
        if cmb_campaign.currentText() == "Nostalgic New Zealand Railways poster":
            about = "An intern found these old posters in a dusty draw! We will pin them up around town and leave " \
                    "them there until someone rips them off or vandalises them."
            lbl_about = QtWidgets.QLabel(about)
            lbl_about.setWordWrap(True)
            path = os.path.join("assets", "old_NZR_posters")
            posters = []
            with open(os.path.join(path, "data.json"), "r", encoding="utf-8") as f:
                poster_data = json.load(f)
            for file in os.listdir(path):
                name, extension = file.split(".")
                if extension == "jpg":
                    posters.append(name)
            cmb_poster = QtWidgets.QComboBox()
            cmb_poster.addItems(posters)
            cmb_poster.setCurrentText("FranzJosef")  # This is the default entirely because I am writing this in Franz, and it is my personal favourite!
            lbl_select_poster = QtWidgets.QLabel("Select Poster:")
            lbl_poster_image = QtWidgets.QLabel("")
            lbl_description = QtWidgets.QLabel(f"Promotes Travel to: {poster_data[cmb_poster.currentText()]['target']}")
            cmb_poster.currentTextChanged.connect(lambda: self.marketing_poster_selection_change(lbl_poster_image,
                                                                                      os.path.join(path, cmb_poster.currentText()),
                                                                                      lbl_description,
                                                                                      f"Promotes Travel to: {poster_data[cmb_poster.currentText()]['target']} \nPosters will be displayed in {poster_data[cmb_poster.currentText()]['putsPostersText']} \nCampaign cost: ${poster_data[cmb_poster.currentText()]['cost']}"))
            self.marketing_poster_selection_change(lbl_poster_image, os.path.join(path, cmb_poster.currentText()),
                                                   lbl_description,
                                                   f"Promotes Travel to: {poster_data[cmb_poster.currentText()]['target']} \nPosters will be displayed in {poster_data[cmb_poster.currentText()]['putsPostersText']} \nCampaign cost: ${poster_data[cmb_poster.currentText()]['cost']}")
            grid.addWidget(lbl_about, 2, 0, 1, 2)
            grid.addWidget(lbl_select_poster, 3, 0)
            grid.addWidget(cmb_poster, 3, 1)
            grid.addWidget(lbl_poster_image, 4, 0, 1, 2)
            grid.addWidget(lbl_description, 5, 0, 1, 2)
            ad_info = {
                "type": "poster",
                "posterData": poster_data,
                "cmb_poster": cmb_poster
            }
        elif cmb_campaign.currentText() == "Television Advertisement":
            about = "TV ads are broadcast across the motu at the selected times for 2 weeks from the start of the " \
                    "campaign."
            lbl_about = QtWidgets.QLabel(about)
            lbl_about.setWordWrap(True)
            cmb_service_to_promote = QtWidgets.QComboBox()
            list_of_services_named = ['Tranz-Passenger company (All services)']
            for s in self.services:
                if s.confirmed:
                    list_of_services_named.append(s.get_name())
            cmb_service_to_promote.addItems(list_of_services_named)
            lbl_select_service = QtWidgets.QLabel("Select Service to promote:")
            lbl_when = QtWidgets.QLabel("When should the ad be broadcast? (You can select more than one)")
            ck_7am = QtWidgets.QCheckBox("7 am ($70,000)")
            ck_noon = QtWidgets.QCheckBox("Noon ($40,000)")
            ck_6pm = QtWidgets.QCheckBox("6 pm ($140,000)")
            ck_6pm.clicked.connect(self._6pm_ad_time_checked)
            ck_9pm = QtWidgets.QCheckBox("9 pm ($100,000)")
            grid.addWidget(lbl_when, 3, 0, 1, 2)
            grid.addWidget(ck_7am, 4, 0)
            grid.addWidget(ck_noon, 4, 1)
            grid.addWidget(ck_6pm, 5, 0)
            grid.addWidget(ck_9pm, 5, 1)
            grid.addWidget(lbl_about, 2, 0, 1, 2)
            grid.addWidget(lbl_select_service, 6, 0)
            grid.addWidget(cmb_service_to_promote, 6, 1)
            ad_info = {
                "type": "tv",
                "ck_7am": ck_7am,
                "ck_noon": ck_noon,
                "ck_6pm": ck_6pm,
                "ck_9pm": ck_9pm,
                "cmb_service": cmb_service_to_promote
            }
        elif cmb_campaign.currentText() == "Radio Advertisement":
            about = "Radio ads are like TV ads but cheaper and less effective. A campaign will be broadcast " \
                    "for two weeks at the selected times."
            lbl_about = QtWidgets.QLabel(about)
            lbl_about.setWordWrap(True)
            cmb_service_to_promote = QtWidgets.QComboBox()
            list_of_services_named = ['Tranz-Passenger company (All services)']
            for s in self.services:
                if s.confirmed:
                    list_of_services_named.append(s.get_name())
            cmb_service_to_promote.addItems(list_of_services_named)
            lbl_select_service = QtWidgets.QLabel("Select Service to promote:")
            lbl_when = QtWidgets.QLabel("When should the ad be broadcast? (You can select more than one)")
            ck_7am = QtWidgets.QCheckBox("7 am ($30,000)")
            ck_noon = QtWidgets.QCheckBox("Noon ($20,000)")
            ck_6pm = QtWidgets.QCheckBox("6 pm ($50,000)")
            ck_9pm = QtWidgets.QCheckBox("9 pm ($40,000)")
            grid.addWidget(lbl_when, 3, 0, 1, 2)
            grid.addWidget(ck_7am, 4, 0)
            grid.addWidget(ck_noon, 4, 1)
            grid.addWidget(ck_6pm, 5, 0)
            grid.addWidget(ck_9pm, 5, 1)
            grid.addWidget(lbl_about, 2, 0, 1, 2)
            grid.addWidget(lbl_select_service, 6, 0)
            grid.addWidget(cmb_service_to_promote, 6, 1)
            ad_info = {
                "type": "radio",
                "ck_7am": ck_7am,
                "ck_noon": ck_noon,
                "ck_6pm": ck_6pm,
                "ck_9pm": ck_9pm,
                "cmb_service": cmb_service_to_promote
            }
        elif cmb_campaign.currentText() == "Social Media Advertisement":
            about = "Social media ads can be targeted at specific demographics. At Tranz-passenger, we aim to serve " \
                    "all demographics so this feature isn't actually useful. You can also target based the location " \
                    "the user is logging in from, which could be useful!"
            lbl_about = QtWidgets.QLabel(about)
            lbl_about.setWordWrap(True)
            cmb_service_to_promote = QtWidgets.QComboBox()
            list_of_services_named = ['Tranz-Passenger company (All services)']
            for s in self.services:
                if s.confirmed:
                    list_of_services_named.append(s.get_name())
            cmb_service_to_promote.addItems(list_of_services_named)
            lbl_select_service = QtWidgets.QLabel("Select Service to promote:")
            lbl_demographic = QtWidgets.QLabel("Select target demographic:")
            cmb_demographic = QtWidgets.QComboBox()
            cmb_demographic.addItems(['no demographic targeting', 'business travelers', 'under 30s', 'families',
                                      'holiday makers', 'environmentally conscious travelers', 'retired people'])
            ck_target_location = QtWidgets.QCheckBox("Only target people in towns where the selected service stops.")
            grid.addWidget(lbl_about, 2, 0, 1, 2)
            grid.addWidget(lbl_select_service, 3, 0)
            grid.addWidget(cmb_service_to_promote, 3, 1)
            grid.addWidget(lbl_demographic, 4, 0)
            grid.addWidget(cmb_demographic, 4, 1)
            grid.addWidget(ck_target_location, 5, 0, 1, 2)
            ad_info = {
                "type": "social media",
                "cmb_demographic": cmb_demographic,
                "ck_target_location": ck_target_location
            }
        elif cmb_campaign.currentText() == "Print Media Advertisement":
            about = "This puts an ad in newspapers and magazines. You can choose to only put ads in local papers, or " \
                    "nationwide. It costs $60,000 for all newspapers, or $10,000 to just target local papers."
            lbl_about = QtWidgets.QLabel(about)
            lbl_about.setWordWrap(True)
            cmb_service_to_promote = QtWidgets.QComboBox()
            list_of_services_named = ['Tranz-Passenger company (All services)']
            for s in self.services:
                if s.confirmed:
                    list_of_services_named.append(s.get_name())
            cmb_service_to_promote.addItems(list_of_services_named)
            lbl_select_service = QtWidgets.QLabel("Select Service to promote:")
            ck_target_location = QtWidgets.QCheckBox("Only place ads in papers local to the selected service")
            grid.addWidget(lbl_about, 2, 0, 1, 2)
            grid.addWidget(lbl_select_service, 3, 0)
            grid.addWidget(cmb_service_to_promote, 3, 1)
            grid.addWidget(ck_target_location, 4, 0, 1, 2)
            ad_info = {
                "type": "print media",
                'cmb_service_2_promote': cmb_service_to_promote,
                "ck_target_location": ck_target_location
            }
        btn_buy_campaign.clicked.connect(lambda: self.buy_campaign(ad_info))
        grid.addWidget(btn_close, 10, 1)
        grid.addWidget(btn_buy_campaign, 10, 0)

    def buy_campaign(self, info):
        self.hint_dict["confirmed_ad"] = True
        if info['type'] == 'poster':
            selection = info['cmb_poster'].currentText()
            target_town = info['posterData'][selection]['target']
            cost = info['posterData'][selection]['cost']
            puts_posters = info['posterData'][selection]['putsPosters']
            promo = promotions.Promotion(self.img_map)
            if self.wallet.addsubtract(-cost, self.img_map.get_time().strftime("%d-%m-%y"), "Buy Ad Campaign - Poster"):
                response = promo.add_poster_promotion(target_town, puts_posters, self.img_map.get_time(), self.services[:len(self.services)-1])
                self.close_report()
                if response[0] == "C":
                    self.wallet.addsubtract(cost, self.img_map.get_time().strftime("%d-%m-%y"), "Ad Campaign refund")
                    self.show_caution(response[0:])
            else:
                self.show_caution("Not enough money")
        elif info['type'] == 'print media':
            if info['ck_target_location'].isChecked():
                cost = 10000
            else:
                cost = 60000
            if self.wallet.addsubtract(-cost, self.img_map.get_time().strftime("%d-%m-%y"), "Buy Ad Campaign - Print media"):
                promo = promotions.Promotion(self.img_map)
                promo.add_print_media(info['cmb_service_2_promote'].currentText(), self.img_map.get_time(), self.services[:len(self.services)-1], info['ck_target_location'].isChecked())
                self.close_report()
            else:
                self.show_caution("Not enough money")
        elif info['type'] == 'social media':
            self.show_caution("This feature is still under development")
        elif info['type'] == 'radio':
            cost = 0
            times = []
            if info['ck_7am'].isChecked():
                cost += 30000
                times.append(7)
            if info['ck_noon']:
                cost += 20000
                times.append(12)
            if info['ck_6pm']:
                cost += 50000
                times.append(18)
            if info['ck_9pm']:
                cost += 40000
                times.append(21)
            if self.wallet.addsubtract(-cost, self.img_map.get_time().strftime("%d-%m-%y"), "Buy Ad Campaign - TV"):
                promo = promotions.Promotion(self.img_map)
                promo.add_radio(info['cmb_service'].currentText(), self.img_map.get_time(),
                                self.services[:len(self.services) - 1], times)
                self.close_report()
            else:
                self.show_caution("Not enough money")
        elif info['type'] == 'tv':
            cost = 0
            times = []
            if info['ck_7am'].isChecked():
                cost += 70000
                times.append(7)
            if info['ck_noon']:
                cost += 40000
                times.append(12)
            if info['ck_6pm']:
                cost += 140000
                times.append(18)
            if info['ck_9pm']:
                cost += 100000
                times.append(21)
            if self.wallet.addsubtract(-cost, self.img_map.get_time().strftime("%d-%m-%y"), "Buy Ad Campaign - TV"):
                promo = promotions.Promotion(self.img_map)
                promo.add_tv_ad(info['cmb_service'].currentText(), self.img_map.get_time(),
                                      self.services[:len(self.services) - 1], times)
                self.close_report()
            else:
                self.show_caution("Not enough money")


    def update_services_panel(self, service):
        """
        Adds a new service to the list of services panel
        :param service: The new service to add (towns.Service)
        :return: None
        """
        frm_service_panel = QtWidgets.QFrame()
        frm_service_panel.setObjectName(f"frm_service_panel{self.colours.get_colour_number(service)}")
        self.img_map.update_connection_ids()
        self.update_map_image()
        frm_service_panel.setMaximumHeight(50)
        self.gr_list_of_routes.addWidget(frm_service_panel)
        gr_service_panel = QtWidgets.QGridLayout(frm_service_panel)
        service_panel = QtWidgets.QLabel(service.get_name())
        service_report = QtWidgets.QPushButton("Service Report")
        service_report.clicked.connect(lambda: self.display_report(service))
        btn_promote = QtWidgets.QPushButton("Promote")
        btn_promote.clicked.connect(lambda: self.marketing(service))
        service_remove = QtWidgets.QPushButton("Delete")
        service_remove.clicked.connect(lambda: self.delete_service(service, [gr_service_panel, service_panel, service_report, service_remove]))
        gr_service_panel.addWidget(service_panel, len(self.services), 0)
        gr_service_panel.addWidget(service_report, len(self.services), 1)
        gr_service_panel.addWidget(btn_promote, len(self.services), 2)
        gr_service_panel.addWidget(service_remove, len(self.services), 3)
        service_panel.show()
        for i in range(len(self.services)-1):
            terminal_stations = self.services[i].get_terminal_stations()
            times_at_terminal_stations = self.services[i].get_terminal_station_times()
            if service.is_connecting(terminal_stations, times_at_terminal_stations):
                service.has_connection = True
                self.services[i].has_connection = True
                logger.debug(f"{self.services[i].get_name()} connects to {service.get_name()}")
                break

    def click_confirm_new_route(self):
        self.company_reputation += random.randint(0, 2)
        name = self.txt_service_name.text()
        self.update_unconfirmed_service()
        response = self.unconfirmed_service.confirm_service(name, self.wallet, self.img_map.get_time().strftime("%d/%m/%y"))
        if response[0] == "C":
            self.show_caution(response)
        else:
            new_achieves = self.achievements.check_for_new_achievement(self.unconfirmed_service)
            self.img_map.display_new_achievement(new_achieves)
            for town in self.unconfirmed_service.stations:
                if town not in self.towns_with_services:
                    self.towns_with_services.append(town)
            self.img_map.update_percent_connected(len(self.towns_with_services) / len(self.towns))
            self.update_services_panel(self.unconfirmed_service)
            self.unconfirmed_service = Service(self.save_manager)
            self.services.append(self.unconfirmed_service)
            self.btn_new_route.setChecked(False)
            self.clicked_new_route(False)

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    size = app.primaryScreen().size()
    with open("style.css", "r", encoding='utf-8') as f:
        app.setStyleSheet(f.read())
    window = MainWindow(scr_size=size)
    window.show()
    app.exec_()
