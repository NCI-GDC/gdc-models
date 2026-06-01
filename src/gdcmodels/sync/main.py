from importlib import resources

import tap

from gdcmodels import constants, extraction_utils
from gdcmodels.sync import mappings, vestigial


def _main(indices: tuple[constants.Index, ...] = tuple(constants.Index)):
    for index in indices:
        mapping = mappings.sync(index)
        mapping_resource = index.models_dir / constants.MAPPING_FILE
        vestigial_delta = vestigial.compute_delta(index, mapping)
        vestigial_resource = index.models_dir / constants.VESTIGIAL_FILE

        with resources.as_file(mapping_resource) as path, path.open("w+") as f:
            extraction_utils.dump_yaml(mapping, f)

        with resources.as_file(vestigial_resource) as path, path.open("w+") as f:
            vestigial_delta.dump(f)


def main() -> None:
    tap.tapify(_main)
