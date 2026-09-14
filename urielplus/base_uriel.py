import logging
import os

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

            include_lineage_in_eval (bool): Whether values filled in via parent language (lineage) data during
            imputation are included when evaluating imputation quality.
            Defaults to False.

            restrict_ewave_to_own_languages (bool): Whether eWAVE-exclusive features are restricted to
            eWAVE's own languages as well as "stan1293" (Standard English). When True, these features are never imputed, aggregated, 
            or included in calculations/vectors for any other language; existing cells are forced to -1 (missing) in place, in memory
            and (if caching is enabled) on disk.
            Defaults to True.
            NOTE: This masking is applied in place and is not reversible by toggling the attribute back
            to False unless URIEL+ is reset.

            codes (str): Whether to identify languages with Iso 639-3 codes (Iso) or Glottocodes (Glotto).
            Defaults to "Iso".
            NOTE: Once set to "Glotto", codes cannot be changed back to "Iso" unless URIEL+ is reset.
    """
    cache = False
    aggregation = 'U'
    fill_with_base_lang = True
    distance_metric = "angular"
    include_lineage_in_eval = False
    codes = 'Iso'
    restrict_ewave_to_own_languages = True


    def __init__(self, feats, langs, data, sources, codes=None):
        #Files of language phylogenetic, typological, geographical, and script vectors, respectively.
        self.files = ["family_features.npz", "features.npz", "geocoord_features.npz", "script_features.npz"]

        self.cur_dir = os.path.dirname(os.path.abspath(__file__))

        self.feats = feats
        self.langs = langs
        self.data = data
        self.sources = sources

        self.lineage_imputed_indices = set()

        self.ewave_scope_langs = None
        self.ewave_scope_feats = None

        if codes is not None:
            if codes not in ("Iso", "Glotto"):
                raise ValueError(f"Invalid codes: {codes}. Valid codes are ('Iso', 'Glotto').")
            self.codes = codes
        else:
            if all(self.is_iso_code(lang) for langs in self.langs for lang in langs):
                self.codes = 'Iso'
            else:
                self.codes = 'Glotto'




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
               
            Raises:
                ValueError: If the provided cache value is not a valid boolean value (True or False).
           
        """
        if not isinstance(cache, bool):
            raise ValueError(f"Invalid boolean value: {cache}. Valid boolean values are True and False.")
        self.cache = cache


       
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
               
            Raises:
                ValueError: If the provided strategy value is invalid.
           
        """
        aggregations = ['U', 'A']
        if aggregation not in aggregations:
            raise ValueError(f"Invalid aggregation: {aggregation}. Valid aggregations are {aggregations}.")
        self.aggregation = aggregation


       
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
               
            Raises:
                ValueError: If the provided fill_with_base_lang value is not a valid boolean value (True or False).
           
        """
        if not isinstance(fill_with_base_lang, bool):
            raise ValueError(f"Invalid boolean value: {fill_with_base_lang}. Valid boolean values are True and False.")
        self.fill_with_base_lang = fill_with_base_lang


   
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
                distance_metric (str): The distance metric to use for distance calculations.
               
            Raises:
                ValueError: If the provided distance metric value is invalid.
           
        """
        distance_metrics = ["angular", "cosine"]
        if distance_metric not in distance_metrics:
            raise ValueError(f"Invalid distance metric: {distance_metric}. Valid distance metrics are {distance_metrics}.")
        self.distance_metric = distance_metric



    def get_lineage_imputed_indices(self):
        """
            Returns the set of language indices whose values were filled in using parent language (lineage)
            data during the most recent imputation run.

            Returns:
                set: The indices of languages filled in via lineage-based imputation.
        """
        return self.lineage_imputed_indices


    def set_lineage_imputed_indices(self, lineage_imputed_indices):
        """
            Sets the set of language indices whose values were filled in using parent language (lineage) data.

            Args:
                lineage_imputed_indices (set): The indices of languages filled in via lineage-based imputation.

            Raises:
                ValueError: If the provided value is not a set.
        """
        if not isinstance(lineage_imputed_indices, set):
            raise ValueError(f"Invalid set value: {lineage_imputed_indices}. Must be a set.")
        self.lineage_imputed_indices = lineage_imputed_indices



    def get_include_lineage_in_eval(self):
        """
            Returns whether values filled in via parent language (lineage) data are included when
            evaluating imputation quality.

            Returns:
                bool: True if lineage-imputed values are included in evaluation, False otherwise.
        """
        return self.include_lineage_in_eval


    def set_include_lineage_in_eval(self, include_lineage_in_eval):
        """
            Sets whether values filled in via parent language (lineage) data are included when evaluating
            imputation quality.

            Args:
                include_lineage_in_eval (bool): True to include lineage-imputed values in evaluation, False
                otherwise.

            Raises:
                ValueError: If the provided value is not a valid boolean value (True or False).
        """
        if not isinstance(include_lineage_in_eval, bool):
            raise ValueError(f"Invalid boolean value: {include_lineage_in_eval}. Valid boolean values are True and False.")
        self.include_lineage_in_eval = include_lineage_in_eval



    def get_restrict_ewave_to_own_languages(self):
        """
            Returns whether eWAVE-exclusive features are restricted to eWAVE's own languages (plus
            "stan1293").

            Returns:
                bool: True if eWAVE features are restricted to eWAVE's own languages, False otherwise.
        """
        return self.restrict_ewave_to_own_languages


    def set_restrict_ewave_to_own_languages(self, restrict_ewave_to_own_languages):
        """
            Sets whether eWAVE-exclusive features are restricted to eWAVE's own languages (plus
            "stan1293").

            Args:
                restrict_ewave_to_own_languages (bool): True to restrict eWAVE features to eWAVE's own
                languages, False otherwise.

            Raises:
                ValueError: If the provided value is not a valid boolean value (True or False).

            NOTE: Setting this to True causes any eWAVE-exclusive feature values for other languages to
            be immediately and irreversibly forced to -1 (missing) the next time that data is accessed
            or computed on. Setting it back to False afterward does not restore those values.
        """
        if not isinstance(restrict_ewave_to_own_languages, bool):
            raise ValueError(f"Invalid boolean value: {restrict_ewave_to_own_languages}. Valid boolean values are True and False.")
        self.restrict_ewave_to_own_languages = restrict_ewave_to_own_languages



    def _apply_ewave_restriction_if_enabled(self, data, langs, feats, idx=1):
        """
            If "restrict_ewave_to_own_languages" is True, forces eWAVE-exclusive features back to -1
            (missing) in place, for every language outside of eWAVE's own scope (its own languages
            plus "stan1293"). No-op if the flag is False, if idx != 1, or if eWAVE has no resolvable
            scope (e.g. not yet integrated).
 
            Args:
                data (np.ndarray): A (languages x features) or (languages x features x sources) array
                to restrict in place; any trailing axis (e.g. source) is preserved and fully cleared
                for restricted cells.
                langs (array-like): Language codes aligned with axis 0 of `data`.
                feats (array-like): Feature names aligned with axis 1 of `data`.
                idx (int): The index of the data array being restricted (only idx == 1 is relevant).
 
            Returns:
                np.ndarray: The same array, with restricted cells forced to -1.
        """
        if not self.restrict_ewave_to_own_languages or idx != 1:
            return data

        if self.ewave_scope_langs is None or self.ewave_scope_feats is None:
            csv_path = os.path.join(self.cur_dir, "database", "urielplus_csvs", "english_dialect_data.csv")
            df = pd.read_csv(csv_path)
    
            self.ewave_scope_langs = set(df["language_id"].astype(str)) | {"stan1293"}
            self.ewave_scope_feats = set(df.columns[1:])
 
        feat_mask = np.isin(np.asarray(feats, dtype=str), list(self.ewave_scope_feats))
        if not feat_mask.any():
            return data
 
        lang_mask = ~np.isin(np.asarray(langs, dtype=str), list(self.ewave_scope_langs))
        if not lang_mask.any():
            return data
 
        data[np.ix_(lang_mask, feat_mask)] = -1.0
        return data




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
        return self.codes



   
    def set_glottocodes(self):
        """
            Sets the language codes in URIEL+ to Glottocodes.

            This function reads a mapping CSV file and applies the mappings to all language phylogenetic,
            typological, geographical, and script vectors files, saving the updated data back to disk if
            caching is enabled. Any language with no corresponding Glottocode is dropped.

            Raises:
                ValueError: If already using Glottocodes, or if the mapping table contains a duplicate ISO code.
        """
        if self.codes == "Glotto":
            raise ValueError("Already using Glottocodes.")
    
        logging.info("Converting ISO 639-3 codes to Glottocodes....")

        csv_path = os.path.join(self.cur_dir, "database", "urielplus_csvs", "uriel_glottocode_map.csv")
        # keep_default_na=False preserves the literal ISO code "nan" (Min Nan Chinese) instead of letting
        # pandas silently convert it to a real NaN during parsing.
        map_df = pd.read_csv(csv_path, dtype=str, keep_default_na=False, na_filter=False)
        map_df["iso_code"] = map_df["iso_code"].str.strip()
        map_df["glottocode"] = map_df["glottocode"].str.strip()
        map_df = map_df[(map_df["iso_code"] != "") & (map_df["glottocode"] != "")]

        if map_df["iso_code"].duplicated().any():
            raise ValueError("uriel_glottocode_map.csv contains a duplicate iso_code entry.")

        mapping = dict(zip(map_df["iso_code"], map_df["glottocode"]))

        for i, file in enumerate(self.files):
            mapped = [mapping.get(str(lang)) for lang in self.langs[i]]
            keep = np.array([value is not None for value in mapped])

            self.langs[i] = np.array([value for value in mapped if value is not None])
            self.data[i] = self.data[i][keep]

            if self.cache:
                np.savez(os.path.join(self.cur_dir, "database", file),
                        feats=self.feats[i], data=self.data[i], langs=self.langs[i], sources=self.sources[i])

        logging.info("Conversion to Glottocodes complete.")

        self.codes = "Glotto"

        if hasattr(self, "_sync_loaded_features"):
            self._sync_loaded_features()
        if hasattr(self, "_refresh_indexes"):
            self._refresh_indexes()






    def get_dialects(self):
        """
            Returns a dictionary of dialects, with keys being indices of base languages in self.langs[1],
            and values being lists of the dialect language codes.

            This function dynamically identifies dialects for languages based on the current language
            representation (ISO 639-3 or Glottocode) by reading from a CSV file containing the mappings.

            Returns:
                dict: A dictionary where keys are indices of base languages, and values are lists of dialect language codes.

            Raises:
                ValueError: If the languages in URIEL+ are not all in either ISO 639-3 or Glottocode representation.
        """
        if self.codes not in ("Glotto", "Iso"):
            raise ValueError(
                "Cannot retrieve dialects if languages in URIEL+ are not all of either ISO 639-3 or Glottocode language representation."
            )
        
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