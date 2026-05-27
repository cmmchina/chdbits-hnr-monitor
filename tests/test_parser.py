import unittest

from hnr_monitor.config import ParserConfig
from hnr_monitor.parser import parse_hnr_records


class ParserTest(unittest.TestCase):
    def test_parse_hnr_table(self) -> None:
        html = """
        <html><body>
          <table>
            <tr><th>种子</th><th>H&R 完成时间</th><th>状态</th></tr>
            <tr>
              <td><a href="details.php?id=123">Ubuntu ISO</a></td>
              <td>12:30:00</td>
              <td>进行中</td>
            </tr>
          </table>
        </body></html>
        """
        config = ParserConfig(
            progress_columns=["H&R 完成时间"],
            name_columns=["种子"],
            status_columns=["状态"],
            torrent_id_patterns=[r"details\.php\?id=(\d+)"],
        )

        records = parse_hnr_records(html, config, "https://ptchdbits.co")

        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].key, "123")
        self.assertEqual(records[0].name, "Ubuntu ISO")
        self.assertEqual(records[0].progress_value, "12:30:00")
        self.assertEqual(records[0].status, "进行中")
        self.assertEqual(records[0].detail_url, "https://ptchdbits.co/details.php?id=123")

    def test_completion_time_is_preferred_for_chdbits_hnr_table(self) -> None:
        html = """
        <html><body>
          <table>
            <tr>
              <th>类型</th><th>标题</th><th>H&R百分比</th><th>剩余时间</th>
              <th>H&R周期</th><th>做种时间</th><th>下载时间</th><th>上传</th>
              <th>下载</th><th>分享率</th><th>完成时间</th>
            </tr>
            <tr>
              <td></td>
              <td><a href="details.php?id=123&hit=1">Private title</a></td>
              <td>14.76%</td>
              <td>18天05:15:50</td>
              <td>5天</td>
              <td>17:43:02</td>
              <td>1:43:16</td>
              <td>383.64 MB</td>
              <td>2.54 GB</td>
              <td>6.78</td>
              <td>0:44:17</td>
            </tr>
          </table>
        </body></html>
        """
        config = ParserConfig(
            progress_columns=["完成时间", "H&R百分比", "做种时间"],
            name_columns=["标题"],
            status_columns=["状态"],
            torrent_id_patterns=[r"details\.php\?id=(\d+)"],
        )

        records = parse_hnr_records(html, config, "https://ptchdbits.co")

        self.assertEqual(records[0].progress_value, "0:44:17")


if __name__ == "__main__":
    unittest.main()
