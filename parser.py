"""
parser.py - HTML 파싱 및 데이터 추출
"""

from bs4 import BeautifulSoup


def parse_job_cards(html_source):
    """HTML에서 채용공고 카드를 파싱하여 리스트로 반환"""
    soup = BeautifulSoup(html_source, "html.parser")
    cards = soup.find_all("div", attrs={"data-sentry-component": "CardJob"})

    print(f"  발견된 카드 수: {len(cards)}")
    jobs = []

    for i, card in enumerate(cards, 1):
        try:
            job = extract_card_data(card)
            jobs.append(job)
            print(f"  [{i}] {job['company']} - {job['title']}")
        except Exception as e:
            print(f"  [{i}] 파싱 실패: {e}")

    return jobs


def extract_card_data(card):
    """개별 카드에서 전체 데이터 추출"""
    job = {}

    # 1) 공고 제목
    title_el = card.select_one('[class*="Typography_variant_size18"]')
    job["title"] = title_el.get_text(strip=True) if title_el else ""

    # 2) 회사명
    company_el = card.select_one('[class*="Typography_variant_size16"]')
    job["company"] = company_el.get_text(strip=True) if company_el else ""

    # 3) 근무지역
    location_chip = card.select_one('[class*="emoji--basicemoji-place2"]')
    if location_chip:
        chip_parent = location_chip.find_parent(
            attrs={"data-sentry-component": "GrayChip"}
        )
        if chip_parent:
            loc_text = chip_parent.select_one('[class*="Typography_variant_size14"]')
            job["location"] = loc_text.get_text(strip=True) if loc_text else ""
        else:
            job["location"] = ""
    else:
        job["location"] = ""

    # 4) 경력 조건
    exp_el = card.select_one(
        '[class*="Typography_variant_size13"][class*="flex-shrink_0"]'
    )
    job["experience"] = exp_el.get_text(strip=True) if exp_el else ""

    # 5) 상세 URL
    link_el = card.select_one('a[href*="/Recruit/GI_Read/"]')
    if link_el:
        href = link_el.get("href", "")
        if href.startswith("/"):
            href = "https://www.jobkorea.co.kr" + href
        job["detail_url"] = href
    else:
        job["detail_url"] = ""

    # 6) 업종 + 직무 (briefcase 아이콘 옆 GrayChip)
    industry_chip = card.select_one('[class*="emoji--basicemoji-briefcase"]')
    if industry_chip:
        chip_parent = industry_chip.find_parent(
            attrs={"data-sentry-component": "GrayChip"}
        )
        if chip_parent:
            text = chip_parent.select_one('[class*="Typography_variant_size14"]')
            raw = text.get_text(strip=True) if text else ""
            parts = [p.strip() for p in raw.split(",")]
            job["industry"] = parts[0] if parts else ""
            job["job_category"] = ", ".join(parts[1:]) if len(parts) > 1 else ""
        else:
            job["industry"] = ""
            job["job_category"] = ""
    else:
        job["industry"] = ""
        job["job_category"] = ""

    # 7) 급여
    salary_chip = card.select_one('[class*="emoji--basicemoji-money_bill"]')
    if salary_chip:
        chip_parent = salary_chip.find_parent(
            attrs={"data-sentry-component": "GrayChip"}
        )
        if chip_parent:
            sal_text = chip_parent.select_one('[class*="Typography_variant_size14"]')
            job["salary"] = sal_text.get_text(strip=True) if sal_text else ""
        else:
            job["salary"] = ""
    else:
        job["salary"] = ""

    # 8) 뱃지
    badge_el = card.select_one('[data-sentry-component="BadgeItem"] span')
    job["badge"] = badge_el.get_text(strip=True) if badge_el else ""

    # 9) 지원 방식
    apply_btn = card.select_one(
        '[class*="_16czznu"] [class*="Typography_variant_size12"]'
    )
    job["apply_type"] = apply_btn.get_text(strip=True) if apply_btn else ""

    # 10) 등록일, 마감일
    date_spans = card.select(
        '[class*="Typography_variant_size13"][class*="Typography_weight_regular"]'
    )
    dates = [
        s.get_text(strip=True) for s in date_spans
        if "등록" in s.get_text() or "마감" in s.get_text() or "채용" in s.get_text()
    ]
    job["posted_date"] = dates[0] if len(dates) > 0 else ""
    job["deadline"] = dates[1] if len(dates) > 1 else ""

    # 11) 복리후생
    benefit_spans = [s.get_text(strip=True) for s in date_spans]
    benefit_texts = [
        t for t in benefit_spans
        if "지원" in t or "제도" in t or "보험" in t
    ]
    job["benefits"] = ", ".join(benefit_texts) if benefit_texts else ""

    return job
