"""Tests for workbook_compare_engine.py: parsing, diffing, and impact
classification. Runs the handoff brief's own "how to verify" checklist
(identity compare = 0 changes; rename/removal, datatype, calc, parameter,
and connection mutation checks) as pytest functions.

The fixture workbook is built with xml.etree.ElementTree and re-serialized
via ET.tostring for every mutated variant - never via raw string/byte
replacement - because ElementTree decodes XML entities on parse, and a
byte-level replace would diverge from what parse_workbook() actually sees.
"""
import copy
import xml.etree.ElementTree as ET

import pytest

from workbook_compare_engine import (
    _fmt,
    _normalize_column_ref,
    _referenced_fields,
    classify_custom_view_impact,
    classify_view_impact,
    compute_diff,
    parse_workbook,
)


def _build_root():
    """A minimal but structurally realistic <workbook> covering: a
    Parameters datasource, a federated datasource with one live postgres
    connection plus a hyper/extract connection, a dimension field, a
    calculated measure field, a worksheet with a categorical filter, and a
    dashboard with one zone."""
    workbook = ET.Element("workbook")
    datasources = ET.SubElement(workbook, "datasources")

    params_ds = ET.SubElement(datasources, "datasource", {"name": "Parameters", "caption": "Parameters"})
    param_col = ET.SubElement(params_ds, "column", {"name": "[Parameter 1]", "caption": "Top N", "datatype": "integer"})
    ET.SubElement(param_col, "calculation", {"class": "tableau", "formula": "10"})

    orders_ds = ET.SubElement(datasources, "datasource", {"name": "federated.0abc123", "caption": "Orders"})
    fed_conn = ET.SubElement(orders_ds, "connection", {"class": "federated"})
    named_conns = ET.SubElement(fed_conn, "named-connections")
    named_conn = ET.SubElement(named_conns, "named-connection", {"name": "postgres.0xyz", "caption": "Orders DB"})
    ET.SubElement(named_conn, "connection", {
        "class": "postgres", "server": "db.example.com", "port": "5432",
        "dbname": "orders_db", "username": "svc_user",
    })
    ET.SubElement(orders_ds, "connection", {"class": "hyper", "dbname": "extract.hyper"})

    ET.SubElement(orders_ds, "column", {
        "name": "[Region]", "caption": "Region", "datatype": "string", "role": "dimension",
    })
    calc_col = ET.SubElement(orders_ds, "column", {
        "name": "[Calculation_1]", "caption": "Total Sales", "datatype": "real",
        "role": "measure", "aggregation": "Sum",
    })
    ET.SubElement(calc_col, "calculation", {"class": "tableau", "formula": "SUM([Sales])"})

    worksheets = ET.SubElement(workbook, "worksheets")
    ws = ET.SubElement(worksheets, "worksheet", {"name": "Sales Summary"})
    table = ET.SubElement(ws, "table")
    view = ET.SubElement(table, "view")
    filt = ET.SubElement(view, "filter", {"class": "categorical", "column": "[federated.0abc123].[Region]"})
    ET.SubElement(filt, "groupfilter", {"function": "member", "level": "[Region]", "member": "East"})

    dashboards = ET.SubElement(workbook, "dashboards")
    dash = ET.SubElement(dashboards, "dashboard", {"name": "Overview"})
    zones = ET.SubElement(dash, "zones")
    ET.SubElement(zones, "zone", {
        "id": "1", "type-v2": "worksheet", "name": "Sales Summary", "x": "0", "y": "0", "w": "800", "h": "600",
    })

    return workbook


def _bytes(root) -> bytes:
    return ET.tostring(root, encoding="utf-8")


def _parse(root):
    return parse_workbook(_bytes(root))


@pytest.fixture
def base_root():
    return _build_root()


def test_identity_diff_is_empty(base_root):
    published = _parse(base_root)
    candidate = _parse(copy.deepcopy(base_root))

    diff = compute_diff(published, candidate)
    assert diff.total == 0
    assert diff.groups == []

    impact = classify_custom_view_impact(published, candidate, diff)
    assert impact["classification"] == "no_change"
    assert impact["risk_level"] == "None"
    assert impact["findings"] == []


