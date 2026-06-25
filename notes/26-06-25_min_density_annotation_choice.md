# Minimum Density Annotation Selection

## Problem
In the visual annotation matching algorithm (`match_annotations_to_choices`), a binary bitmap represents the drawing/ink strokes as `0` and the white background as `1`. Previously, the code selected the radio choice with the *maximum* mean value. However, a higher mean value corresponds to more background (less ink), whereas the correct approach is to select the radio choice with the *minimum* mean value (the one with the most ink/strokes).

## Change
- Modified [annotation_matcher.py](file:///home/khemi/workspace/app_to_bt/worker/src/pdf_processor/annotation_matcher.py) to initialize `min_field_val = 1.0`.
- Changed the comparison check to evaluate `choice_bitmap_mean < min_field_val` so that the choice containing the most ink (lowest mean) is correctly identified and selected.
