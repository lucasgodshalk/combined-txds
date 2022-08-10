import tempfile
import os
import hashlib
import dill

class LagrangePickler:
    def __init__(self) -> None:
        dill.settings['recurse'] = True

        self.pickle_dir = os.path.join(tempfile.gettempdir(), "combined-txds-lagrange-pickler")
        if not os.path.exists(self.pickle_dir):
            os.makedirs(self.pickle_dir)

    def _get_pickle_file(self, lagrange_key):
        sha1 = hashlib.sha1()
        sha1.update(lagrange_key.encode('utf8'))
        hash = sha1.hexdigest()
        hash = hash[:10]
        return os.path.join(self.pickle_dir, f"{hash}.p")

    def has_pickle(self, lagrange_key):
        pickle_file = self._get_pickle_file(lagrange_key)
        return os.path.isfile(pickle_file)

    def try_unpickle(self, lagrange_key):
        if not self.has_pickle(lagrange_key):
            raise Exception("No pickle file exists.")
        
        pickle_filepath = self._get_pickle_file(lagrange_key)

        derivatives = dill.load(open(pickle_filepath, "rb"))

        return derivatives

    def try_pickle(self, lagrange_key, derivatives):
        pickle_file = self._get_pickle_file(lagrange_key)
        dill.dump(derivatives, open(pickle_file, "wb" ) )