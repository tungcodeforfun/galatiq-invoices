"""Unit tests for the deterministic tools: item resolution, stock aggregation, totals, duplicates and revisions."""

from __future__ import annotations

from conftest import make_invoice

from invoice_agents.tools import ToolBox, content_hash, number_key, resolve_item, text_key

CATALOG = {"WidgetA": {}, "WidgetB": {}, "GadgetX": {}}


def codes(box: ToolBox) -> list[str]:
    return [f.code for f in box.finding_list()]


def test_resolve_item_normalizes_spacing_and_parenthetical_notes():
    assert resolve_item("Widget A", CATALOG) == ("WidgetA", "normalized")
    assert resolve_item("WidgetA (rush order)", CATALOG) == ("WidgetA", "normalized")
    assert resolve_item("GadgetX", CATALOG) == ("GadgetX", "exact")


def test_resolve_item_never_guesses_a_near_miss():
    assert resolve_item("WidgetC", CATALOG) == (None, "none")


def test_unknown_item_is_a_finding(store, policy):
    box = ToolBox(make_invoice([("SuperGizmo", 12, 400)]), store, policy)
    assert box.resolve_item(1)["item"] is None
    assert codes(box) == ["UNKNOWN_ITEM"]


def test_stock_is_summed_across_repeated_lines(store, policy):
    invoice = make_invoice([("WidgetA", 10, 250), ("WidgetB", 1, 500), ("WidgetA", 4, 240), ("WidgetA", 2, 250)])
    box = ToolBox(invoice, store, policy)
    result = box.check_stock("WidgetA")
    assert result["requested"] == 16 and result["in_stock"] == 15 and result["lines"] == [1, 3, 4]
    assert codes(box) == ["STOCK_EXCEEDED"]


def test_stock_exactly_at_limit_passes(store, policy):
    box = ToolBox(make_invoice([("GadgetX", 5, 750)]), store, policy)
    assert box.check_stock("GadgetX")["ok"]
    assert codes(box) == []


def test_zero_stock_item_is_a_fraud_signal(store, policy):
    box = ToolBox(make_invoice([("FakeItem", 100, 1000)]), store, policy)
    box.check_stock("FakeItem")
    assert set(codes(box)) == {"STOCK_EXCEEDED", "FRAUD_SIGNALS"}


def test_totals_include_tax_and_shipping(store, policy):
    invoice = make_invoice([("WidgetA", 8, 250), ("WidgetB", 4, 500)], total=4485.00, tax=335.00, shipping=150.00)
    box = ToolBox(invoice, store, policy)
    assert box.check_totals()["ok"]


def test_total_off_by_fifty_is_flagged_with_the_difference(store, policy):
    invoice = make_invoice([("WidgetA", 2, 250)], total=585.00, subtotal=500.00, tax=35.00)
    box = ToolBox(invoice, store, policy)
    assert not box.check_totals()["ok"]
    assert box.finding_list()[0].evidence["difference"] == 50.0


def test_total_within_one_cent_passes(store, policy):
    box = ToolBox(make_invoice([("WidgetA", 3, 250)], total=750.01), store, policy)
    assert box.check_totals()["ok"]


def test_price_variance_beyond_tolerance_warns(store, policy):
    box = ToolBox(make_invoice([("WidgetA (rush order)", 4, 300)]), store, policy)
    assert box.check_price(1)["variance_pct"] == 20.0
    assert codes(box) == ["PRICE_VARIANCE"]


def test_invoice_number_formats_share_one_key():
    assert number_key("INV-1002") == number_key("INV 1002") == number_key("1002") == "1002"


def record(store, invoice, status="PAID"):
    store.record_invoice(
        number=invoice.invoice_number, number_key=number_key(invoice.invoice_number), vendor=invoice.vendor,
        vendor_key=text_key(invoice.vendor), content_hash=content_hash(invoice, store.catalog()), status=status,
        total=invoice.total, source_file="x", run_id="r",
    )


def test_same_content_under_a_new_number_is_a_duplicate(store, policy):
    original = make_invoice([("WidgetA", 10, 250), ("WidgetB", 5, 500)], number="INV-1001")
    record(store, original)
    resubmitted = make_invoice([("Widget A", 10, 250), ("WidgetB", 5, 500)], number="INV-1101")
    box = ToolBox(resubmitted, store, policy)
    assert box.check_duplicate()["result"] == "duplicate"
    assert codes(box) == ["DUPLICATE"]


def test_changed_invoice_under_a_decided_number_is_a_revision_conflict(store, policy):
    record(store, make_invoice([("WidgetA", 3, 250), ("WidgetB", 2, 500)], total=1890.0, number="INV-1004"))
    revised = make_invoice([("WidgetA", 3, 250), ("WidgetB", 2, 500), ("GadgetX", 5, 750)], total=5940.0,
                           number="INV-1004")
    box = ToolBox(revised, store, policy)
    assert box.check_duplicate() == {"result": "revision_conflict", "prior_total": 1890.0, "prior_status": "PAID",
                                     "delta": 4050.0}


def test_failed_payment_does_not_count_as_a_prior_decision(store, policy):
    invoice = make_invoice([("WidgetA", 1, 250)])
    record(store, invoice, status="PAYMENT_FAILED")
    assert ToolBox(invoice, store, policy).check_duplicate()["result"] == "no_match"


def test_coverage_lists_every_required_check_until_run(store, policy):
    box = ToolBox(make_invoice([("WidgetA", 1, 250), ("WidgetA", 1, 250)]), store, policy)
    assert len(box.missing_checks()) == 2 + 2 + 1 + 3
    box.run_missing()
    assert box.missing_checks() == []
