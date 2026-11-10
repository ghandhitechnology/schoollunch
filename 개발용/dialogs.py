# -*- coding: utf-8 -*-
"""메인 화면과 커스텀 에디터가 함께 쓰는 모달 대화상자.

두 화면에 거의 같은 시간표 편집 대화상자가 각각 복사돼 있었다.
여기 한 벌만 두고 호출부는 on_saved 콜백으로 각자 뒤처리를 한다.
"""
import customtkinter as ctk

import config
from ui_common import COLORS, RADIUS, SPACE, TYPE, font, mono_font

PERIOD_ROWS = 7


def _make_dialog(parent, title, size):
    dialog = ctk.CTkToplevel(parent)
    dialog.title(title)
    dialog.geometry(size)
    dialog.transient(parent)
    dialog.resizable(False, False)
    # CTkToplevel 은 생성 직후 아직 맵되지 않아 grab_set 이 실패한다.
    dialog.after(120, lambda: dialog.grab_set() if dialog.winfo_exists() else None)
    return dialog


def _footer(dialog, on_confirm, confirm_text="확인", cancel_text="취소"):
    bar = ctk.CTkFrame(dialog, fg_color="transparent")
    bar.pack(fill="x", padx=SPACE["lg"], pady=(SPACE["sm"], SPACE["lg"]), side="bottom")
    ctk.CTkButton(
        bar, text=confirm_text, command=on_confirm, width=96,
        font=font(TYPE["body"], "bold"), corner_radius=RADIUS["sm"],
        fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"],
    ).pack(side="right")
    ctk.CTkButton(
        bar, text=cancel_text, command=dialog.destroy, width=80,
        font=font(TYPE["body"]), corner_radius=RADIUS["sm"],
        fg_color="transparent", hover_color=COLORS["nav_hover"],
        text_color=COLORS["text_dim"], border_width=1, border_color=COLORS["border"],
    ).pack(side="right", padx=(0, SPACE["sm"]))
    return bar


def open_timetable_editor(parent, timetable, on_saved=None):
    """교시별 시간·과목·교사를 직접 고친다.

    timetable 은 제자리에서 수정된 뒤 캐시에 저장된다 (기존 동작 유지).
    on_saved(timetable) 로 호출부가 각자 화면을 새로 그린다.
    """
    dialog = _make_dialog(parent, "시간표 직접 편집", "520x560")

    head = ctk.CTkFrame(dialog, fg_color="transparent")
    head.pack(fill="x", padx=SPACE["lg"], pady=(SPACE["lg"], SPACE["sm"]))
    ctk.CTkLabel(head, text="시간표 직접 편집", font=font(TYPE["title"], "bold"),
                 anchor="w").pack(fill="x")
    ctk.CTkLabel(head, text="컴시간알리미 정보가 틀렸을 때 직접 고칠 수 있습니다.",
                 font=font(TYPE["caption"]), text_color=COLORS["text_dim"],
                 anchor="w").pack(fill="x", pady=(2, 0))

    body = ctk.CTkScrollableFrame(dialog, fg_color=COLORS["surface_alt"],
                                  corner_radius=RADIUS["md"])
    body.pack(fill="both", expand=True, padx=SPACE["lg"], pady=SPACE["sm"])

    header = ctk.CTkFrame(body, fg_color="transparent")
    header.pack(fill="x", pady=(0, SPACE["xs"]))
    for text, width in (("교시", 44), ("시간", 96), ("과목", 130), ("교사", 96)):
        ctk.CTkLabel(header, text=text, width=width, anchor="w",
                     font=font(TYPE["caption"], "bold"),
                     text_color=COLORS["text_dim"]).pack(side="left", padx=(0, SPACE["xs"]))

    periods = list(timetable.get("periods") or [])
    while len(periods) < PERIOD_ROWS:
        periods.append({"period": len(periods) + 1, "time": "", "subject": "", "teacher": ""})

    def entry(parent_row, value, width, placeholder=""):
        e = ctk.CTkEntry(parent_row, width=width, font=font(TYPE["body"]),
                         corner_radius=RADIUS["sm"], border_color=COLORS["border"],
                         placeholder_text=placeholder)
        if value:
            e.insert(0, value)
        e.pack(side="left", padx=(0, SPACE["xs"]))
        return e

    entries = []
    for period in periods:
        num = period.get("period", 1)
        row = ctk.CTkFrame(body, fg_color="transparent")
        row.pack(fill="x", pady=2)
        ctk.CTkLabel(row, text=f"{num}교시", width=44, anchor="w",
                     font=font(TYPE["body"])).pack(side="left", padx=(0, SPACE["xs"]))
        time_e = entry(row, period.get("time") or "", 96, "08:40")
        sub_e = entry(row, period.get("subject") or "", 130)
        tch_e = entry(row, period.get("teacher") or "", 96)
        entries.append((num, time_e, sub_e, tch_e))

    def save():
        new_periods = []
        for num, time_e, sub_e, tch_e in entries:
            time_str, sub_str, tch_str = (time_e.get().strip(), sub_e.get().strip(),
                                          tch_e.get().strip())
            if time_str or sub_str or tch_str:
                new_periods.append({"period": num, "time": time_str,
                                    "subject": sub_str, "teacher": tch_str})
        timetable["periods"] = new_periods
        timetable["_edited"] = True
        config.save_cache_entry("timetable", timetable)
        dialog.destroy()
        if on_saved:
            on_saved(timetable)

    _footer(dialog, save)
    return dialog


def open_teacher_roster(parent, on_saved=None):
    """컴시간알리미가 가린 교사 이름('김완*')을 풀기 위한 전체 명단."""
    dialog = _make_dialog(parent, "교사 명단", "440x520")

    head = ctk.CTkFrame(dialog, fg_color="transparent")
    head.pack(fill="x", padx=SPACE["lg"], pady=(SPACE["lg"], SPACE["sm"]))
    ctk.CTkLabel(head, text="교사 명단", font=font(TYPE["title"], "bold"),
                 anchor="w").pack(fill="x")
    ctk.CTkLabel(
        head,
        text="컴시간알리미는 교사 이름을 '김완*'처럼 가려서 보냅니다.\n"
             "전체 이름을 한 줄에 하나씩 적어 두면, 정확히 한 명과\n"
             "일치할 때 자동으로 전체 이름으로 바꿔 표시합니다.",
        font=font(TYPE["caption"]), text_color=COLORS["text_dim"],
        justify="left", anchor="w",
    ).pack(fill="x", pady=(2, 0))

    box = ctk.CTkTextbox(dialog, font=mono_font(TYPE["mono"]), corner_radius=RADIUS["md"],
                         border_width=1, border_color=COLORS["border"],
                         fg_color=COLORS["surface_alt"])
    box.pack(fill="both", expand=True, padx=SPACE["lg"], pady=SPACE["sm"])
    box.insert("1.0", "\n".join(config.load_config().get("teacher_names", [])))

    def save():
        names = []
        for line in box.get("1.0", "end").splitlines():
            name = line.strip()
            if name and name not in names:
                names.append(name)
        latest = config.load_config()
        latest["teacher_names"] = names
        config.save_config(latest)
        dialog.destroy()
        if on_saved:
            on_saved(names)

    _footer(dialog, save, confirm_text="저장", cancel_text="닫기")
    box.focus_set()
    return dialog
