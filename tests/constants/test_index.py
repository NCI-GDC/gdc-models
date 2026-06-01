from importlib import resources

import pytest

from gdcmodels import constants

GROUPED_INDICES = constants.GRAPH_INDICES | constants.VIZ_INDICES
UNGROUPED_INDICES = frozenset(constants.Index) - GROUPED_INDICES
NON_GRAPH_INDICES = frozenset(constants.Index) - constants.GRAPH_INDICES


@pytest.mark.parametrize("index", NON_GRAPH_INDICES)
def test__components__non_graph(index: constants.Index) -> None:
    assert index.components == (str(index), str(index))


@pytest.mark.parametrize("index", constants.GRAPH_INDICES)
def test__components__graph(index: constants.Index) -> None:
    assert index.components == (constants.GRAPH_NAMESPACE, str(index))


@pytest.mark.parametrize("index", constants.GRAPH_INDICES)
def test__index_group__graph(index: constants.Index) -> None:
    assert index.index_group == "graph"


@pytest.mark.parametrize("index", constants.VIZ_INDICES)
def test__index_group__viz(index: constants.Index) -> None:
    assert index.index_group == "viz"


@pytest.mark.parametrize("index", UNGROUPED_INDICES)
def test__index_group__ungrouped(index: constants.Index) -> None:
    with pytest.raises(ValueError):
        _ = index.index_group


@pytest.mark.parametrize("index", NON_GRAPH_INDICES)
def test__models_dir__non_graph(index: constants.Index) -> None:
    assert index.models_dir == resources.files("gdcmodels.esmodels") / index


@pytest.mark.parametrize("index", constants.GRAPH_INDICES)
def test__models_dir__graph(index: constants.Index) -> None:
    assert index.models_dir == resources.files("gdcmodels.esmodels").joinpath(
        f"{constants.GRAPH_NAMESPACE}/{index}"
    )


@pytest.mark.parametrize("index", constants.VIZ_INDICES)
def test__unnormalized_properties__viz(index: constants.Index) -> None:
    assert index.unnormalized_properties == constants.VIZ_UNNORMALIZED_PROPERTIES


@pytest.mark.parametrize("index", constants.GRAPH_INDICES)
def test__unnormalized_properties__graph(index: constants.Index) -> None:
    assert index.unnormalized_properties == constants.GRAPH_UNNORMALIZED_PROPERTIES


@pytest.mark.parametrize("index", GROUPED_INDICES)
def test__overlay_file__grouped_index(index: constants.Index) -> None:
    assert index.overlay_file("test") == resources.files("gdcmodels.sync.overlays").joinpath(
        f"test/{index.index_group}/{index}.yaml"
    )


@pytest.mark.parametrize("index", UNGROUPED_INDICES)
def test__overlay_file__ungrouped_index(index: constants.Index) -> None:
    with pytest.raises(ValueError):
        _ = index.overlay_file("test")