def test_federated_hash_prefix_normalizes_away(base_root):
    published = _parse(base_root)

    candidate_root = copy.deepcopy(base_root)
    filt = candidate_root.find(".//worksheet/table/view/filter")
    filt.set("column", "[federated.9xyz789].[Region]")
    candidate = _parse(candidate_root)

    diff = compute_diff(published, candidate)
    assert diff.total == 0
    assert not any(g.key == "filters" for g in diff.groups)


def test_hyper_extract_connection_mutation_is_ignored(base_root):
    """Negative test: changing the extract cache connection must never
    surface as a diff - it's the false-change trap the handoff called out."""
    published = _parse(base_root)

    candidate_root = copy.deepcopy(base_root)
    hyper_conn = candidate_root.find(".//datasource[@caption='Orders']/connection[@class='hyper']")
    hyper_conn.set("dbname", "extract_v2.hyper")
    candidate = _parse(candidate_root)

    diff = compute_diff(published, candidate)
    assert diff.total == 0
    assert not any(g.key == "conns" for g in diff.groups)


def test_worksheet_rename_is_high_and_directly_impacted(base_root):
    published = _parse(base_root)

    candidate_root = copy.deepcopy(base_root)
    ws = candidate_root.find(".//worksheet[@name='Sales Summary']")
    ws.set("name", "Sales Summary v2")
    candidate = _parse(candidate_root)

    diff = compute_diff(published, candidate)
    views_group = next(g for g in diff.groups if g.key == "views")
    ops = {(i.op, i.label) for i in views_group.items}
    assert ("remove", "View: Sales Summary") in ops
    assert ("add", "View: Sales Summary v2") in ops

    impact = classify_custom_view_impact(published, candidate, diff)
    assert impact["risk_level"] == "High"
    assert impact["classification"] == "directly_impacted"
    assert any(
        f["severity"] == "High" and "removed or renamed" in f["title"]
        for f in impact["findings"]
    )


def test_field_datatype_change_is_medium_and_potentially_impacted(base_root):
    published = _parse(base_root)

    candidate_root = copy.deepcopy(base_root)
    region_col = candidate_root.find(".//column[@name='[Region]']")
    region_col.set("datatype", "integer")
    candidate = _parse(candidate_root)

    diff = compute_diff(published, candidate)
    fields_group = next(g for g in diff.groups if g.key == "fields")
    change_item = next(i for i in fields_group.items if i.op == "change")
    assert change_item.label == "Field: [Region]"
    datatype_part = next(p for p in change_item.parts if p["attr"] == "datatype")
    assert datatype_part == {"attr": "datatype", "before": "string", "after": "integer"}

    impact = classify_custom_view_impact(published, candidate, diff)
    assert impact["risk_level"] == "Medium"
    assert impact["classification"] == "potentially_impacted"


def test_calc_formula_edit_shows_exact_before_after(base_root):
    published = _parse(base_root)

    candidate_root = copy.deepcopy(base_root)
    calc = candidate_root.find(".//column[@name='[Calculation_1]']/calculation")
    calc.set("formula", "SUM([Sales]) * 1.1")
    candidate = _parse(candidate_root)

    diff = compute_diff(published, candidate)
    calcs_group = next(g for g in diff.groups if g.key == "calcs")
    change_item = next(i for i in calcs_group.items if i.op == "change")
    assert change_item.before == "SUM([Sales])"
    assert change_item.after == "SUM([Sales]) * 1.1"


def test_parameter_value_change_flags_params_group(base_root):
    published = _parse(base_root)

    candidate_root = copy.deepcopy(base_root)
    param_calc = candidate_root.find(".//datasource[@name='Parameters']/column/calculation")
    param_calc.set("formula", "20")
    candidate = _parse(candidate_root)

    diff = compute_diff(published, candidate)
    params_group = next(g for g in diff.groups if g.key == "params")
    change_item = next(i for i in params_group.items if i.op == "change")
    value_part = next(p for p in change_item.parts if p["attr"] == "value")
    assert value_part == {"attr": "value", "before": "10", "after": "20"}

    impact = classify_custom_view_impact(published, candidate, diff)
    assert any(f["category"] == "Parameters" and f["severity"] == "Medium" for f in impact["findings"])


