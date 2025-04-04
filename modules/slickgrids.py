from streamlit_slickgrid import (
    Formatters,
    FieldType,
    ExportServices,
)

def slickgrid_empresa(empresas, contatos_map):
    dataset = []
    eid = 0
    for empresa in empresas:
        empresa_nome = empresa.get("razao_social", "")
        empresa_id = empresa.get("_id")
        contatos_list = []
        if empresa_id in contatos_map:
            for contato in contatos_map[empresa_id]:
                contato_nome = contato.get("nome", "")
                contato_sobrenome = contato.get("sobrenome", "")
                full_name = f"{contato_nome} {contato_sobrenome}"
                contatos_list.append(full_name)

        dataset.append({
            "id": eid,
            "empresa": empresa_nome,
            "contatos": contatos_list if contatos_list else None,
            "vendedor": empresa.get("proprietario", ""),
            "produtos": empresa.get("produto_interesse", ""),
            "__parent": None,
            "__depth": 0,
            "title": empresa_nome,
        })
        eid += 1

    data = dataset

    columns = [
        {
            "id": "title",
            "name": "Empresas cadastradas",
            "field": "title",
            "sortable": True,
            "minWidth": 50,
            "type": FieldType.string,
            "filterable": True,
            "formatter": Formatters.tree,
            "exportCustomFormatter": Formatters.treeExport,
        },
        {
            "id": "contatos",
            "name": "Contatos associados",
            "field": "contatos",
            "sortable": True,
            "minWidth": 50,
            "type": FieldType.string,
            "filterable": True,
            "formatter": Formatters.tree,
            "exportCustomFormatter": Formatters.treeExport,
        },
        {
            "id": "vendedor",
            "name": "Vendedor",
            "field": "vendedor",
            "sortable": True,
            "minWidth": 50,
            "type": FieldType.string,
            "filterable": True,
        },
        {
            "id": "produtos",
            "name": "Lista de Produtos de Interesse",
            "field": "produtos",
            "sortable": True,
            "minWidth": 50,
            "type": FieldType.string,
            "filterable": True,
        },

    ]

    options = {
        "enableFiltering": True,
        "enableTextExport": True,
        "enableExcelExport": True,
        "excelExportOptions": {"sanitizeDataExport": True},
        "textExportOptions": {"sanitizeDataExport": True},
        "externalResources": [
            ExportServices.ExcelExportService,
            ExportServices.TextExportService,
        ],
        "autoResize": {
            "minHeight": 300,
        },
        "enableTreeData": True,
        "multiColumnSort": False,
        "treeDataOptions": {
            "columnId": "title",
            "indentMarginLeft": 15,
            "initiallyCollapsed": True,
            "parentPropName": "__parent",
            "levelPropName": "__depth",
        },
    }

    return data, columns, options