"""컴시간 변경 수업의 실제 응답 형식을 검증한다. 네트워크/설정 변경 없음."""
import unittest

from fetch_timetable import _decode_week


class ChangedLessons(unittest.TestCase):
    def decode(self, row, original=None):
        subjects = [""] * 33
        teachers = [""] * 29
        for index, name in {22: "고화A", 3: "심수A", 17: "고물A",
                            11: "공영", 32: "지구", 13: "통사A"}.items():
            subjects[index] = name
        for index, name in {20: "이병*", 3: "김완*", 15: "김병*",
                            10: "양수*", 28: "변난*", 12: "문지*"}.items():
            teachers[index] = name
        raw = {
            "자료1": [None, [None, [None, row, [0], [0], [0], [0]]]],
            "자료2": teachers,
            "자료3": subjects,
            "일과시간": ["1(08:50)", "2(09:50)", "3(10:50)",
                       "4(11:45)", "5(13:35)", "6(14:35)", "7(15:30)"],
        }
        boot = {"day_key": "1", "teacher_key": "2", "subject_key": "3"}
        if original is not None:
            raw["자료4"] = [None, [None, [None, original, [0], [0], [0], [0]]]]
            boot["original_key"] = "4"
            raw["변경알림"] = 0
        return _decode_week(raw, boot, 1, 1)["days"][0]

    def test_original_comparison_when_change_alerts_are_disabled(self):
        periods = self.decode([2, 22020, 17015], original=[2, 22020, 13012])
        self.assertEqual([p["changed"] for p in periods], [False, True])

    def test_monday_changed_fourth_and_seventh_lessons(self):
        periods = self.decode([7, 22020, 22020, 3003, ">17015",
                               11010, 32028, ">13012"])
        self.assertEqual([p["subject"] for p in periods],
                         ["고화A", "고화A", "심수A", "고물A", "공영", "지구", "통사A"])
        self.assertEqual((periods[3]["teacher"], periods[6]["teacher"]),
                         ("김병*", "문지*"))
        self.assertEqual(periods[6]["time"], "15:30")
        self.assertEqual([p["period"] for p in periods if p["changed"]], [4, 7])

    def test_numeric_strings_and_empty_changed_cells(self):
        periods = self.decode([4, "22020", ">0", ">17015", 0])
        self.assertEqual([p["subject"] for p in periods], ["고화A", "", "고물A"])
        self.assertEqual(periods[1]["teacher"], "")
        self.assertEqual(self.decode([2, 0, ">0"]), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
