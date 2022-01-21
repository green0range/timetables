import datetime
import os
import pickle


class SaveManager():
    def __init__(self):
        self.save_slot = None

    def get_save_time(self, slotnum):
        path = os.path.join("saves", f"slot{slotnum}")
        save_time = "new"
        if os.path.exists(path):
            with open(os.path.join(path, "savetime.txt"), "r") as f:
                save_time = f.read()
        return save_time.strip("\n")

    def get_dir(self):
        return os.path.join("saves", f"slot{self.save_slot}")

    def set_save_slot(self, slot):
        self.save_slot = slot

    def save(self, wallet, score, towns, services, map_):
        self.delete_save(self.save_slot)  # delete any old save data
        path = os.path.join("saves", f"slot{self.save_slot}")
        os.mkdir(path)
        time_saved = datetime.datetime.now()
        with open(os.path.join(path, "money.pkl"), "wb") as fb:
            pickle.dump(wallet, fb)
        with open(os.path.join(path, "score.pkl"), "wb") as fb:
            pickle.dump(score, fb)
        with open(os.path.join(path, "towns.pkl"), "wb") as fb:
            pickle.dump(towns, fb)
        with open(os.path.join(path, "services.pkl"), "wb") as fb:
            pickle.dump(services, fb)
        with open(os.path.join(path, "map.pkl"), "wb") as fb:
            pickle.dump(map_, fb)
        with open(os.path.join(path, "savetime.txt"), "w") as f:
            f.write(time_saved.strftime("%H:%M %d/%m/%y"))

    def load(self):
        path = os.path.join("saves", f"slot{self.save_slot}")
        if not os.path.exists(path):
            return None
        with open(os.path.join(path, "money.pkl"), "rb") as fb:
            wallet = pickle.load(fb)
        with open(os.path.join(path, "score.pkl"), "rb") as fb:
            score = pickle.load(fb)
        with open(os.path.join(path, "towns.pkl"), "rb") as fb:
            towns = pickle.load(fb)
        with open(os.path.join(path, "services.pkl"), "rb") as fb:
            services = pickle.load(fb)
        with open(os.path.join(path, "map.pkl"), "rb") as fb:
            map_ = pickle.load(fb)
        return wallet, score, towns, services, map_

    def recursive_delete(self, path):
        if os.path.isfile(path):
            os.remove(path)
            return
        if os.path.isdir(path):
            for item in os.listdir(path):
                self.recursive_delete(os.path.join(path, item))
            os.rmdir(path)

    def delete_save(self, slotnum):
        path = os.path.join("saves", f"slot{slotnum}")
        self.recursive_delete(path)
