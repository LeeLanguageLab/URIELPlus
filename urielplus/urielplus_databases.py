import json
import logging
import math
import os
import re

import numpy as np
import pandas as pd

from .base_uriel import BaseURIEL


class URIELPlusDatabases(BaseURIEL):
    def _get_new_features(self, feats, columns):
        """
            Identifies and returns the new features to URIEL+.

            Args:
                feats (np.ndarray): The current features array.
                columns (list): The list of all features.

            Returns:
                list: A list of new features to URIEL+.
        """
        featlist = feats.tolist()
        return [feat for feat in columns if feat not in featlist]


    def _get_new_languages(self, langs, data, column):
        """
            Identifies and returns the new languages to URIEL+.

            Args:
                langs (np.ndarray): The current languages array.
                data (pd.DataFrame): The new dataset containing all languages.
                column (str): The column in the dataset that contains language codes.

            Returns:
                list: A list of new languages to URIEL+.
        """
        langlist = langs.tolist()
        return [lang for lang in data[column] if lang not in langlist]


    def _set_new_data_dimensions(self, data, new_feats, new_langs, new_sources):
        """
            Expands the URIEL+ data array to accommodate new features, languages, and sources, initializing new values
            to -1.0.

            Args:
                data (np.ndarray): The current data array.
                new_feats (list): List of new features to add.
                new_langs (list): List of new languages to add.
                new_sources (list): List of new sources to add.

            Returns:
                np.ndarray: The expanded data array with new dimensions.
        """
        new_data = np.full(
            (data.shape[0] + len(new_langs), data.shape[1] + len(new_feats), data.shape[2] + len(new_sources)),
            -1.0
        )
        new_data[:data.shape[0], :data.shape[1], :data.shape[2]] = data
        return new_data


    def is_database_incorporated(self, database):
        """
            Checks if a specific database has already been integrated into URIEL+.

            Args:
                database (str): The name of the database to check.

            Returns:
                bool: True if the database is already integrated.
        """
        all_sources = [str(s).upper() for s in self.sources[1]]
        return database.upper() in all_sources



    @staticmethod
    def _lineage_parts(value):
        """
            Splits a raw lineage string into its trimmed path components, root to leaf.

            Args:
                value: The raw lineage value from lang_fam_geo.csv (may be NaN/None/"<NA>").

            Returns:
                tuple: The non-empty, stripped lineage components, in root-to-leaf order.
        """
        if value is None or (isinstance(value, float) and math.isnan(value)):
            return ()
        return tuple(part.strip() for part in str(value).split(",") if part.strip() and part.strip() != "<NA>")


    def _selected_family_metadata(self):
        """
            Loads lang_fam_geo.csv and, for languages with more than one row, keeps only the row with the
            deepest (most specific) lineage.

            Returns:
                tuple: (full DataFrame with every CSV row, DataFrame indexed by language_id holding
                only the selected row per language).
        """
        csv_path = os.path.join(self.cur_dir, "database", "urielplus_csvs", "lang_fam_geo.csv")
        frame = pd.read_csv(csv_path, dtype={"language_id": "string", "language_name": "string", "lineage": "string"})
        frame.columns = frame.columns.str.strip('"')
        frame["language_id"] = frame["language_id"].str.strip()

        frame["_depth"] = frame["lineage"].fillna("").map(
            lambda value: len([part for part in str(value).split(",") if part.strip()])
        )
        selected = (
            frame.sort_values(["language_id", "_depth"], ascending=[True, False], kind="stable")
            .drop_duplicates("language_id", keep="first")
            .set_index("language_id", drop=False)
        )
        return frame, selected


    def _calculate_phylogeny_vectors(self):
        """
            Rebuilds the full family-features matrix from lang_fam_geo.csv. Every lineage prefix across
            every language becomes its own path-qualified feature (F_<root> > <child> > ... > <node>).
            The source axis is labelled "GLOTTOLOG_DERIVED".
            
            If caching is enabled, overwrites the "family_features.npz" file.

            Raises:
                ValueError: If the family source does not yield 8,887 path-qualified nodes or 8,582 direct parent relations.
        """
        frame, selected = self._selected_family_metadata()

        paths = set()
        for lineage in frame["lineage"]:
            parts = self._lineage_parts(lineage)
            paths.update(parts[:depth] for depth in range(1, len(parts) + 1))
        ordered_paths = sorted(paths, key=lambda path: (len(path), " > ".join(path)))

        if len(ordered_paths) != 8887:
            raise ValueError(f"the family source must yield 8,887 path-qualified nodes, found {len(ordered_paths)}")
        edge_count = sum(len(path) > 1 for path in ordered_paths)
        if edge_count != 8582:
            raise ValueError(f"the family source must yield 8,582 direct parent relations, found {edge_count}")

        features = np.asarray(["F_" + " > ".join(path) for path in ordered_paths], dtype=str)
        path_index = {path: idx for idx, path in enumerate(ordered_paths)}

        languages = np.asarray(self.langs[1], dtype=str)
        data = np.full((len(languages), len(features), 1), -1, dtype=np.int8)

        for row, language in enumerate(languages):
            if language not in selected.index:
                continue
            parts = self._lineage_parts(selected.at[language, "lineage"])
            if not parts:
                continue
            data[row, :, 0] = 0
            indices = [path_index[parts[:depth]] for depth in range(1, len(parts) + 1)]
            data[row, indices, 0] = 1

        self.feats[0] = features
        self.langs[0] = languages
        self.data[0] = data
        self.sources[0] = np.asarray(["GLOTTOLOG_DERIVED"])

        if self.cache:
            np.savez(os.path.join(self.cur_dir, "database", self.files[0]), feats=self.feats[0], data=self.data[0], langs=self.langs[0], sources=self.sources[0])

        self._sync_loaded_features(0)
        self._refresh_indexes(0)


    def _calculate_geocoord_vectors(self):
        """
            Rebuilds the full geography-features matrix from scratch using the great-circle distance
            (in km, via the Haversine calculation), normalized by Earth's antipodal distance
            (π x 6371.0 km). Every language gets a distance to a fixed set of reference
            anchors, which are read from the "original_uriel/geocoord_features.npz".
            Feature names use the "G_DISTANCE_TO_LATITUDE_<lat>_LONGITUDE_<lon>" format and the source
            axis is labelled "GLOTTOLOG_DERIVED".

            If caching is enabled, overwrites the `geocoord_features.npz` file.
        """
        frame, selected = self._selected_family_metadata()

        with np.load(os.path.join(self.cur_dir, "database", "original_uriel", "geocoord_features.npz"),
                     allow_pickle=False) as archive:
            original_features = archive["feats"].astype(str)

        anchors = []
        features = []
        for feat in original_features:
            match = re.fullmatch(r"GC_(-?\d+(?:\.\d+)?)_(-?\d+(?:\.\d+)?)", feat)
            if match is None:
                raise ValueError(f"invalid original geographic reference feature: {feat!r}")
            latitude, longitude = match.groups()
            anchors.append((float(latitude), float(longitude)))
            features.append(f"G_DISTANCE_TO_LATITUDE_{latitude}_LONGITUDE_{longitude}")

        MAX_DIST = math.pi * 6371.000  # Earth's antipodal distance, ~20015.1 km

        # Function provided by Dr. Patrick Littell
        def getGreatCircleDistance(lat1, lon1, lat2, lon2):
            ''' Get the great-circle distance between two coordinates
                using the Haversine calculation '''

            f1 = math.radians(lat1)
            f2 = math.radians(lat2)
            df = math.radians(lat2-lat1)
            dl = math.radians(lon2-lon1)

            a = (math.sin(df/2) ** 2 +
                    math.cos(f1) * math.cos(f2) *
                    math.sin(dl/2) ** 2)
            c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
            return 6371.000 * c

        languages = np.asarray(self.langs[1], dtype=str)
        data = np.full((len(languages), len(features), 1), -1.0, dtype=np.float32)

        for row, language in enumerate(languages):
            if language not in selected.index:
                continue

            lat = pd.to_numeric(selected.at[language, "latitude"], errors="coerce")
            lon = pd.to_numeric(selected.at[language, "longitude"], errors="coerce")
            if pd.isna(lat) or pd.isna(lon):
                continue

            try:
                distances = [getGreatCircleDistance(lat, lon, a_lat, a_lon) / MAX_DIST for a_lat, a_lon in anchors]
                data[row, :, 0] = np.array(distances, dtype=np.float32)
            except Exception:
                data[row, :, 0] = -1.0

        self.feats[2] = np.asarray(features, dtype=str)
        self.langs[2] = languages
        self.data[2] = data
        self.sources[2] = np.asarray(["GLOTTOLOG_DERIVED"])

        if self.cache:
            np.savez(os.path.join(self.cur_dir, "database", self.files[2]), feats=self.feats[2], data=self.data[2], langs=self.langs[2], sources=self.sources[2])

        self._sync_loaded_features(2)
        self._refresh_indexes(2)


    def _calculate_script_vectors(self):
        """
            Rebuilds the full script-features matrix from script_data.csv and applies
            feature_mappings.json rules to derive and remove script features. Exact-collapse
            rules combine bundled SCRIPTSOURCE columns, while positive-implication rules
            propagate positive values to a fixed point. The source axis is labelled
            "SCRIPTSOURCE_DERIVED".

            If caching is enabled, overwrites the "script_features.npz" file.
        """
        self._ensure_feature_mappings()

        csv_path = os.path.join(self.cur_dir, "database", "urielplus_csvs", "script_data.csv")
        script_csv = pd.read_csv(csv_path)
        script_csv.columns = script_csv.columns.str.strip('"')
        script_csv["language_id"] = script_csv["language_id"].str.strip('"')

        raw_columns = [col for col in script_csv.columns if col not in ("language_id", "language_name")]
        column_position = {col: idx for idx, col in enumerate(raw_columns)}

        languages = np.asarray(self.langs[1], dtype=str)
        data = np.full((len(languages), len(raw_columns), 1), -1.0, dtype=np.float32)

        row_by_language = {str(lang).strip('"'): i for i, lang in enumerate(script_csv["language_id"])}
        for row, language in enumerate(languages):
            source_row = row_by_language.get(language)
            if source_row is None:
                continue
            for col in raw_columns:
                data[row, column_position[col], 0] = float(script_csv.at[source_row, col])

        # Apply SCRIPTSOURCE exact-collapse rules restricted to the "script" matrix
        removed = set()
        for record in self.feature_mappings:
            if record.get("database") != "SCRIPTSOURCE":
                continue

            if record.get("disposition") in ("not_represented", "collapsed_into"):
                removed.update(record.get("bundled_columns", ()))

            if record.get("relationship") != "exact_collapse":
                continue

            for target in record.get("targets", ()):
                if target.get("matrix") != "script":
                    continue

                expression = target["expression"]
                match = re.compile(r"^OR\((.*)\)$").fullmatch(str(expression).strip())
                if match is None:
                    raise ValueError(f"unsupported exact-collapse expression: {expression!r}")
                operands = tuple(part.strip() for part in match.group(1).split(","))
                if any(op not in column_position for op in operands):
                    continue  # operand not present in this build yet; nothing to collapse for this target

                operand_indices = [column_position[op] for op in operands]
                operand_values = data[:, operand_indices, 0]
                collapsed = np.where(
                    np.any(operand_values == 1, axis=1), 1,
                    np.where(np.all(operand_values == 0, axis=1), 0, -1)
                )

                target_feature = target["feature_id"]
                if target_feature not in column_position:
                    data = np.concatenate([data, np.full((len(languages), 1, 1), -1.0, dtype=np.float32)], axis=1)
                    raw_columns.append(target_feature)
                    column_position[target_feature] = len(raw_columns) - 1

                target_index = column_position[target_feature]
                data[:, target_index, 0] = np.maximum(data[:, target_index, 0], collapsed)

        # Apply positive-implication rules restricted to the "script" matrix
        implication_records = [
            record for record in self.feature_mappings
            if record.get("database") == "URIELPLUS"
            and record.get("relationship") == "positive_implication"
            and any(target.get("matrix") == "script" for target in record.get("targets", ()))
        ]

        for _ in range(len(implication_records) + 1):
            changed = False
            for record in implication_records:
                antecedents = [item["id"] for item in record.get("source_features", ())]
                targets = [t for t in record.get("targets", ()) if t.get("matrix") == "script"]
                if len(targets) != 1 or any(a not in column_position for a in antecedents):
                    continue

                target_feature = targets[0]["feature_id"]
                if target_feature not in column_position:
                    continue

                antecedent_indices = [column_position[a] for a in antecedents]
                active = np.any(data[:, antecedent_indices, 0] == 1, axis=1)

                target_index = column_position[target_feature]
                update = active & (data[:, target_index, 0] != 1)
                if update.any():
                    data[update, target_index, 0] = 1
                    changed = True
            if not changed:
                break
        else:
            raise ValueError("script positive-implication rules did not reach a fixed point.")

        # Drop raw columns that were bundled into a derived feature or explicitly not represented
        keep_mask = np.array([col not in removed for col in raw_columns])
        features = np.asarray(raw_columns, dtype=str)[keep_mask]
        data = data[:, keep_mask, :]

        self.feats[3] = features
        self.langs[3] = languages
        self.data[3] = data
        self.sources[3] = np.asarray(["SCRIPTSOURCE_DERIVED"])

        if self.cache:
            np.savez(os.path.join(self.cur_dir, "database", self.files[3]), feats=self.feats[3], data=self.data[3], langs=self.langs[3], sources=self.sources[3])

        self._sync_loaded_features(3)
        self._refresh_indexes(3)



    def _get_or_create_derived_source(self):
        """
            Finds the "DERIVED" source, creating an empty layer
            (initialized to -1 for every existing language and feature) if it does not already exist.

            Returns:
                int: The index of the "DERIVED" source.
        """
        matches = np.where(self.sources[1] == "DERIVED")[0]
        if len(matches):
            return int(matches[0])
        self.data[1] = self._set_new_data_dimensions(self.data[1], [], [], ["DERIVED"])
        self.sources[1] = np.append(self.sources[1], "DERIVED")
        return len(self.sources[1]) - 1


    def _ensure_feature_mappings(self):
        """
            This function ensures feature mappings are loaded before use.
        """
        if not hasattr(self, "feature_mappings"):
            path = os.path.join(self.cur_dir, "database", "urielplus_csvs", "feature_mappings.json")
            with open(path, "r", encoding="utf-8") as f:
                self.feature_mappings = json.load(f)


    def _feature_inclusion_map(self, database, columns):
        """
            Determines whether each raw column belonging to a database should become its own public
            typological feature, according to "feature_mappings.json".


            Args:
                database (str): The name of the database whose columns are being checked (e.g. "GRAMBANK").
                columns (list): The raw column names to check, exactly as they appear in the source CSV.


            Returns:
                dict: A mapping from each column name to True (disposition "represented" or "collapsed_into" -
                the latter is written temporarily so inferred_features() can read it as an exact_collapse
                operand, then purged by _removed_operand_features() once consumed) or False (disposition
                "not_represented", excluded because it maps to no public feature at all, ever).


            Raises:
                ValueError: If a column is undocumented, a documented column is not present in columns, a
                column is documented more than once with conflicting dispositions, or a column is
                documented with a disposition other than "represented", "collapsed_into", or
                "not_represented".
        """
        self._ensure_feature_mappings()

        column_dispositions = {}
        for record in self.feature_mappings:
            if record.get("database") != database:
                continue

            # Ignore historical bundled conversion column mappings.
            if any(
                source_feature.get("namespace") in (
                    "urielplus_v1_bundled_conversion_column",
                    "removed_urielplus_operand",
                )
                for source_feature in record.get("source_features", ())
            ):
                continue
            
            disposition = record.get("disposition")
            for column in record.get("bundled_columns", ()):
                if disposition not in ("represented", "collapsed_into", "not_represented"):
                    raise ValueError(
                        f"{database} column {column!r} is documented with an unsupported disposition: {disposition!r}."
                    )
                existing = column_dispositions.get(column)
                if existing is not None and existing != disposition:
                    raise ValueError(
                        f"{database} column {column!r} is documented with conflicting dispositions."
                    )
                column_dispositions[column] = disposition

        documented = set(column_dispositions)
        provided = set(columns)
        if documented != provided:
            undocumented = sorted(provided - documented)
            unmatched = sorted(documented - provided)
            raise ValueError(
                f"{database} mappings must document every bundled feature column exactly once. "
                f"Undocumented columns: {undocumented}. Documented columns not present in the source: {unmatched}."
            )

        return {
            column: disposition in ("represented", "collapsed_into")
            for column, disposition in column_dispositions.items()
        }


    def inferred_features(self):
        """
            Consolidates typological features according to "feature_mappings.json".
            Exact-collapse rules populate the "DERIVED" source using either values
            merged across real sources or three-valued OR over the rule's operands.
            Positive-implication rules propagate positive values to a fixed point.
            Redundant features marked as "not_represented", "collapsed_into", or
            "removed_urielplus_operand" are removed unless protected by a represented
            target.

            If caching is enabled, updates the "features.npz" file.
        """
        self._ensure_feature_mappings()

        derived_index = self._get_or_create_derived_source()
        feature_position = {str(feat): idx for idx, feat in enumerate(self.feats[1])}

        logging.info("Inferring feature data based on similar features.....")

        # Exact collapse
        for record in self.feature_mappings:
            if record.get("relationship") != "exact_collapse":
                continue
            targets = [t for t in record.get("targets", ()) if t.get("matrix") == "typological"]
            if not targets:
                continue

            is_global = record.get("database") == "URIELPLUS"
            source_index = None
            if not is_global:
                source_matches = np.where(self.sources[1] == record.get("source_layer"))[0]
                if len(source_matches) == 0:
                    continue  # this record's source is not part of the current build yet
                source_index = source_matches[0]

            for target in targets:
                target_feature = target["feature_id"]

                if is_global:
                    # Merge the target's own value across every real source into DERIVED; no operands here.
                    if target_feature not in feature_position:
                        continue  # nothing written to this target by any other rule yet
                    real_source_indices = [i for i in range(len(self.sources[1])) if i != derived_index]
                    collapsed = self.data[1][:, feature_position[target_feature], real_source_indices].max(axis=1)
                else:
                    # Each target carries its own operand set in "expression"; a record's "source_features"/
                    # "bundled_columns" may be a broader union shared across several targets (or something
                    # other than typological feature IDs), so it must not stand in for this.
                    expression = target["expression"]
                    match = re.compile(r"^OR\((.*)\)$").fullmatch(str(expression).strip())
                    if match is None:
                        raise ValueError(f"unsupported exact-collapse expression: {expression!r}")
                    operands = tuple(part.strip() for part in match.group(1).split(","))
                    if not operands or any(not operand for operand in operands):
                        raise ValueError(f"malformed exact-collapse expression: {expression!r}")

                    if any(op not in feature_position for op in operands):
                        continue  # operand not present in this build yet; nothing to collapse for this target

                    operand_indices = [feature_position[op] for op in operands]
                    operand_values = self.data[1][:, operand_indices, source_index]

                    collapsed = np.where(
                        np.any(operand_values == 1, axis=1), 1,
                        np.where(np.all(operand_values == 0, axis=1), 0, -1)
                    )

                if target_feature not in feature_position:
                    self.data[1] = self._set_new_data_dimensions(self.data[1], [target_feature], [], [])
                    self.feats[1] = np.append(self.feats[1], target_feature)
                    feature_position[target_feature] = len(self.feats[1]) - 1
                    derived_index = self._get_or_create_derived_source()

                target_index = feature_position[target_feature]
                current = self.data[1][:, target_index, derived_index]
                self.data[1][:, target_index, derived_index] = np.maximum(current, collapsed)

        # Positive implication: propagate "1" from antecedent to consequent, to a fixpoint
        implication_records = [
            record for record in self.feature_mappings
            if record.get("database") == "URIELPLUS" and record.get("relationship") == "positive_implication"
            and any(t.get("matrix") == "typological" for t in record.get("targets", ()))
        ]

        for _ in range(len(implication_records) + 1):
            changed = False
            for record in implication_records:
                antecedents = [item["id"] for item in record.get("source_features", ())]
                targets = [t for t in record.get("targets", ()) if t.get("matrix") == "typological"]
                if len(targets) != 1 or any(a not in feature_position for a in antecedents):
                    continue
                target_feature = targets[0]["feature_id"]
                if target_feature not in feature_position:
                    continue

                antecedent_indices = [feature_position[a] for a in antecedents]
                active = np.any(self.data[1][:, antecedent_indices, :] == 1, axis=(1, 2))

                target_index = feature_position[target_feature]
                update = active & (self.data[1][:, target_index, derived_index] != 1)
                if update.any():
                    self.data[1][update, target_index, derived_index] = 1
                    changed = True
            if not changed:
                break
        else:
            raise ValueError("typological positive-implication rules did not reach a fixed point.")

        removed = set()
        protected = set()
        for record in self.feature_mappings:
            for source_feature in record.get("source_features", ()):
                if source_feature.get("namespace") == "removed_urielplus_operand":
                    removed.add(source_feature["id"])

            if record.get("disposition") in ("not_represented", "collapsed_into"):
                removed.update(record.get("bundled_columns", ()))

            if record.get("disposition") == "represented":
                protected.update(
                    target["feature_id"]
                    for target in record.get("targets", ())
                    if target.get("matrix") == "typological"
                )
        removed_operands = removed - protected

        redundant_mask = np.isin(self.feats[1], list(removed_operands))
        if redundant_mask.any():
            self.feats[1] = self.feats[1][~redundant_mask]
            self.data[1] = self.data[1][:, ~redundant_mask, :]

        if self.cache:
            np.savez(os.path.join(self.cur_dir, "database", self.files[1]),
                    feats=self.feats[1], data=self.data[1], langs=self.langs[1], sources=self.sources[1])

        self._sync_loaded_features(1)
        self._refresh_indexes(1)

        logging.info("Feature inference complete.")


    def integrate_saphon(self, convert_glottocodes_param=False):
        """
            Updates URIEL+ with data from the updated SAPHON database.

            This function integrates the updated SAPHON data.

            Args:
                convert_glottocodes_param (bool): If True, converts language codes to Glottocodes.
        """
        if self.is_database_incorporated("UPDATED_SAPHON"):
            logging.info("UPDATED_SAPHON already integrated; skipping.")
            return

        logging.info("Importing updated SAPHON from \"saphon_data.csv\"....")

        saphon_data = pd.read_csv(os.path.join(self.cur_dir, "database", "urielplus_csvs", "saphon_data.csv"))

        code_col = "iso_code" if (self.codes == "Iso" and not convert_glottocodes_param) else "glottocode"

        source_index = np.where(self.sources[1] == "PHOIBLE_SAPHON")

        for i, lang in enumerate(saphon_data[code_col]):
            if not pd.isna(lang):
                lang_index = np.where(self.langs[1] == lang)[0][0]
                for feat in saphon_data.columns[2:]:
                    feat_index = np.where(self.feats[1] == feat)
                    self.data[1][lang_index, feat_index, source_index] = saphon_data[feat][i]

        self.sources[1][source_index] = "UPDATED_SAPHON"

        if self.cache:
            np.savez(os.path.join(self.cur_dir, "database", self.files[1]),
                     feats=self.feats[1], data=self.data[1], langs=self.langs[1], sources=self.sources[1])

        logging.info("Updated SAPHON integration complete..")


    def integrate_bdproto(self):
        """
            Updates URIEL+ with data from the BDPROTO database.

            This function integrates the BDPROTO data, converting language codes to Glottocodes if necessary,
            and updates the feature data in URIEL+.
        """
        if self.is_database_incorporated("BDPROTO"):
            logging.info("BDPROTO already integrated; skipping.")
            return

        logging.info("Importing BDPROTO from \"bdproto_data.csv\"....")

        if self.codes == "Iso":
            self.set_glottocodes()

        bdproto_data = pd.read_csv(os.path.join(self.cur_dir, "database", "urielplus_csvs", "bdproto_data.csv"))

        new_langs = self._get_new_languages(self.langs[1], bdproto_data, "language_id")
        new_source = "BDPROTO"

        old_num_langs = self.data[1].shape[0]
        self.data[1] = self._set_new_data_dimensions(self.data[1], [], new_langs, [new_source])

        new_langs_added = 0
        for i, lang in enumerate(bdproto_data["language_id"]):
            lang_index = None
            try:
                lang_index = np.where(self.langs[1] == lang)[0][0]
                if type(lang_index) not in [int, np.int64, float, np.float64]:
                    lang_index = old_num_langs + new_langs_added
                    new_langs_added += 1
            except:
                lang_index = old_num_langs + new_langs_added
                new_langs_added += 1
            for feat in bdproto_data.columns[1:]:
                feat_index = np.where(self.feats[1] == feat)
                self.data[1][lang_index, feat_index, -1] = bdproto_data[feat][i]
        self.langs[1] = np.append(self.langs[1], np.array(new_langs).flatten())
        self.sources[1] = np.append(self.sources[1], new_source)

        if self.cache:
            np.savez(os.path.join(self.cur_dir, "database", self.files[1]),
                     feats=self.feats[1], data=self.data[1], langs=self.langs[1], sources=self.sources[1])
            
        self._calculate_phylogeny_vectors()
        self._calculate_geocoord_vectors()
        self._calculate_script_vectors()

        self._sync_loaded_features(1)
        self._refresh_indexes(1)

        logging.info("BDPROTO integration complete.")


    def integrate_grambank(self):
        """
            Updates URIEL+ with data from the Grambank database.

            This function integrates the Grambank data, converting language codes to Glottocodes if necessary,
            and updates the feature data in URIEL+.
        """
        if self.is_database_incorporated("GRAMBANK"):
            logging.info("GRAMBANK already integrated; skipping.")
            return

        self._ensure_feature_mappings()

        logging.info("Importing Grambank from \"grambank_data.csv\"....")

        if self.codes == "Iso":
            self.set_glottocodes()

        grambank_data = pd.read_csv(os.path.join(self.cur_dir, "database", "urielplus_csvs", "grambank_data.csv"))

        inclusion = self._feature_inclusion_map("GRAMBANK", list(grambank_data.columns[1:]))
        included_columns = [col for col in grambank_data.columns[1:] if inclusion[col]]

        new_feats = self._get_new_features(self.feats[1], included_columns)
        new_langs = self._get_new_languages(self.langs[1], grambank_data, "language_id")
        new_source = "GRAMBANK"

        old_num_langs = self.data[1].shape[0]
        self.data[1] = self._set_new_data_dimensions(self.data[1], new_feats, new_langs, [new_source])

        self.feats[1] = np.append(self.feats[1], new_feats)

        new_langs_added = 0
        for i, lang in enumerate(grambank_data["language_id"]):
            lang_index = None
            try:
                lang_index = np.where(self.langs[1] == lang)[0][0]
                if type(lang_index) not in [int, np.int64, float, np.float64]:
                    lang_index = old_num_langs + new_langs_added
                    new_langs_added += 1
            except:
                lang_index = old_num_langs + new_langs_added
                new_langs_added += 1
            for feat in grambank_data.columns[1:]:
                feat_index = np.where(self.feats[1] == feat)
                self.data[1][lang_index, feat_index, -1] = grambank_data[feat][i]
        self.langs[1] = np.append(self.langs[1], np.array(new_langs).flatten())
        self.sources[1] = np.append(self.sources[1], new_source)

        if self.cache:
            np.savez(os.path.join(self.cur_dir, "database", self.files[1]),
                     feats=self.feats[1], data=self.data[1], langs=self.langs[1], sources=self.sources[1])
            
        self._calculate_phylogeny_vectors()
        self._calculate_geocoord_vectors()
        self._calculate_script_vectors()

        self.inferred_features()

        logging.info("Grambank integration complete.")


    def integrate_apics(self):
        """
            Updates URIEL+ with data from the APiCS database.

            This function integrates the APiCS data, converting language codes to Glottocodes if necessary,
            and updates the feature data in URIEL+.
        """
        if self.is_database_incorporated("APICS"):
            logging.info("APICS already integrated; skipping.")
            return
        
        self._ensure_feature_mappings()

        logging.info("Importing APiCS from \"apics_data.csv\"....")

        if self.codes == "Iso":
            self.set_glottocodes()

        apics_data = pd.read_csv(os.path.join(self.cur_dir, "database", "urielplus_csvs", "apics_data.csv"))

        new_langs = self._get_new_languages(self.langs[1], apics_data, "language_id")

        apics_data = apics_data[["language_id"] + [col for col in apics_data.columns if col != "language_id"]]

        inclusion = self._feature_inclusion_map("APICS", list(apics_data.columns[1:]))
        included_columns = [col for col in apics_data.columns[1:] if inclusion[col]]

        new_feats = self._get_new_features(self.feats[1], included_columns)

        new_source = "APICS"

        old_num_langs = self.data[1].shape[0]
        self.data[1] = self._set_new_data_dimensions(self.data[1], new_feats, new_langs, [new_source])

        self.feats[1] = np.append(self.feats[1], new_feats)

        new_langs_added = 0
        for i, lang in enumerate(apics_data["language_id"]):
            lang_index = None
            try:
                lang_index = np.where(self.langs[1] == lang)[0][0]
                if type(lang_index) not in [int, np.int64, float, np.float64]:
                    lang_index = old_num_langs + new_langs_added
                    new_langs_added += 1
            except:
                lang_index = old_num_langs + new_langs_added
                new_langs_added += 1
            for feat in apics_data.columns[1:]:
                feat_index = np.where(self.feats[1] == feat)

                self.data[1][lang_index, feat_index, -1] = apics_data[feat][i]
        self.langs[1] = np.append(self.langs[1], np.array(new_langs).flatten())
        self.sources[1] = np.append(self.sources[1], new_source)

        if self.cache:
            np.savez(os.path.join(self.cur_dir, "database", self.files[1]),
                     feats=self.feats[1], data=self.data[1], langs=self.langs[1], sources=self.sources[1])

        self._calculate_phylogeny_vectors()
        self._calculate_geocoord_vectors()
        self._calculate_script_vectors()

        self.inferred_features()

        logging.info("APiCS integration complete.")


    def integrate_ewave(self):
        """
            Updates URIEL+ with data from the EWAVE database.

            This function integrates the EWAVE data, converting language codes to Glottocodes if necessary,
            and updates the feature data in URIEL+.
        """
        if self.is_database_incorporated("EWAVE"):
            logging.info("EWAVE already integrated; skipping.")
            return
        
        self._ensure_feature_mappings()

        logging.info("Importing eWAVE from \"english_dialect_data.csv\"....")

        if self.codes == "Iso":
            self.set_glottocodes()

        df = pd.read_csv(os.path.join(os.path.join(self.cur_dir, "database", "urielplus_csvs", "english_dialect_data.csv")))

        inclusion = self._feature_inclusion_map("EWAVE", list(df.columns[1:]))
        included_columns = [col for col in df.columns[1:] if inclusion[col]]

        new_langs = self._get_new_languages(self.langs[1], df, "language_id")
        new_feats = self._get_new_features(self.feats[1], included_columns)
        new_source = "EWAVE"

        old_num_langs = self.data[1].shape[0]
        self.data[1] = self._set_new_data_dimensions(self.data[1], new_feats, new_langs, [new_source])

        self.feats[1] = np.append(self.feats[1], new_feats)

        new_langs_added = 0
        for i, lang in enumerate(df["language_id"]):
            lang_index = None
            try:
                lang_index = np.where(self.langs[1] == lang)[0][0]
                if type(lang_index) not in [int, np.int64, float, np.float64]:
                    lang_index = old_num_langs + new_langs_added
                    new_langs_added += 1
            except:
                lang_index = old_num_langs + new_langs_added
                new_langs_added += 1
            for feat in df.columns[1:]:
                feat_index = np.where(self.feats[1] == feat)
                self.data[1][lang_index, feat_index, -1] = df[feat][i]
        self.langs[1] = np.append(self.langs[1], np.array(new_langs).flatten())
        self.sources[1] = np.append(self.sources[1], new_source)

        if self.cache:
            np.savez(os.path.join(self.cur_dir, "database", self.files[1]),
                     feats=self.feats[1], data=self.data[1], langs=self.langs[1], sources=self.sources[1])

        self._calculate_phylogeny_vectors()
        self._calculate_geocoord_vectors()
        self._calculate_script_vectors()

        self.inferred_features()

        logging.info("eWAVE integration complete.")


    def integrate_glottolog(self):
        """
            Updates URIEL+ with data from the Glottolog database.

            This function integrates the Glottolog data.
        """
        logging.info("Importing Glottolog from \"dialects.csv\"....")

        if self.codes == "Iso":
            self.set_glottocodes()
        
        glottolog_data = pd.read_csv(os.path.join(self.cur_dir, "database", "urielplus_csvs", "dialects.csv"))

        code_cols = ['Language Glot', 'Dialect(s) Glot']

        new_langs = set()

        for col in code_cols:
            for entry in glottolog_data[col].dropna():
                parts = [code.strip() for code in entry.split(',') if code.strip()]
                new_langs.update(parts)

        existing_langs = set(self.langs[1]) if len(self.langs) > 1 else set()
        new_langs = sorted(new_langs - existing_langs)

        if not new_langs:
            logging.info("GLOTTOLOG dialects already integrated; skipping.")
            return

        self.data[1] = self._set_new_data_dimensions(self.data[1], [], new_langs, [])
        self.langs[1] = np.append(self.langs[1], np.array(new_langs).flatten())
        
        if self.cache:
            np.savez(os.path.join(self.cur_dir, "database", self.files[1]),
                     feats=self.feats[1], data=self.data[1], langs=self.langs[1], sources=self.sources[1])

        self._calculate_phylogeny_vectors()
        self._calculate_geocoord_vectors()
        self._calculate_script_vectors()

        self._sync_loaded_features(1)
        self._refresh_indexes(1)

        logging.info("Glottolog integration complete.")


    def integrate_databases(self):
        """
            Updates URIEL+ with data from all available databases (UPDATED_SAPHON, BDPROTO, GRAMBANK, APICS, EWAVE, GLOTTOLOG).
        """
        logging.info("Importing all databases....")

        databases = {
            "UPDATED_SAPHON": self.integrate_saphon,
            "BDPROTO": self.integrate_bdproto,
            "GRAMBANK": self.integrate_grambank,
            "APICS": self.integrate_apics,
            "EWAVE": self.integrate_ewave,
        }
       
        for db, integrate_method in databases.items():
            if not self.is_database_incorporated(db):
                integrate_method()

        self.integrate_glottolog()
        self.inferred_features()

        logging.info("All databases integration complete.")


    def integrate_custom_databases(self, *args):
        """
            Updates URIEL+ based on provided databases.

            Args:
                *args: Databases to update URIEL+ with.

            Raises:
                KeyError: If a provided database name is invalid.
        """
        logging.info("Importing custom databases....")

        if len(args) == 1 and isinstance(args[0], list):
            databases = args[0]
        else:
            databases = list(args)

        valid_databases = {
            "UPDATED_SAPHON": self.integrate_saphon,
            "BDPROTO": self.integrate_bdproto,
            "GRAMBANK": self.integrate_grambank,
            "APICS": self.integrate_apics,
            "EWAVE": self.integrate_ewave,
            "GLOTTOLOG": self.integrate_glottolog,
            "INFERRED": self.inferred_features,
        }

        for db in databases:
            if db not in valid_databases:
                raise KeyError(f"Unknown database: {db}. Valid databases are {list(valid_databases.keys())}.")
            if db == "GLOTTOLOG" or not self.is_database_incorporated(db):
                valid_databases[db]()
           
        logging.info("Custom databases integration complete.")