def test_live_connection_change_flags_conns_group(base_root):
    published = _parse(base_root)

    candidate_root = copy.deepcopy(base_root)
    conn = candidate_root.find(".//named-connection/connection[@class='postgres']")
    conn.set("server", "db2.example.com")
    conn.set("dbname", "orders_db_v2")
    conn.set("username", "svc_user2")
    candidate = _parse(candidate_root)

    diff = compute_diff(published, candidate)
    conns_group = next(g for g in diff.groups if g.key == "conns")
    change_item = next(i for i in conns_group.items if i.op == "change")
    parts_by_attr = {p["attr"]: p for p in change_item.parts}
    assert parts_by_attr["server"] == {"attr": "server", "before": "db.example.com", "after": "db2.example.com"}
    assert parts_by_attr["dbname"] == {"attr": "dbname", "before": "orders_db", "after": "orders_db_v2"}
    assert parts_by_attr["username"] == {"attr": "username", "before": "svc_user", "after": "svc_user2"}


def test_classify_view_impact_scopes_rename_to_its_own_view(base_root):
    """A rename of one view must not mark every other custom view as
    directly_impacted - only the view that was actually removed/renamed."""
    published = _parse(base_root)

    candidate_root = copy.deepcopy(base_root)
    ws = candidate_root.find(".//worksheet[@name='Sales Summary']")
    ws.set("name", "Sales Summary v2")
    candidate = _parse(candidate_root)

    diff = compute_diff(published, candidate)
    impact = classify_custom_view_impact(published, candidate, diff)
    assert impact["classification"] == "directly_impacted"

    renamed_view = classify_view_impact("Sales Summary", published, candidate, diff, impact["classification"])
    assert renamed_view == "directly_impacted"

    unrelated_view = classify_view_impact("Overview", published, candidate, diff, impact["classification"])
    assert unrelated_view == "potentially_impacted"


def test_parameters_datasource_excluded_from_fields(base_root):
    struct = _parse(base_root)
    assert "[Parameter 1]" not in struct.fields
    assert "[Parameter 1]" in struct.parameters
    assert struct.parameters["[Parameter 1]"] == {"caption": "Top N", "datatype": "integer", "value": "10"}


@pytest.mark.parametrize("ref,expected", [
    ("[federated.abc123].[Sales]", "[Sales]"),
    ("[federated.XYZ_789].[Region]", "[Region]"),
    ("[Region]", "[Region]"),
    ("", ""),
    (None, None),
])
def test_normalize_column_ref(ref, expected):
    assert _normalize_column_ref(ref) == expected


@pytest.mark.parametrize("value,expected", [
    (None, "(none)"),
    (True, "yes"),
    (False, "no"),
    ({"a": 1, "b": 2}, "a=1, b=2"),
    ([], "(none)"),
    (["x", "y"], "x, y"),
    ([{"encoding": "color", "field": "[Region]"}], "color: [Region]"),
    ([{"field": "[Region]", "direction": "ASC"}], "[Region] ASC"),
    (5, "5"),
])
def test_fmt(value, expected):
    assert _fmt(value) == expected


@pytest.mark.parametrize("formula,expected", [
    (None, set()),
    ("", set()),
    ("10", set()),
    ("SUM([Sales])", {"[Sales]"}),
    ("SUM([Sales]) + LEN([Region])", {"[Sales]", "[Region]"}),
])
def test_referenced_fields(formula, expected):
    assert _referenced_fields(formula) == expected


def test_field_role_change_flags_medium_finding(base_root):
    published = _parse(base_root)

    candidate_root = copy.deepcopy(base_root)
    region_col = candidate_root.find(".//column[@name='[Region]']")
    region_col.set("role", "measure")
    candidate = _parse(candidate_root)

    diff = compute_diff(published, candidate)
    impact = classify_custom_view_impact(published, candidate, diff)
    assert any(
        f["category"] == "Fields" and f["severity"] == "Medium" and "role" in f["title"]
        for f in impact["findings"]
    )


