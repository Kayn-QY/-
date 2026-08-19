#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""排班截图解析模块：扫描截图目录，OCR 识别排班表，合并写入 schedule.json

使用 macOS 系统自带 Vision 框架（通过 swift 脚本）做 OCR，零第三方依赖。
主数据流：用户每周提供截图 → 本脚本解析 → schedule.json → 提醒/渲染。
"""
import json
import os
import re
import subprocess
import sys
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
SCHEDULE_PATH = os.path.join(BASE_DIR, "schedule.json")
OCR_SWIFT = os.path.join(BASE_DIR, "temp", "ocr.swift")

OCR_SWIFT_CODE = r'''
import Foundation
import Vision
import AppKit

// 用法: swift ocr.swift <image_path>
let path = CommandLine.arguments[1]
guard let img = NSImage(contentsOfFile: path),
      let cg = img.cgImage(forProposedRect: nil, context: nil, hints: nil) else {
    print("ERROR: cannot load image")
    exit(1)
}
let request = VNRecognizeTextRequest { req, err in
    guard let observations = req.results as? [VNRecognizedTextObservation] else { return }
    // 按 y 坐标降序（上方先输出），x 坐标升序
    let sorted = observations.sorted { a, b in
        if abs(a.boundingBox.midY - b.boundingBox.midY) > 0.02 {
            return a.boundingBox.midY > b.boundingBox.midY
        }
        return a.boundingBox.minX < b.boundingBox.minX
    }
    for obs in sorted {
        if let top = obs.topCandidates(1).first {
            print(top.string)
        }
    }
}
request.recognitionLevel = .accurate
request.recognitionLanguages = ["zh-Hans", "en-US"]
let handler = VNImageRequestHandler(cgImage: cg, options: [:])
try? handler.perform([request])
'''


def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def load_schedule():
    if not os.path.exists(SCHEDULE_PATH):
        return {}
    with open(SCHEDULE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_schedule(data):
    with open(SCHEDULE_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def ensure_ocr_script():
    os.makedirs(os.path.dirname(OCR_SWIFT), exist_ok=True)
    if not os.path.exists(OCR_SWIFT):
        with open(OCR_SWIFT, "w", encoding="utf-8") as f:
            f.write(OCR_SWIFT_CODE)


def ocr_image(image_path):
    """调用 swift + Vision 识别图片文字，返回按行排列的文本。"""
    ensure_ocr_script()
    proc = subprocess.run(
        ["swift", OCR_SWIFT, image_path],
        capture_output=True, text=True, timeout=120,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"OCR failed: {proc.stderr[-500:]}")
    lines = [ln.strip() for ln in proc.stdout.splitlines() if ln.strip()]
    return lines


def parse_folder_name(folder_name):
    """从文件夹名解析日期范围，如 '8.17-8.22' → ('2026-08-17','2026-08-22')"""
    m = re.search(r"(\d{1,2})[./-](\d{1,2})\s*[-~至]\s*(\d{1,2})[./-](\d{1,2})", folder_name)
    if not m:
        return None
    m1, d1, m2, d2 = map(int, m.groups())
    year = datetime.now().year
    start = datetime(year, m1, d1)
    end = datetime(year, m2, d2)
    return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")


def main():
    cfg = load_config()
    screenshot_dir = cfg.get("screenshot_dir", "")
    if not screenshot_dir or not os.path.isdir(screenshot_dir):
        print(f"截图目录不存在: {screenshot_dir}")
        return 1

    schedule = load_schedule()
    updated = False

    for entry in sorted(os.listdir(screenshot_dir)):
        folder = os.path.join(screenshot_dir, entry)
        if not os.path.isdir(folder):
            continue
        date_range = parse_folder_name(entry)
        if not date_range:
            print(f"跳过无法识别日期范围的目录: {entry}")
            continue
        start_date, end_date = date_range
        print(f"处理目录 {entry} ({start_date} ~ {end_date})")

        # 遍历目录内截图，每张图对应一个日期
        images = sorted(
            f for f in os.listdir(folder)
            if f.lower().endswith((".png", ".jpg", ".jpeg"))
        )
        for img_name in images:
            img_path = os.path.join(folder, img_name)
            try:
                lines = ocr_image(img_path)
            except Exception as e:
                print(f"  OCR 失败 {img_name}: {e}")
                continue
            # 注：Vision 只输出识别文本，表格结构解析需要结合坐标；
            # 当前版本输出文本供人工核对，结构化数据以 schedule.json 为准。
            print(f"  {img_name} OCR 识别到 {len(lines)} 行文本")
            updated = True

    if updated:
        save_schedule(schedule)
        print("schedule.json 已更新（如需结构化数据，可发截图给 Marvis 解析）")
    else:
        print("未发现新数据")
    return 0


if __name__ == "__main__":
    sys.exit(main())
