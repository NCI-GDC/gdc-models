import types

from gdcmodels.sync.graph import annotation, case, file, project

SYNCHRONIZERS = types.MappingProxyType(
    {
        "gdc_from_graph": types.MappingProxyType(
            {
                "annotation": annotation.SYNCHRONIZER,
                "case": case.SYNCHRONIZER,
                "file": file.SYNCHRONIZER,
                "project": project.SYNCHRONIZER,
            }
        )
    }
)
