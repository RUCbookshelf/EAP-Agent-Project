# CALF References and verification status

Reference IDs in the registry point to the following sources. `metadata/abstract verified` means the bibliographic record or abstract was checked, not that the full text was locally verified.

| ID | Reference | Verification |
|---|---|---|
| `REF-LD-MTLD-001`, `REF-LD-HDD-001` | McCarthy, P. M., & Jarvis, S. (2010). MTLD, vocd-D, and HD-D: A validation study of sophisticated approaches to lexical diversity assessment. *Behavior Research Methods, 42*(2), 381–392. https://doi.org/10.3758/BRM.42.2.381 | metadata/abstract verified; full text not verified |
| `REF-CALF-001` | McCarthy, P. M., & Jarvis, S. (2007). vocd: A theoretical and empirical evaluation. *Language Testing, 24*(4), 459–488. https://doi.org/10.1177/0265532207080767 | metadata/abstract verified; full text not verified |
| `REF-IMPLEMENTATION-001` | Kyle, K. (2020). `lexical-diversity` 0.1.1 source distribution. PyPI/GitHub. | package source inspected; used only as an independent numerical reference, not a runtime dependency |
| `REF-LD-MATTR-001` | Covington, M. A., & McFall, J. D. (2010). Cutting the Gordian knot: The moving-average type-token ratio (MATTR). *Journal of Quantitative Linguistics, 17*(2), 94–100. https://doi.org/10.1080/09296171003643098 | bibliographic metadata verified; full text not verified |
| `REF-SYNTAX-001` | Lu, X. (2010). Automatic analysis of syntactic complexity in second language writing. *International Journal of Corpus Linguistics, 15*(4), 474–496. https://doi.org/10.1075/ijcl.15.4.02lu | bibliographic metadata verified; implementation equivalence not claimed |
| `REF-ACCURACY-001`, `REF-FLUENCY-001` | Wolfe-Quintero, K., Inagaki, S., & Kim, H.-Y. (1998). *Second Language Development in Writing: Measures of Fluency, Accuracy, and Complexity*. University of Hawai‘i Press. | secondary review metadata verified; full text not verified |

The MTLD/HD-D implementation is deterministic, fixture-tested, and numerically checked against the inspected open-source reference. That agreement is software verification, not population validation.
