"""PWA version notice detects Home and canonical CSS updates without forced reload."""
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
class PwaStyleUpdateDetectionTests(unittest.TestCase):
 def test_both_styles_tracked_and_user_controls_refresh(self):
  html=(ROOT/"index.html").read_text(encoding="utf-8")
  script=html.split('const trackedStyles = ',1)[1].split('</script>',1)[0]
  for name in ('vestra-iphone-canonical-scale.css','vestra-home-first-look-order.css','publishedVersions','installedVersions','vestraUiUpdateNotice'):
   self.assertIn(name,script)
  self.assertIn("refresh.addEventListener('click'",script)
  self.assertNotIn("window.location.reload()",script)
if __name__=='__main__':unittest.main()
