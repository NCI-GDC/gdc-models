import deepdiff
import mergedeep


def deep_merge_mapping_files(one: dict, two: dict) -> dict:
    return mergedeep.merge(one, two, strategy=mergedeep.Strategy.ADDITIVE)


def deep_diff_mapping_files(new: dict, old: dict) -> dict:
    """Return the dictionary of things that are in the old dict and not in the new."""
    diff = deepdiff.DeepDiff(new, old)
    return {} + deepdiff.Delta(diff, force=True)
