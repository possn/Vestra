from pathlib import Path
import re
import unittest

HTML=(Path(__file__).resolve().parents[1]/"index.html").read_text(encoding="utf-8")

class SidebarCanonicalNavigationTest(unittest.TestCase):
    def test_same_names_for_primary_tabs_and_drawer(self):
        for key,label in [("dashboard","Início"),("assets","Carteira"),("market","Mercado"),("cashflow","Fluxos"),("settings","Mais")]:
            self.assertRegex(HTML,rf'data-view="{key}"[^>]*>.*?<span>{re.escape(label)}</span>')
        self.assertNotIn('<div class="sidebar__sub">v4.0</div>',HTML)

    def test_secondary_functions_remain_available(self):
        for key in ['data-view="dividends"','data-view="analysis"','id="sideBtnExportJSON"','id="sideBtnSnapshot"']:
            self.assertIn(key,HTML)
