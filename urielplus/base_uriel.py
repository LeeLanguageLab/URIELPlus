import logging
import os
import sys


import numpy as np
import pandas as pd


class BaseURIEL:
    """
        Configuration options:
            cache (bool): Whether to cache distance languages and changes to databases.
            Defaults to False.


            aggregation (str): Whether to perform a union ('U') or average ('A') operation on data for aggregation and distance
            calculations.
            Defaults to 'U'.


            fill_with_base_lang (bool): Whether to fill missing values during aggregation using parent language data.
            Defaults to False.


            distance_metric (str): The distance metric to use for distance calculations ("angular" or "cosine").
            Defaults to "angular".


            codes (str): Whether to identify languages with Iso 639-3 codes (Iso) or Glottocodes (Glotto).
            Defaults to "Iso".
            NOTE: Once set to "Glotto", codes cannot be changed back to "Iso" unless URIEL+ is reset.
    """
    cache = False
    aggregation = 'U'
    fill_with_base_lang = True
    distance_metric = "angular"
    codes = 'Iso'


    def __init__(self, feats, langs, data, sources):
        #Files of language phylogenetic, typological, geographical, and scriptural vectors, respectively.
        self.files = ["family_features.npz", "features.npz", "geocoord_features.npz", "script_features.npz"]


        self.cur_dir = os.path.dirname(os.path.abspath(__file__))
        self.logger = logging.getLogger(self.__class__.__name__)


        self.feats = feats
        self.langs = langs
        self.data = data
        self.sources = sources




    def get_cache(self):
        """
            Returns whether to cache distance languages and changes to databases.


            Returns:
                bool: True if caching is enabled, False otherwise.
        """
        return self.cache


    def set_cache(self, cache):
        """
            Sets whether to cache distance languages and changes to databases.


            Args:
                cache (bool): True to enable caching, False otherwise.
               
            Logging:
                Error: Logs an error if the provided cache value is not a valid boolean value (True or False).
           
        """
        if isinstance(cache, bool):
            self.cache = cache
        else:
            logging.error(f"Invalid boolean value: {cache}. Valid boolean values are True and False.")
            sys.exit(1)


       
    def get_aggregation(self):
        """
            Returns whether to perform a union ('U') or average ('A') operation on data for aggregation and distance calculations.


            Returns:
                str: 'U' if aggregation is union, 'A' if aggregation is average.
        """
        return self.aggregation
   
    def set_aggregation(self, aggregation):
        """
            Sets whether to perform a union ('U') or average ('A') operation on data for aggregation and distance calculations.


            Args:
                aggregation (str): Whether to perform a union ('U') or average ('A') operation on data for aggregation and distance calculations.
               
            Logging:
                Error: Logs an error if the provided strategy value is invalid.
           
        """
        aggregations = ['U', 'A']
        if aggregation in aggregations:
            self.aggregation = aggregation
        else:
            logging.error(f"Invalid aggregation: {aggregation}. Valid aggregations are {aggregations}.")
            sys.exit(1)


       
    def get_fill_with_base_lang(self):
        """
            Returns whether to fill missing values during aggregation using parent language data.


            Returns:
                bool: True if filling missing values with parent language data is enabled, False otherwise.
        """
        return self.fill_with_base_lang


    def set_fill_with_base_lang(self, fill_with_base_lang):
        """
            Sets whether to fill missing values during aggregation using parent language data.


            Args:
                fill_with_base_lang (bool): True to enable filling with base language, False otherwise.
               
            Logging:
                Error: Logs an error if the provided fill_with_base_lang value is not a valid boolean value (True or False).
           
        """
        if isinstance(fill_with_base_lang, bool):
            self.fill_with_base_lang = fill_with_base_lang
            self.dialects = self.get_dialects()
        else:
            logging.error(f"Invalid boolean value: {fill_with_base_lang}. Valid boolean values are True and False.")
            sys.exit(1)  


   
    def get_distance_metric(self):
        """
            Returns the distance metric to use for distance calculations.


            Returns:
                str: The distance metric to use for distance calculations.
        """
        return self.distance_metric
   
    def set_distance_metric(self, distance_metric):
        """
            Sets the distance metric to use for distance calculations.


            Args:
                distance_metric (bool): The distance metric to use for distance calculations.
               
            Logging:
                Error: Logs an error if the provided distance metric value is invalid.
           
        """
        distance_metrics = ["angular", "cosine"]
        if distance_metric in distance_metrics:
            self.distance_metric = distance_metric
        else:
            logging.error(f"Invalid distance metric: {distance_metric}. Valid distance metrics are {distance_metrics}.")
            sys.exit(1)




    def is_iso_code(self, lang):
        """
            Checks if a provided language code is in ISO 639-3 code format.


            Args:
                lang (str): The language code to check.


            Returns:
                bool: True if the code is in ISO 639-3 code format (3 alphabetic characters); otherwise, False.
        """
        return (len(lang) == 3 and lang.isalpha())
   
    def is_glottocode(self, lang):
        """
            Checks if a provided language code is in Glottocode format.


            Args:
                lang (str): The language code to check.


            Returns:
                bool: True if the code is in Glottocode format (4 alphabetic characters followed by 4 numeric characters); otherwise, False.
        """
        return (len(lang) == 8 and lang[:4].isalpha() and lang[4:].isnumeric())


    def get_codes(self):
        """
        Returns whether URIEL+ identifies languages with Iso 639-3 codes (Iso) or Glottocodes (Glotto).


        Returns:
            str: 'Iso' if codes is Iso 639-3 codes, 'Glotto' if codes is Glottocodes.
        """
        if all(self.is_iso_code(lang) for langs in self.langs for lang in langs):
            return 'Iso'
        else:
            return 'Glotto'
        


   
    def set_glottocodes(self):
        """
            Sets the language codes in URIEL+ to Glottocodes.


            This function reads a mapping CSV file and applies the mappings to all language phylogenetic, typological,
            and geographical vectors files, saving the updated data back to disk if caching is enabled.
        """
        if self.codes == "Glotto":
            logging.error("Already using Glottocodes.")
            sys.exit(1)

        

        logging.info("Converting ISO 639-3 codes to Glottocodes....")


        csv_path = os.path.join(self.cur_dir, "database", "urielplus_csvs", "uriel_glottocode_map.csv")
        map_df = pd.read_csv(csv_path)


        #Needed to perserve language Min Nan Chinese with Iso 639-3 code "nan"
        map_df["code"] = map_df["code"].astype(str)


        for i, file in enumerate(self.files):
            langs_df = pd.DataFrame(self.langs[i], columns=["code"])
            merged_df = pd.merge(langs_df, map_df, on="code", how="inner")
            merged_df = merged_df.dropna()
            merged_df = merged_df.drop(columns=['X', "code"])
            merged_np = merged_df.to_numpy()
            na_indices = langs_df.index.difference(merged_df.index)
            data_cleaned = np.delete(self.data[i], na_indices, axis=0)
            self.langs[i] = merged_np
            self.data[i] = data_cleaned
            self.langs[i] = np.array([l[0] for l in self.langs[i]])


            if self.cache:
                np.savez(os.path.join(self.cur_dir, "database", file),
                         feats=self.feats[i], data=self.data[i], langs=self.langs[i], sources=self.sources[i])
               
        logging.info("Conversion to Glottocodes complete.")


        #Sets codes to Glotto (Glottocodes).
        self.codes = "Glotto"






    def get_dialects(self):
        """
        Returns a dictionary of dialects, with keys being indices of base languages in self.langs[1],
        and values being lists of the dialect language codes.

        This function dynamically identifies dialects for languages based on the current language
        representation (ISO 639-3 or Glottocode) by reading from a CSV file containing the mappings.

        Returns:
            dict: A dictionary where keys are indices of base languages, and values are lists of dialect language codes.

        Logging:
            Error: If the languages in URIEL+ are not all in either ISO 639-3 or Glottocode representation.
        """
        if not self.codes == "Glotto" and not self.codes == "Iso" :
            logging.error(
                "Cannot retrieve dialects if languages in URIEL+ are not all of either ISO 639-3 or Glottocode language representation."
            )
            sys.exit(1)
        
        code = "Glot" if self.codes == "Glotto" else "Iso"

        csv_path = os.path.join(self.cur_dir, "database", "urielplus_csvs", "dialects.csv")
        dialects_df = pd.read_csv(csv_path)

        dialects_by_language = {}

        for index, language_code in enumerate(self.langs[1]):
            row = dialects_df[dialects_df["Language " + code] == language_code]
            if not row.empty:
                dialects = row["Dialect(s) " + code].values[0]
                if pd.notna(dialects):
                    dialects_by_language[index] = dialects.split(", ")

        return dialects_by_language