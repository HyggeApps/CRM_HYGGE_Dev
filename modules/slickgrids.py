import datetime
import streamlit as st
from streamlit_slickgrid import (
    Formatters,
    FieldType,
    ExportServices,
    Filters,
    StreamlitSlickGridFormatters
)

red = "#ff4b4b"
orange = "#ffa421"
yellow = "#ffe312"
green = "#21c354"

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


        ua_str = empresa.get("ultima_atividade", "")
        if ua_str:
            try:
                ua_date = datetime.datetime.strptime(ua_str, "%Y-%m-%d").date()
                today = datetime.date.today()
                atividade_dias = (today - ua_date).days
            except Exception:
                atividade_dias = ""
        else:
                atividade_dias = ""

        dataset.append({
            "id": eid,
            "empresa": empresa_nome,
            "contatos": contatos_list if contatos_list else None,
            "vendedor": empresa.get("proprietario", ""),
            "ultima_atividade": atividade_dias,
            "__parent": None,
            "__depth": 0,
            "title": empresa_nome,
        })
        eid += 1

    data = dataset

    # Cria lista única de vendedores a partir da coleção empresas para o select-box do filtro
    unique_vendedores = sorted(list(set(
        empresa.get("proprietario", "") for empresa in empresas if empresa.get("proprietario", "")
    )))

    columns = [
        {
            "id": "title",
            "name": "Empresas cadastradas",
            "field": "title",
            "sortable": True,
            "minWidth": 200,
            "type": FieldType.string,
            "filterable": True,
            "formatter": Formatters.tree,
            "exportCustomFormatter": Formatters.treeExport,
        },
        {
            "id": "ultima_atividade",
            "name": "Última atividade (dias)",
            "field": "ultima_atividade",
            "sortable": True,
            "minWidth": 50,
            "type": FieldType.number,
            "filterable": True,
            "filter": {
                "model": Filters.slider,
                "operator": ">=",
            },
            "formatter": StreamlitSlickGridFormatters.numberFormatter,
            "params": {
                "colors": [
                    # [maxValue, foreground, background]
                    [10, green, None],  # None equivale a deixar sem alteração
                    [30, yellow],
                    [90, orange],
                    [1000, red]
                ],
                "minDecimal": 0,
                "maxDecimal": 3,
                "numberSuffix": "d",
            },
        },
        {
            "id": "vendedor",
            "name": "Vendedor",
            "field": "vendedor",
            "sortable": True,
            "minWidth": 50,
            "type": FieldType.string,
            "filterable": True,
            "filter": {
                "model": Filters.singleSelect,
                "collection": [""] + unique_vendedores,
            },
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