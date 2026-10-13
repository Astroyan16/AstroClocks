import tkinter as tk
import unittest
from types import SimpleNamespace
from urllib.parse import parse_qs, urlparse
from unittest.mock import Mock, patch

from astroclocks.app_object_search import (
    _link_target_sources, _set_result_text, _target_catalog_links,
)


class CatalogLinksTests(unittest.TestCase):
    def test_wds_identifier_keeps_plus_sign_and_cache_has_same_destination(self):
        for source in ("WDS", "WDS Cache", "WDS bundled"):
            links = _target_catalog_links(dict(source=source, wds="19387+2750"))
            self.assertEqual(links[0][0], "WDS")
            query = parse_qs(urlparse(links[0][1]).query)
            self.assertEqual(query["WDS"], ["19387+2750"])
            self.assertEqual(query["-source"], ["B/wds/wds"])

    def test_simbad_uses_original_identifier_even_for_merged_catalog(self):
        links = _target_catalog_links(dict(source="BSC local + SIMBAD/CDS",
                                           source_id="[ABC] +12 34", name="Pretty label"))
        self.assertEqual(links[0][0], "SIMBAD/CDS")
        self.assertEqual(parse_qs(urlparse(links[0][1]).query)["Ident"], ["[ABC] +12 34"])

    def test_missing_identifiers_open_catalog_pages_and_local_sources_have_no_link(self):
        self.assertEqual(len(_target_catalog_links(dict(source="WDS"))), 1)
        self.assertEqual(_target_catalog_links(dict(source="SIMBAD/CDS"))[0][1],
                         "https://simbad.cds.unistra.fr/simbad/")
        self.assertEqual(_target_catalog_links(dict(source="Featured")), [])

    def test_links_only_tag_source_line_and_are_removed_with_next_message(self):
        root = tk.Tk()
        root.withdraw()
        try:
            widget = tk.Text(root)
            app = SimpleNamespace(result_text=widget, text="#eeeeee", accent="#44ccee")
            _set_result_text(app, "WDS target\nMagnitude: 2\nData source: WDS")
            _link_target_sources(app, dict(source="WDS", wds="19387+2750"))
            ranges = widget.tag_ranges("catalog-link-0")
            self.assertEqual(len(ranges), 2)
            self.assertEqual(str(ranges[0]).split(".")[0], "3")
            self.assertEqual(widget.get(*ranges), "WDS")
            self.assertEqual(widget.tag_cget("catalog-link-0", "underline"), "1")
            _set_result_text(app, "Search failed")
            self.assertNotIn("catalog-link-0", widget.tag_names())
            self.assertEqual(widget.cget("state"), tk.DISABLED)
        finally:
            root.destroy()

    def test_click_opens_associated_url_and_hover_changes_cursor(self):
        widget = Mock()
        widget.index.return_value = "3.0"
        widget.search.return_value = "3.13"
        app = SimpleNamespace(result_text=widget, accent="#44ccee")
        _link_target_sources(app, dict(source="SIMBAD/CDS", source_id="M 31"))
        bindings = {call.args[1]: call.args[2] for call in widget.tag_bind.call_args_list}
        with patch("astroclocks.app_object_search.webbrowser.open_new_tab") as browser:
            bindings["<Button-1>"](None)
            self.assertEqual(parse_qs(urlparse(browser.call_args.args[0]).query)["Ident"], ["M 31"])
        bindings["<Enter>"](None)
        widget.config.assert_called_with(cursor="hand2")
        bindings["<Leave>"](None)
        widget.config.assert_called_with(cursor="xterm")
