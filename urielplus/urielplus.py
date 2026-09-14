from .urielplus_databases import URIELPlusDatabases
from .urielplus_imputation import URIELPlusImputation
from .urielplus_querying import URIELPlusQuerying

import logging
import os
import shutil

import numpy as np


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")


'''
URIEL+ library for integrating new and updated databases into URIEL and robust distance calculations.


Contributors: Aditya Khan (adityakhan@cs.toronto.edu), Mason Shipton (masonshipton25@gmail.com), York Hay Ng (york.ng@mail.utoronto.ca), David Anugraha (anugraha@cs.toronto.edu), Kaiyao Duan (davidduan04@gmail.com), Phuong H. Hoang (fiona.hoang@mail.utoronto.ca), Eric Khiu (erickhiu@umich.edu), Xiang Lu (jameslx@umich.edu), A. Seza Doğruöz (as.dogruoz@ugent.be), En-Shiun Annie Lee (annie.lee@ontariotechu.ca)


Last modified: September 12, 2026
'''


class URIELPlus(URIELPlusDatabases, URIELPlusImputation, URIELPlusQuerying):
    def __init__(self):
        """
            Initializes the URIEL+ class, setting up vector identifications of languages, and instantiating the classes
            needed for integrating databases, imputing missing values, and querying the knowledge base.

            Raises:
                FileNotFoundError: If a file is not found in the original_uriel directory.
                ValueError: If geographic feature matrices contain values other than -1.
                            If phylogeny, typological, or script feature matrices contain values other than -1, 0, and 1
        """
        self.files = ["family_features.npz", "features.npz", "geocoord_features.npz", "script_features.npz"]
        self.cur_dir = os.path.dirname(os.path.abspath(__file__))
        self.loaded_features  = []

        for file in self.files:
            file_path = os.path.join(self.cur_dir, "database", file)
            if not os.path.isfile(file_path):
                logging.info(f"{file_path} is missing in \"database\". Copying from \"original_uriel\"...")

                old_file_path = os.path.join(self.cur_dir, "database", "original_uriel", file)
                try:
                    shutil.copy(old_file_path, file_path)
                except FileNotFoundError:
                    raise FileNotFoundError(f"{file} not found in \"original_uriel\".")
            with np.load(file_path, allow_pickle=True) as l:
                self.loaded_features.append(dict(l))

        for index, matrix in enumerate(self.loaded_features):
            if index == 2:  # geography
                if not self._valid_geographic_data(matrix["data"]):
                    raise ValueError(
                        f"{self.files[index]}: geographic feature matrices may contain only -1 "
                        "or finite values from 0 to 1"
                    )
            else:  # phylogeny, typological, script
                if not self._valid_linguistic_data(matrix["data"]):
                    raise ValueError(
                        f"{self.files[index]}: linguistic feature matrices may contain only -1, 0, and 1"
                    )

        self.feats = [l["feats"] for l in self.loaded_features]
        self.langs = [l["langs"] for l in self.loaded_features]
        self.data = [l["data"] for l in self.loaded_features]
        self.sources = [l["sources"] for l in self.loaded_features]

        super().__init__(self.feats, self.langs, self.data, self.sources)

        self.databases = self
        self.imputation = self
        self.querying = self

        self._refresh_indexes()






    @staticmethod
    def _valid_linguistic_data(data):
        """
            Checks whether a linguistic (phylogeny, typological, or script) feature matrix contains only
            valid values.

            Args:
                data (np.ndarray): The feature data to validate.

            Returns:
                bool: True if every value in data is -1, 0, or 1.
        """
        values = np.asarray(data)
        if values.size == 0:
            return True
        return bool(np.all((values == -1) | (values == 0) | (values == 1)))


    @staticmethod
    def _valid_geographic_data(data):
        """
            Checks whether a geographic feature matrix contains only valid values.

            Args:
                data (np.ndarray): The feature data to validate.

            Returns:
                bool: True if every value in data is -1 or a finite value from 0 to 1.
        """
        values = np.asarray(data)
        if values.size == 0:
            return True
        return bool(np.all((values == -1) | (np.isfinite(values) & (values >= 0) & (values <= 1))))


    def _refresh_indexes(self, matrix_index=None):
        """
            Rebuilds name-to-position lookup tables for the given matrix, or all matrices if None.

            Args:
                matrix_index (int, optional): The index of the matrix to rebuild lookup tables for. If None,
                rebuilds lookup tables for all matrices.
        """
        indexes = range(len(self.feats)) if matrix_index is None else (matrix_index,)
        if matrix_index is None:
            self._feature_index = [None] * len(self.feats)
            self._language_index = [None] * len(self.langs)
            self._source_index = [None] * len(self.sources)

        for index in indexes:
            self._feature_index[index] = {str(v): p for p, v in enumerate(self.feats[index])}
            self._language_index[index] = {str(v): p for p, v in enumerate(self.langs[index])}
            self._source_index[index] = {str(v): p for p, v in enumerate(self.sources[index])}


    def _sync_loaded_features(self, matrix_index=None):
        """
            Keeps database loaded_features in sync with feats, langs, data, and sources for the provided matrix,
            or all four matrices if None.

            Args:
                matrix_index (int, optional): The index of the matrix to sync. If None, syncs all four matrices.
        """
        indexes = range(len(self.loaded_features)) if matrix_index is None else (matrix_index,)
        for index in indexes:
            matrix = self.loaded_features[index]
            matrix.update(
                feats=self.feats[index],
                langs=self.langs[index],
                data=self.data[index],
                sources=self.sources[index],
            )




    def get_loaded_features(self, l_name):
        """
            Returns the URIEL+ loaded features associated with the provided name, if the name is valid.

            Args:
                l_name (str): The name of the loaded features to return. Valid options are "phylogeny", "typological",
                "geography", or "script".

            Returns:
                np.ndarray: The corresponding loaded features as a NumPy array.

            Raises:
                KeyError: If the name is invalid.
           
        """
        l_map = {
            "phylogeny": self.loaded_features[0],
            "typological": self.loaded_features[1],
            "geography": self.loaded_features[2],
            "script": self.loaded_features[3],
        }
        if l_name in l_map:
            return l_map[l_name]
        raise KeyError(f"Unknown loaded features: {l_name}. Valid loaded features are {list(l_map.keys())}.")


    """
        The following three functions return loaded features representing phylogeny, typological, geography,
        and script vectors, respectively.

        Returns:
            np.ndarray: The corresponding loaded features as a NumPy array.
    """
    def get_phylogeny_loaded_features(self):
        """Returns the phylogeny loaded features."""
        return self.loaded_features[0]
   
    def get_typological_loaded_features(self):
        """Returns the typological loaded features."""
        return self.loaded_features[1]
   
    def get_geography_loaded_features(self):
        """Returns the geography loaded features."""
        return self.loaded_features[2]
    
    def get_script_loaded_features(self):
        """Returns the script loaded features."""
        return self.loaded_features[3]



    def set_loaded_features(self, l_name, file):
        """
            Updates the loaded features associated with the provided name by loading data from the provided file.

            Args:
                l_name (str): The name of the loaded_features to update. Valid options are "phylogeny", "typological",
                "geography", or "script".
                file (str): The file name to load the loaded features data from.

            Raises:
                KeyError: If the name is invalid.
                FileNotFoundError: If the file is missing.
                ValueError: If the data fails validation.
        """
        l_map = {
            "phylogeny": 0,
            "typological": 1,
            "geography": 2,
            "script": 3,
        }
        if l_name not in l_map:
            raise KeyError(f"Unknown loaded features: {l_name}. Valid loaded features are {list(l_map.keys())}.")

        l_idx = l_map[l_name]
        file_path = os.path.join(self.cur_dir, "database", file)
        try:
            with np.load(file_path, allow_pickle=True) as l:
                matrix = dict(l)
        except FileNotFoundError:
            raise FileNotFoundError(f"File not found: {file_path}. Failed to update {l_name} loaded features.")

        if l_idx == 2:
            if not self._valid_geographic_data(matrix["data"]):
                raise ValueError("geographic feature matrices may contain only -1 or finite values from 0 to 1")
        elif not self._valid_linguistic_data(matrix["data"]):
            raise ValueError("linguistic feature matrices may contain only -1, 0, and 1")

        self.loaded_features[l_idx] = matrix
        self.feats[l_idx] = matrix["feats"]
        self.langs[l_idx] = matrix["langs"]
        self.data[l_idx] = matrix["data"]
        self.sources[l_idx] = matrix["sources"]
        self.files[l_idx] = file
        logging.info(f"{l_name} loaded features updated successfully from {file}.")

        self._refresh_indexes(l_idx)


    """
        The following three functions updates loaded features representing phylogeny, typological, geography,
        and script vectors, respectively.

        Args:
            file (str): The file name to load the loaded features data from.
    """    
    def set_phylogeny_loaded_features(self, file):
        """Updates the phylogeny loaded features."""
        self.set_loaded_features("phylogeny", file)

    def set_typological_loaded_features(self, file):
        """Updates the typological loaded features."""
        self.set_loaded_features("typological", file)

    def set_geography_loaded_features(self, file):
        """Updates the geography loaded features."""
        self.set_loaded_features("geography", file)

    def set_script_loaded_features(self, file):
        """Updates the script loaded features."""
        self.set_loaded_features("script", file)
   




    def get_arrays(self, l_name):
        """
            Returns the arrays within the URIEL+ loaded features associated with the provided name, if the name is
            valid.

            Args:
                l_name (str): The name of the loaded features to return. Valid options are "phylogeny", "typological",
                "geography", or "script".

            Returns:
                tuple: The arrays within the corresponding loaded features as NumPy arrays.
        """
        loaded_features = self.get_loaded_features(l_name)
        return loaded_features["feats"], loaded_features["data"], loaded_features["langs"], loaded_features["sources"]


    """
        The following three functions return all the arrays within loaded features representing
        phylogeny, typological, geography, and script vectors, respectively.

        Returns:
            tuple: The arrays within the corresponding loaded features as NumPy arrays.
    """
    def get_phylogeny_arrays(self):
        """Returns the phylogeny arrays."""
        return self.get_arrays("phylogeny")
   
    def get_typological_arrays(self):
        """Returns the typological arrays."""
        return self.get_arrays("typological")
   
    def get_geography_arrays(self):
        """Returns the geography arrays."""
        return self.get_arrays("geography")
    
    def get_script_arrays(self):
        """Returns the script arrays."""
        return self.get_arrays("script")




    """
        The following four functions return all the arrays from all loaded features representing
        features, languages, feature data, and sources, respectively.

        Returns:
            list: A list of NumPy arrays containing the corresponding arrays from each loaded features.
    """
    def get_features_arrays(self):
        """Returns the features arrays."""
        return self.feats
   
    def get_languages_arrays(self):
        """Returns the languages arrays."""
        return self.langs
   
    def get_data_arrays(self):
        """Returns the data arrays."""
        return self.data
   
    def get_sources_arrays(self):
        """Returns the sources arrays."""
        return self.sources




    """
        The following functions return the array corresponding with a specific loaded features
        and one of either features, languages, data, or sources arrays.

        Returns:
            np.ndarray: A NumPy array of either the features, languages, data, or sources of a specific loaded
            features.
    """
    def get_phylogeny_features_array(self):
        """Returns the features array of the phylogeny loaded features."""
        return self.feats[0]
   
    def get_typological_features_array(self):
        """Returns the features array of the typological loaded features."""
        return self.feats[1]
   
    def get_geography_features_array(self):
        """Returns the features array of the geography loaded features."""
        return self.feats[2]
    
    def get_script_features_array(self):
        """Returns the features array of the script loaded features."""
        return self.feats[3]
   
    def get_phylogeny_languages_array(self):
        """Returns the languages array of the phylogeny loaded features."""
        return self.langs[0]
   
    def get_typological_languages_array(self):
        """Returns the languages array of the typological loaded features."""
        return self.langs[1]
   
    def get_geography_languages_array(self):
        """Returns the languages array of the geography loaded features."""
        return self.langs[2]
    
    def get_script_languages_array(self):
        """Returns the languages array of the script loaded features."""
        return self.langs[3]
   
    def get_phylogeny_data_array(self):
        """Returns the data array of the phylogeny loaded features."""
        return self.data[0]
   
    def get_typological_data_array(self):
        """Returns the data array of the typological loaded features."""
        return self.data[1]
   
    def get_geography_data_array(self):
        """Returns the data array of the geography loaded features."""
        return self.data[2]
    
    def get_script_data_array(self):
        """Returns the data array of the script loaded features."""
        return self.data[3]
   
    def get_phylogeny_sources_array(self):
        """Returns the sources array of the phylogeny loaded features."""
        return self.sources[0]
   
    def get_typological_sources_array(self):
        """Returns the sources array of the typological loaded features."""
        return self.sources[1]
   
    def get_geography_sources_array(self):
        """Returns the sources array of the geography loaded features."""
        return self.sources[2]
    
    def get_script_sources_array(self):
        """Returns the sources array of the script loaded features."""
        return self.sources[3]




    def reset(self):
        """Restores URIEL+ to the released database, discarding in-memory changes."""
        self.__init__()