def test_filter_card_removed_flags_finding(base_root):
    published = _parse(base_root)

    candidate_root = copy.deepcopy(base_root)
    view = candidate_root.find(".//worksheet[@name='Sales Summary']/table/view")
    filt = view.find("./filter")
    view.remove(filt)
    candidate = _parse(candidate_root)

    diff = compute_diff(published, candidate)
    impact = classify_custom_view_impact(published, candidate, diff)

    filter_findings = [f for f in impact["findings"] if f["category"] == "Filters"]
    assert len(filter_findings) == 1
    assert filter_findings[0]["severity"] == "Medium"
    assert "removed" in filter_findings[0]["title"]


def test_new_filter_added_flags_finding(base_root):
    published = _parse(base_root)

    candidate_root = copy.deepcopy(base_root)
    view = candidate_root.find(".//worksheet[@name='Sales Summary']/table/view")
    filt = ET.SubElement(view, "filter", {"class": "categorical", "column": "[federated.0abc123].[Calculation_1]"})
    ET.SubElement(filt, "groupfilter", {"function": "member", "level": "[Calculation_1]", "member": "100"})
    candidate = _parse(candidate_root)

    diff = compute_diff(published, candidate)
    impact = classify_custom_view_impact(published, candidate, diff)

    assert any(
        f["category"] == "Filters" and f["severity"] == "Medium" and "New filter added" in f["title"]
        for f in impact["findings"]
    )


def test_sort_order_change_flags_low_finding(base_root):
    published = _parse(base_root)

    candidate_root = copy.deepcopy(base_root)
    ws = candidate_root.find(".//worksheet[@name='Sales Summary']")
    view = ws.find("./table/view")
    ET.SubElement(view, "sort", {"column": "[federated.0abc123].[Region]", "direction": "ASC", "class": "computed"})
    candidate = _parse(candidate_root)

    diff = compute_diff(published, candidate)
    impact = classify_custom_view_impact(published, candidate, diff)

    assert any(
        f["category"] == "Sorts" and f["severity"] == "Low" and "Sort order changed" in f["title"]
        for f in impact["findings"]
    )


def test_encoding_change_flags_medium_finding(base_root):
    published = _parse(base_root)

    candidate_root = copy.deepcopy(base_root)
    ws = candidate_root.find(".//worksheet[@name='Sales Summary']")
    view = ws.find("./table/view")
    encodings = ET.SubElement(view, "encodings")
    ET.SubElement(encodings, "color", {"column": "[federated.0abc123].[Region]"})
    candidate = _parse(candidate_root)

    diff = compute_diff(published, candidate)
    impact = classify_custom_view_impact(published, candidate, diff)

    assert any(
        f["category"] == "Encodings" and f["severity"] == "Medium" and "Shelf/encoding pills changed" in f["title"]
        for f in impact["findings"]
    )


def test_calc_referenced_fields_changed_flags_finding(base_root):
    published = _parse(base_root)

    candidate_root = copy.deepcopy(base_root)
    calc = candidate_root.find(".//column[@name='[Calculation_1]']/calculation")
    calc.set("formula", "SUM([Sales]) + LEN([Region])")
    candidate = _parse(candidate_root)

    diff = compute_diff(published, candidate)
    impact = classify_custom_view_impact(published, candidate, diff)

    calc_findings = [f for f in impact["findings"] if f["category"] == "Calculations"]
    assert len(calc_findings) == 1
    assert calc_findings[0]["severity"] == "Medium"
    assert "[Region]" in calc_findings[0]["detail"]


def test_calc_formula_edit_same_fields_no_referenced_field_finding(base_root):
    published = _parse(base_root)

    candidate_root = copy.deepcopy(base_root)
    calc = candidate_root.find(".//column[@name='[Calculation_1]']/calculation")
    calc.set("formula", "SUM([Sales]) * 1.1")
    candidate = _parse(candidate_root)

    diff = compute_diff(published, candidate)
    calcs_group = next(g for g in diff.groups if g.key == "calcs")
    change_item = next(i for i in calcs_group.items if i.op == "change")
    assert change_item.before == "SUM([Sales])"
    assert change_item.after == "SUM([Sales]) * 1.1"

    impact = classify_custom_view_impact(published, candidate, diff)
    assert not any(f["category"] == "Calculations" for f in impact["findings"])
