"""
==============================================
 요세미티 캠핑장 빈자리 모니터링 스크립트 v4
 - 요세미티 내 모든 캠핑장 체크
 - 6/22-25 전체 + 1박씩(22-23, 23-24, 24-25)
 - 5분마다 체크
 - Recreation.gov → Gmail 이메일 알림
==============================================
"""

import requests
import smtplib
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta

# =============================================
# ⚙️  설정
# =============================================
CONFIG = {
    "gmail_sender":   "sungmokbyun@gmail.com",
    "gmail_password": "lmyevnmuhkwpdczs",
    "notify_email":   "sungmokbyun@gmail.com",
    "check_interval_seconds": 300,  # 5분마다 체크
}

# 체크할 날짜 조합
DATE_RANGES = [
    {"start": "2026-06-22", "end": "2026-06-25", "label": "3박 전체 (6/22~25)"},
    {"start": "2026-06-22", "end": "2026-06-23", "label": "1박 (6/22~23)"},
    {"start": "2026-06-23", "end": "2026-06-24", "label": "1박 (6/23~24)"},
    {"start": "2026-06-24", "end": "2026-06-25", "label": "1박 (6/24~25)"},
]

# 요세미티 내 모든 캠핑장
CAMPGROUNDS = [
    {"id": "232447",   "name": "Upper Pines",      "rv": True},
    {"id": "232450",   "name": "North Pines",       "rv": True},
    {"id": "232449",   "name": "Lower Pines",       "rv": True},
    {"id": "232451",   "name": "Hodgdon Meadow",    "rv": True},
    {"id": "232452",   "name": "Crane Flat",        "rv": True},
    {"id": "232446",   "name": "Wawona",            "rv": True},
    {"id": "232448",   "name": "Tuolumne Meadows",  "rv": True},
    {"id": "10083567", "name": "White Wolf",        "rv": True},
    {"id": "10083831", "name": "Porcupine Flat",   "rv": False},
    {"id": "232453",   "name": "Bridalveil Creek",  "rv": False},
]
# =============================================


def check_availability(campground_id, start_date, end_date):
    months_to_check = set()
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end   = datetime.strptime(end_date,   "%Y-%m-%d")
    current = start
    while current <= end:
        months_to_check.add(current.strftime("%Y-%m"))
        current += timedelta(days=1)

    all_availabilities = {}

    for month in sorted(months_to_check):
        url = f"https://www.recreation.gov/api/camps/availability/campground/{campground_id}/month"
        params = {"start_date": f"{month}-01T00:00:00.000Z"}
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

        try:
            response = requests.get(url, params=params, headers=headers, timeout=15)
            response.raise_for_status()
            data = response.json()
        except Exception as e:
            return None, str(e)

        for site_id, site_info in data.get("campsites", {}).items():
            if site_id not in all_availabilities:
                all_availabilities[site_id] = {"avail": {}}
            all_availabilities[site_id]["avail"].update(
                site_info.get("availabilities", {})
            )

    needed_dates = []
    current = start
    while current < end:
        needed_dates.append(current.strftime("%Y-%m-%dT00:00:00Z"))
        current += timedelta(days=1)

    available_sites = []
    for site_id, site_data in all_availabilities.items():
        if all(site_data["avail"].get(d) == "Available" for d in needed_dates):
            available_sites.append(site_id)

    return available_sites, None


