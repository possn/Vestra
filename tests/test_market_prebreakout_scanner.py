from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
SCANNER=(ROOT/"market-opportunities.js").read_text(encoding="utf-8")
LENSES=(ROOT/"market-opportunity-lenses.js").read_text(encoding="utf-8")
LOADER=(ROOT/"market-static-universe.js").read_text(encoding="utf-8")

class PreBreakoutContractTests(unittest.TestCase):
    def test_discoverable_as_separate_market_tab(self):
        self.assertIn('data-vestra-lens="breakout"',LENSES)
        self.assertIn('Pré-breakout',LENSES)
        self.assertIn("if(lens==='breakout')",SCANNER)
        self.assertIn("breakoutSetup",SCANNER)
        self.assertIn("market-opportunity-lenses.js?v=3.2",LOADER)

    def test_requires_real_history_and_aligned_upward_moving_averages(self):
        self.assertIn('if(bars.length<220)return null',SCANNER)
        self.assertIn('last<219)return null',SCANNER)
        self.assertIn('if(ageDays>7||ageDays< -1)return null',SCANNER)
        self.assertIn("'ETF','FUND','MUTUALFUND','CRYPTO'",SCANNER)
        self.assertIn('current>sma150&&sma50>sma200&&slopes.every(x=>x>0)',SCANNER)
        self.assertIn('prior50<=prior200',SCANNER)
        self.assertIn('width<oldWidth*.8&&width<=.22',SCANNER)
        self.assertIn('if(distance>8||distance<0)return null',SCANNER)

    def test_volume_and_breakout_remain_source_confirmed(self):
        self.assertIn('volumes.length>=30',SCANNER)
        self.assertIn('lastVolume>=averageVolume*1.5',SCANNER)
        self.assertIn('const volumeDry=baseline!=null&&quiet!=null&&quiet<=baseline*.80',SCANNER)
        self.assertIn("const stage=distance<=4&&volumeDry?'pré-breakout':'compressão'",SCANNER)
        self.assertIn('(volumeDry?7:0)',SCANNER)
        self.assertNotIn('(volumeConfirmed?7:0)',SCANNER)
        self.assertIn('if((bars[last].high??current)>resistance*1.005)return null',SCANNER)
        self.assertIn("!['compressão','pré-breakout'].includes(item.stage)",SCANNER)
        self.assertNotIn("const stage=breakout?'confirmado'",SCANNER)
        self.assertIn('Sem secagem de volume verificada',SCANNER)
        self.assertIn('Volume a secar; confirmação pendente',SCANNER)
        self.assertIn('Setup técnico, não previsão',SCANNER)

if __name__=='__main__':
    unittest.main()
