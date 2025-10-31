# [URIEL+: Enhancing Linguistic Inclusion and Usability in a Typological and Multilingual Knowledge Base](https://aclanthology.org/2025.coling-main.463/)

![knowledge base for natural language processing](./logo.png)

URIEL is a knowledge base offering geographical, phylogenetic, and typological vector representations for 7970 languages. It includes distance measures between these vectors for 4005 languages, which are accessible via the lang2vec tool. Despite being frequently cited, URIEL is limited in terms of linguistic inclusion and overall usability. To tackle these challenges, we introduce URIEL+, an enhanced version of URIEL and lang2vec addressing these limitations. In addition to expanding typological feature coverage for 2898 languages, URIEL+ improves user experience with robust, customizable distance calculations to better suit the needs of the users. These upgrades also offer competitive performance on downstream tasks and provide distances that better align with linguistic distance studies.

If you are interested for more information, check out our [full paper](https://aclanthology.org/2025.coling-main.463/).

## Citation

<u>If you use this code for your research, please cite the following work:</u>

```bibtex
@inproceedings{khan-etal-2025-uriel,
    title = "{URIEL}+: Enhancing Linguistic Inclusion and Usability in a Typological and Multilingual Knowledge Base",
    author = {Khan, Aditya  and
      Shipton, Mason  and
      Anugraha, David  and
      Duan, Kaiyao  and
      Hoang, Phuong H.  and
      Khiu, Eric  and
      Do{\u{g}}ru{\"o}z, A. Seza  and
      Lee, En-Shiun Annie},
    editor = "Rambow, Owen  and
      Wanner, Leo  and
      Apidianaki, Marianna  and
      Al-Khalifa, Hend  and
      Eugenio, Barbara Di  and
      Schockaert, Steven",
    booktitle = "Proceedings of the 31st International Conference on Computational Linguistics",
    month = jan,
    year = "2025",
    address = "Abu Dhabi, UAE",
    publisher = "Association for Computational Linguistics",
    url = "https://aclanthology.org/2025.coling-main.463/",
    pages = "6937--6952",
    abstract = "URIEL is a knowledge base offering geographical, phylogenetic, and typological vector representations for 7970 languages. It includes distance measures between these vectors for 4005 languages, which are accessible via the lang2vec tool. Despite being frequently cited, URIEL is limited in terms of linguistic inclusion and overall usability. To tackle these challenges, we introduce URIEL+, an enhanced version of URIEL and lang2vec that addresses these limitations. In addition to expanding typological feature coverage for 2898 languages, URIEL+ improves the user experience with robust, customizable distance calculations to better suit the needs of users. These upgrades also offer competitive performance on downstream tasks and provide distances that better align with linguistic distance studies."
}
```

If you have any questions, you can open a [GitHub Issue](https://github.com/Lee-Language-Lab/URIELPlus/issues) or send us an [email](mailto:masonshipton25@gmail.com).

Contributors: [Aditya Khan](mailto:adityakhan@cs.toronto.edu), [Mason Shipton](mailto:masonshipton25@gmail.com), [York Hay Ng](mailto:york.ng@mail.utoronto.ca), [David Anugraha](mailto:anugraha@cs.toronto.edu), [Kaiyao Duan](mailto:davidduan04@gmail.com), [Phuong H. Hoang](mailto:fiona.hoang@mail.utoronto.ca), [Eric Khiu](mailto:erickhiu@umich.edu), [Xiang Lu](mailto:jameslx@umich.edu), [A. Seza Doğruöz](mailto:as.dogruoz@ugent.be), [En-Shiun Annie Lee](mailto:annie.lee@ontariotechu.ca)

## Contents

+ [Environment](#environment)
+ [Setup Instruction](#setup-instruction)
+ [Configuration Options Examples](#configuration-options-examples)
+ [Retrieving Loaded Features Examples](#retrieving-loaded-features-examples)
+ [Database Integration Examples](#database-integration-examples)
+ [Imputation Examples](#imputation-examples)
+ [Language Distance Calculation Examples](#language-distance-calculation-examples)

## Environment

Python 3.10 or later. If you're working with the `MIDASpy` extra dependencies, version of Python must be less than 3.11. Details of dependencies are in `setup.py`. NOTE: There are known issues with the MIDASpy extra dependencies. Please use between Python 3.10 and Python 3.11 for the time being.

## Setup Instruction

+ To get started with URIEL+:
    ```bash
    pip install urielplus
    ```

    ```python
    from urielplus import urielplus

    u = urielplus.URIELPlus()
    ```

## Configuration Options Examples

+ URIEL+ offers various configurations that you can adjust:
    - Caching: Enable or disable caching (True or False).
    - Aggregation Method: Choose the method for aggregating data across sources ('U' for unweighted, 'A' for weighted).
    - Fill Missing Data: Decide whether to fill missing data using parent language data (True or False).
    - Distance Metric: Specify the distance metric to be used ("angular" or "cosine").

+ Changing A Configuration:
    ```python
    u.set_{configuration}({option})
    ```

+ Checking A Configuration:
    ```python
    u.get_{configuration}({option})
    ```

+ Replace `{configuration}` with `cache`, `aggregation`, `fill_with_base_lang`, or `distance_metric`.
+ Replace `{option}` with your desired value for the selected configuration.
+ Note: the default configurations are `cache=False`, `aggregation='U'`, `fill_with_base_lang=True`, and `distance_metric="angular"`.

## Retrieving Loaded Features Examples

+ Retrieving A Loaded Feature:
    ```python
    u.get_{vector_type}_{feature_type}_array()
    ```
+ Replace `{vector_type}` with `phylogeny`, `typological`, `geography`, or `scriptural`.
+ Replace `{feature_type}` with `features`, `languages`, `data`, or `sources`.

+ Example:
    ```python
    u.get_typological_languages_array()
    ```

## Database Integration Examples

+ Integrating One Database:
    ```python
    u.integrate_{database}()
    ```
+ Integrating Some Databases:
    ```python
    u.integrate_custom_databases({databases})
    ```
+ Integrating All Databases:
    ```python
    u.integrate_databases()
    ```
+ Set Language Codes to Glottocodes:
    ```python
    u.set_glottocodes()
    ```
+ Reset all changes:
    ```python
    u.reset()
    ```
+ Import (and replace all existing) data from a custom CSV file:
  ```python
    u.import_csv({file_path}, {index})
    ```

+ Replace `{database}` with `saphon`, `bdproto`, `grambank`, `apics`, `ewave`, or `glottolog`.
+ Replace `{databases}` with arguments `"UPDATED_SAPHON"`, `"BDPROTO"`, `"GRAMBANK"`, `"APICS"`, `"EWAVE"`, and/or `"GLOTTOLOG"` (e.g., `"UPDATED_SAPHON"`, `"BDPROTO"`, `"EWAVE"`).
+ Replace `{index}` with `0` for genetic data, `1` for typological data, `2` for geographic data, or `3` for scriptural data.

## Imputation Examples

+ Aggregate Typological and Scriptural Data:
    ```python
    u.set_aggregation({aggregation}) 
    u.aggregate()
    ```

+ Impute Missing Values:
    ```python
    u.{imputation_strategy}_imputation()
    ```

+ Replace `{aggregation}` with `'U'` (union) or `'A'` (average).
+ Replace `{imputation_strategy}` with `midaspy`, `knn`, `softimpute`, or `mean`.

## Language Distance Calculation Examples

+ Calculate a Specific Distance:
    ```python
    print(u.new_distance({distance_type}, {languages}))
    ```

+ Calculate Distance Using Specific Features:
    ```python
    print(u.new_custom_distance({features}, {languages}, {source}))
    ```

+ Retrieve Language Vectors:
    ```python
    u.get_vector({distance_type}, {languages})
    ```

+ View URIEL+ Feature Coverage:
    ```python
    u.feature_coverage()
    ```

+ Calculate Confidence Scores for Distances
    ```python
    print(u.confidence_score({language 1}, {language 2}, {distance_type}))
    ```

+ Replace `{distance_type}` with a distance type (e.g., `"featural"`) or a list (e.g., `["syntactic"`, `"phonological"]`). Must be single distance type for retrieving language vectors.
+ Replace `{features}` with a list of features (e.g., `["F_Germanic", "S_SVO", "P_NASAL_VOWELS"]`).
+ Replace `{languages}`, `{language 1}`, and `{language 2}` with language codes (e.g., `"stan1293"`, `"hind1269"`).
+ Replace `{source}` with one database (e.g., `"WALS"`) or all databases (`'A'`).
+ Note: the default `{source}` is all databases.