def send_email(results):
    sender   = CONFIG["gmail_sender"]
    password = CONFIG["gmail_password"]
    receiver = CONFIG["notify_email"]

    subject = f"🏕️ 요세미티 빈자리 발견! ({datetime.now().strftime('%m/%d %H:%M')})"

    rows = ""
    for r in results:
        booking_url = f"https://www.recreation.gov/camping/campgrounds/{r['camp_id']}"
        rv_badge = "🚐 RV가능" if r["rv"] else "⛺ 텐트전용"
        rows += f"""
        <tr>
            <td style="padding:10px;border-bottom:1px solid #eee">
                <b>{r['camp_name']}</b><br>
                <span style="font-size:12px;color:#888">{rv_badge}</span>
            </td>
            <td style="padding:10px;border-bottom:1px solid #eee">{r['label']}</td>
            <td style="padding:10px;border-bottom:1px solid #eee;color:#2e7d32;font-weight:bold">{r['count']}개</td>
            <td style="padding:10px;border-bottom:1px solid #eee">
                <a href="{booking_url}" style="background:#2e7d32;color:white;padding:6px 14px;
                text-decoration:none;border-radius:4px;font-size:13px;">예약하기 →</a>
            </td>
        </tr>"""

    body = f"""
    <html><body style="font-family:sans-serif;max-width:600px">
    <h2 style="color:#2e7d32">🏕️ 요세미티 캠핑장 빈자리 발견!</h2>
    <table style="border-collapse:collapse;width:100%;margin-top:16px">
        <tr style="background:#f5f5f5">
            <th style="padding:10px;text-align:left">캠핑장</th>
            <th style="padding:10px;text-align:left">날짜</th>
            <th style="padding:10px;text-align:left">빈자리</th>
            <th style="padding:10px;text-align:left">예약</th>
        </tr>
        {rows}
    </table>
    <br>
    <p style="color:#e53935;font-weight:bold">⚡ 빈자리는 금방 사라집니다! 빠르게 예약하세요!</p>
    <p style="color:gray;font-size:12px">발견 시각: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
    </body></html>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = sender
    msg["To"]      = receiver
    msg.attach(MIMEText(body, "html"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender, password)
            server.sendmail(sender, receiver, msg.as_string())
        print(f"  ✅ 이메일 발송 완료! → {receiver}")
        return True
    except Exception as e:
        print(f"  ❌ 이메일 발송 실패: {e}")
        return False


def main():
    total = len(CAMPGROUNDS) * len(DATE_RANGES)
    print("=" * 60)
    print("  요세미티 캠핑장 빈자리 모니터링 v4 시작!")
    print(f"  캠핑장 {len(CAMPGROUNDS)}개 × 날짜 {len(DATE_RANGES)}가지 = 총 {total}가지 체크")
    print(f"  체크 날짜: 6/22~25 전체 + 1박씩")
    print(f"  체크 주기: 5분마다")
    print("=" * 60)

    notified = set()

    while True:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"\n🔍 [{now}] 체크 시작...")
        print("-" * 60)

        found_results = []

        for camp in CAMPGROUNDS:
            for dr in DATE_RANGES:
                key = f"{camp['id']}_{dr['start']}_{dr['end']}"
                if key in notified:
                    continue

                sites, error = check_availability(camp["id"], dr["start"], dr["end"])

                if error:
                    print(f"  ⚠️  {camp['name']} [{dr['label']}] 오류")
                elif sites:
                    print(f"  🎉 {camp['name']} [{dr['label']}] → {len(sites)}개 빈자리!")
                    found_results.append({
                        "camp_id":   camp["id"],
                        "camp_name": camp["name"],
                        "rv":        camp["rv"],
                        "label":     dr["label"],
                        "count":     len(sites),
                    })
                    notified.add(key)
                else:
                    print(f"  ❌ {camp['name']} [{dr['label']}] 없음")

                time.sleep(0.5)

        if found_results:
            print(f"\n📧 {len(found_results)}건 빈자리! 이메일 발송 중...")
            send_email(found_results)
        else:
            print("\n  현재 모든 캠핑장 빈자리 없음.")

        next_check = datetime.fromtimestamp(
            time.time() + CONFIG["check_interval_seconds"]
        ).strftime("%H:%M:%S")
        print(f"\n⏰ 다음 체크: {next_check} (Ctrl+C로 종료)")
        time.sleep(CONFIG["check_interval_seconds"])


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n모니터링 종료.")