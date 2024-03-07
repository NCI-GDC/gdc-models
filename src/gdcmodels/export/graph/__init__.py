import types

from gdcmodels.export.graph import annotation, case, file, project

EXPORTERS = types.MappingProxyType(
    {
        "gdc_from_graph": types.MappingProxyType(
            {
                "annotation": annotation.EXPORTER,
                "case": case.EXPORTER,
                "file": file.EXPORTER,
                "project": project.EXPORTER,
            }
        )
    }
)
