import datetime
import os
import pickle


class SaveManager():
    def __init__(self):
        self.save_slot = None
        self.data_file_ids = []
        if not os.path.exists("saves"):
            os.mkdir("saves")

    def get_save_time(self, slotnum):
        path = os.path.join("saves", f"slot{slotnum}")
        save_time = "new"
        if os.path.exists(os.path.join(path, "savetime.txt")):
            with open(os.path.join(path, "savetime.txt"), "r") as f:
                save_time = f.read()
        return save_time.strip("\n")

    def get_dir(self):
        return os.path.join("saves", f"slot{self.save_slot}")

    def set_save_slot(self, slot):
        self.save_slot = slot

    def save_data(self, file_id, data, allow_overwrite=False, append_mode=False):
        """
        For saving data while the game is running (as opposed to pickling all objects and then exiting the game)
        This should be used if data generated is likely to put constraints of memory, and doesn't need to be
        accessed to often.
        Access data with load_data(file_id)
        Do not manually save data to the save directory, as all data the save manager isn't aware of will be deleted
        as part of the cleanup process before saving.
        :param allow_overwrite: If True, overwrites existing data with the same file_id
        :param file_id: An identifier for the data (likely will be used as the filename)
        :param data: The data as a string. byte data is not supported.
        :return: None
        """
        path = os.path.join("saves", f"slot{self.save_slot}")
        if not os.path.exists(path):
            os.mkdir(path)
        path = os.path.join("saves", f"slot{self.save_slot}", file_id)
        if not path in self.data_file_ids:
            self.data_file_ids.append(path)
        elif not allow_overwrite and not append_mode:
            raise FileExistsError
        if append_mode:
            with open(path, "a", encoding='utf-8') as f:
                f.write(data)
        else:
            with open(path, "w", encoding='utf-8') as f:
                f.write(data)

    def load_data(self, file_identifier):
        path = os.path.join("saves", f"slot{self.save_slot}", file_identifier)
        if not os.path.exists(path):
            return
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()


    def save(self, wallet, score, towns, services, map_):
        self.delete_save(self.save_slot, keep_data=True)  # delete any old save data
        path = os.path.join("saves", f"slot{self.save_slot}")
        if not os.path.exists(path):
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
        with open(os.path.join(path, "saved_data_list.txt"), "w") as f:
            f.writelines(self.data_file_ids)

    def load(self):
        """ To load, the savetime.txt file must exist. This is so that we know the save actually exists,
            as data (e.g. from the wallet) could be saved without the game having a valid full save."""
        path = os.path.join("saves", f"slot{self.save_slot}")
        if not os.path.exists(os.path.join(path, "savetime.txt")):
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
        with open(os.path.join(path, "saved_data_list.txt"), "r") as f:
            self.data_file_ids = f.readlines()
        return wallet, score, towns, services, map_

    def recursive_delete(self, path, keep_data=False):
        if os.path.isfile(path):
            if keep_data and path in self.data_file_ids:
                return
            os.remove(path)
            return
        if os.path.isdir(path):
            for item in os.listdir(path):
                self.recursive_delete(os.path.join(path, item), keep_data=keep_data)
            try:
                os.rmdir(path)
            except OSError:
                pass  # OSError: [Errno 39] Directory not empty: 'saves/slot1'

    def delete_save(self, slotnum, keep_data=False):
        path = os.path.join("saves", f"slot{slotnum}")
        self.recursive_delete(path, keep_data=keep_data)
