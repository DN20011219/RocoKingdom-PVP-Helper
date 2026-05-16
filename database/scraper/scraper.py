import argparse
import json
import os
import sys
import socket
import time
from urllib.parse import urljoin, urlencode, unquote

try:
    import requests
except Exception:
    requests = None

try:
    from bs4 import BeautifulSoup
except Exception:
    BeautifulSoup = None
import re
import html as html_module
from urllib import request as urllib_request


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Referer": "https://wiki.biligame.com/rocom/",
}


def fetch(url, timeout=15, retries=3):
    """Fetch URL with retry logic for network errors"""
    for attempt in range(retries):
        try:
            if requests:
                try:
                    resp = requests.get(url, headers=HEADERS, timeout=timeout)
                    resp.raise_for_status()
                    return resp.text
                except Exception:
                    pass
            
            # fallback to urllib without system proxy detection on Windows
            req = urllib_request.Request(url, headers=HEADERS)
            opener = urllib_request.build_opener(urllib_request.ProxyHandler({}))
            with opener.open(req, timeout=timeout) as resp:
                raw = resp.read()
                try:
                    return raw.decode("utf-8")
                except Exception:
                    return raw.decode(errors="replace")
        
        except (socket.error, socket.herror, socket.gaierror, socket.timeout) as e:
            # Network-level error - retry
            if attempt < retries - 1:
                wait_time = 2 ** attempt  # exponential backoff
                print(f"  Network error (attempt {attempt+1}/{retries}): {type(e).__name__}, retrying in {wait_time}s...", flush=True)
                time.sleep(wait_time)
                continue
            else:
                raise Exception(f"Network error after {retries} retries: {e}")
        
        except Exception as e:
            # Other errors - don't retry, just raise
            raise


def save_text(text, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def save_json_atomic(data, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp_path = f"{path}.tmp.{os.getpid()}"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    try:
        os.replace(tmp_path, path)
    except PermissionError:
        fallback_path = f"{path}.partial"
        try:
            os.replace(tmp_path, fallback_path)
            print(f"  Save blocked for {path}; wrote progress to {fallback_path}", flush=True)
        except Exception:
            try:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
            except Exception:
                pass
            raise


def sanitize_filename(value):
    value = re.sub(r'[\\/:*?"<>|]+', "_", value)
    value = value.strip().strip(".")
    return value or "page"


def strip_html(fragment):
    fragment = re.sub(r'(?is)<br\s*/?>', '\n', fragment)
    fragment = re.sub(r'(?is)<[^>]+>', ' ', fragment)
    return html_module.unescape(' '.join(fragment.split()))


def extract_balanced_div_block(html_text, start_index):
    start_tag = re.search(r'(?is)<div\b[^>]*>', html_text[start_index:])
    if not start_tag:
        return ""
    start = start_index + start_tag.start()
    pos = start
    depth = 0
    tag_pattern = re.compile(r'(?is)</?div\b[^>]*>')
    while True:
        tag_match = tag_pattern.search(html_text, pos)
        if not tag_match:
            return html_text[start:]
        tag = tag_match.group(0)
        if tag.lower().startswith('</div'):
            depth -= 1
        else:
            depth += 1
        pos = tag_match.end()
        if depth == 0:
            return html_text[start:pos]


def parse_skill_block(block_html, tab_title):
    def find_text(pattern):
        match = re.search(pattern, block_html, flags=re.S | re.I)
        return strip_html(match.group(1)) if match else ""

    name = find_text(r'<div class="rocom_sprite_skillName[^>]*>(.*?)</div>')
    level = find_text(r'<div class="rocom_sprite_skill_level[^>]*>(.*?)</div>')
    power = find_text(r'<div class="rocom_sprite_skillDamage[^>]*>(.*?)</div>')
    damage = find_text(r'<div class="rocom_sprite_skill_power[^>]*>(.*?)</div>')
    if not damage:
        damage = power
    skill_type = find_text(r'<div class="rocom_sprite_skillType[^>]*>(.*?)</div>')
    content = find_text(r'<div class="rocom_sprite_skillContent[^>]*>(.*?)</div>')

    icon_title = ""
    icon_href = ""
    icon_src = ""
    # anchor href is the skill page, while img src is the actual icon asset
    icon_match = re.search(r'(?is)<a[^>]+href="([^"]+)"(?:[^>]*title="([^"]*)")?.*?<img[^>]+src="([^"]+)"', block_html)
    if icon_match:
        icon_href = icon_match.group(1)
        icon_src = icon_match.group(3)
        if icon_match.group(2):
            icon_title = html_module.unescape(icon_match.group(2)).strip()
        else:
            # fallback: try to extract text within the anchor
            a_inner = re.search(r'(?is)<a[^>]+href="[^"]+"[^>]*>(.*?)</a>', block_html)
            if a_inner:
                icon_title = strip_html(a_inner.group(1))

    attribute = ""
    # primary: img with attribute class and alt
    attr_match = re.search(r'(?is)<img[^>]*class="[^"]*rocom_sprite_skill_attr[^"]*"[^>]*alt="([^"]+)"', block_html)
    if attr_match:
        alt_text = html_module.unescape(attr_match.group(1))
        attr_name = re.search(r'属性\s*([^.\s]+)\.png', alt_text)
        attribute = attr_name.group(1) if attr_name else alt_text
    else:
        # fallback: any img alt mentioning 属性 (e.g., "图标 宠物 属性 普通.png")
        m2 = re.search(r'(?is)<img[^>]*alt="([^"]*属性[^"]*)"', block_html)
        if m2:
            alt_text = html_module.unescape(m2.group(1))
            # Strategy: extract attribute name from alt text like "图标 宠物 属性 普通.png"
            # Step 1: try 属性\s*XXX\.png pattern
            m_attr_png = re.search(r'属性\s*([^.\s]+)\.png', alt_text)
            if m_attr_png:
                attribute = m_attr_png.group(1)
            else:
                # Step 2: try 属性\s+XXX pattern (no .png)
                m_attr_space = re.search(r'属性\s+([\u4e00-\u9fff]+)', alt_text)
                if m_attr_space:
                    attribute = m_attr_space.group(1)
                else:
                    # Step 3: find last token before .png
                    m_last = re.search(r'([\u4e00-\u9fff]+)\.png', alt_text)
                    if m_last:
                        attribute = m_last.group(1)
                    # Step 4: if all fails, don't use the full alt_text, leave empty
        else:
            # fallback: check img src filename for encoded '属性_<name>.png'
            m3 = re.search(r'属性[_%20%25A-Za-z0-9\u4e00-\u9fff-]*([%0-9A-Za-z\u4e00-\u9fff]+)\.png', block_html)
            if m3:
                candidate = m3.group(1)
                try:
                    candidate = unquote(candidate)
                except Exception:
                    pass
                attribute = candidate

    if not name:
        name = icon_title

    return {
        "category": tab_title,
        "name": name,
        "icon_title": icon_title,
        "icon_href": icon_href,
        "icon_src": icon_src,
        "attribute": attribute,
        "level": level,
        "power": power,
        "damage": damage,
        "skill_type": skill_type,
        "content": content,
    }


def parse_pet_skills_from_html(html_text):
    skills = []
    skill_box_index = html_text.find('rocom_sprite_skill_tabBox')
    if skill_box_index == -1:
        return skills
    skill_container = extract_balanced_div_block(html_text, skill_box_index)
    if not skill_container:
        return skills

    tab_pattern = re.compile(r'(?is)<div\b[^>]*class="[^"]*tabbertab[^"]*"[^>]*title="([^"]+)"[^>]*>')
    tab_matches = list(tab_pattern.finditer(skill_container))
    for tab_index, tab_match in enumerate(tab_matches):
        tab_title = html_module.unescape(tab_match.group(1)).strip()
        tab_block = extract_balanced_div_block(skill_container, tab_match.start())
        if not tab_block:
            continue
        box_pattern = re.compile(r'(?is)<div\b[^>]*class="[^"]*rocom_sprite_skill_box[^"]*"[^>]*>')
        for box_index, box_match in enumerate(box_pattern.finditer(tab_block)):
            block = extract_balanced_div_block(tab_block, box_match.start())
            if not block:
                continue
            skill = parse_skill_block(block, tab_title)
            skill["index"] = box_index
            skills.append(skill)
    return skills


def parse_skill_detail_from_html(html_text):
    """Extract basic attribute and description from a skill page HTML."""
    if not html_text:
        return {}

    # Try to find explicit attribute text like "属性：火"
    attr = ""
    m = re.search(r'属性[:：]\s*([^<\n\r]+)', html_text)
    if m:
        attr = strip_html(html_module.unescape(m.group(1))).strip()
    else:
        # fallback: find img alt that mentions 属性
        m2 = re.search(r'<img[^>]*alt="([^"]*属性[^"]*)"', html_text)
        if m2:
            alt_text = html_module.unescape(m2.group(1))
            # Strategy: extract attribute name like "普通", "火", etc. from alt like "图标 宠物 属性 普通.png"
            # Step 1: try 属性\s*XXX\.png pattern
            attr_match = re.search(r'属性\s*([\u4e00-\u9fff]+)\.png', alt_text)
            if attr_match:
                attr = attr_match.group(1)
            else:
                # Step 2: try 属性\s+XXX pattern (no .png)
                attr_space = re.search(r'属性\s+([\u4e00-\u9fff]+)', alt_text)
                if attr_space:
                    attr = attr_space.group(1)
                else:
                    # Step 3: find last token before .png
                    attr_last = re.search(r'([\u4e00-\u9fff]+)\.png', alt_text)
                    if attr_last:
                        attr = attr_last.group(1)
                    # Step 4: if all fails, leave attr empty (don't use full alt_text)

    # Try to extract a short description block
    desc = ""
    dm = re.search(r'(?is)<div[^>]*class="[^"]*(rocom_skill_desc|rocom_skill_content|rocom_skill_text|skill-desc)[^"]*"[^>]*>(.*?)</div>', html_text)
    if dm:
        desc = strip_html(dm.group(2))
    else:
        pm = re.search(r'(?is)<p[^>]*class="[^"]*(rocom_skill_desc|rocom_skill_content)[^"]*"[^>]*>(.*?)</p>', html_text)
        if pm:
            desc = strip_html(pm.group(2))

    return {"attribute": attr, "description": desc}


def parse_pet_qualification_from_html(html_text):
    qualification = {
        "total": "",
        "stats": [],
        "stats_map": {},
    }
    if not html_text:
        return qualification

    start = html_text.find("rocom_sprite_info_qualification")
    if start == -1:
        return qualification
    end = html_text.find("rocom_sprite_layout_2", start)
    if end == -1:
        end = html_text.find("rocom_sprite_skill_tabBox", start)
    fragment = html_text[start:end if end != -1 else len(html_text)]

    total_match = re.search(r"资质值</p>\s*<p>(\d+)</p>", html_text)
    if total_match:
        qualification["total"] = total_match.group(1)

    for name, value in re.findall(
        r'<p class="rocom_sprite_info_qualification_name">([^<]+)</p>.*?'
        r'<p class="rocom_sprite_info_qualification_value">([^<]+)</p>',
        fragment,
        flags=re.S,
    ):
        stat_name = strip_html(html_module.unescape(name))
        stat_value = strip_html(html_module.unescape(value))
        if not stat_name or not stat_value:
            continue
        qualification["stats"].append({"name": stat_name, "value": stat_value})
        qualification["stats_map"][stat_name] = stat_value

    return qualification


def parse_pet_characteristic_from_html(html_text):
    if not html_text:
        return {}

    match = re.search(
        r'<p class="rocom_sprite_info_characteristic_title[^\"]*">(.*?)</p>\s*'
        r'<p class="rocom_sprite_info_characteristic_text[^\"]*">(.*?)</p>',
        html_text,
        flags=re.S,
    )
    if not match:
        return {}

    return {
        "name": strip_html(match.group(1)),
        "content": strip_html(match.group(2)),
    }


def group_skills_by_category(skills):
    pools = []
    index_by_category = {}
    for skill in skills:
        category = skill.get("category", "")
        if category not in index_by_category:
            index_by_category[category] = len(pools)
            pools.append({"category": category, "skills": []})
        pools[index_by_category[category]]["skills"].append(skill)
    return pools


def download_and_parse_pet_page(pet, html_dir):
    link = pet.get("link", "")
    title = unquote(link.rstrip("/").split("/")[-1]) if link else ""
    safe_title = sanitize_filename(title or pet.get("name", "page"))
    html_path = os.path.join(html_dir, f"{safe_title}.html")
    html_text = ""
    error = ""
    if os.path.exists(html_path):
        try:
            with open(html_path, "r", encoding="utf-8") as f:
                html_text = f.read()
        except Exception:
            html_text = ""
    if not html_text and link:
        try:
            html_text = fetch(link, timeout=30)
        except Exception as exc:
            error = str(exc)
    if html_text:
        save_text(html_text, html_path)
    skills = parse_pet_skills_from_html(html_text) if html_text else []
    # Enrich each skill by fetching its skill page (if available) and extracting attribute/description
    skills_html_dir = os.path.join(html_dir, "skills")
    os.makedirs(skills_html_dir, exist_ok=True)
    for skl in skills:
        try:
            href = skl.get("icon_href", "")
            if not href:
                continue
            # derive a safe filename for caching
            skill_title = unquote(href.rstrip("/").split("/")[-1]) if href else skl.get("name", "skill")
            safe_skill = sanitize_filename(skill_title or skl.get("name", "skill"))
            skill_html_path = os.path.join(skills_html_dir, f"{safe_skill}.html")
            skill_html = ""
            if os.path.exists(skill_html_path):
                try:
                    with open(skill_html_path, "r", encoding="utf-8") as sf:
                        skill_html = sf.read()
                except Exception:
                    skill_html = ""
            if not skill_html:
                # construct full url if necessary
                full_url = href
                if href.startswith("/"):
                    full_url = urljoin("https://wiki.biligame.com", href)
                try:
                    skill_html = fetch(full_url, timeout=20)
                except Exception as e:
                    skl.setdefault("skill_page_error", str(e))
                    continue
                if skill_html:
                    try:
                        save_text(skill_html, skill_html_path)
                    except Exception:
                        pass
            details = parse_skill_detail_from_html(skill_html)
            if details.get("attribute"):
                skl["attribute"] = details.get("attribute")
            if details.get("description"):
                skl["description"] = details.get("description")
            if skill_html:
                skl["skill_page"] = skill_html_path
        except Exception as e:
            skl.setdefault("skill_enrich_error", str(e))
    qualification = parse_pet_qualification_from_html(html_text) if html_text else {}
    characteristic = parse_pet_characteristic_from_html(html_text) if html_text else {}
    return {
        "title": title,
        "html_path": html_path if html_text else "",
        "skills": skills,
        "skill_pools": group_skills_by_category(skills),
        "qualification": qualification,
        "characteristic": characteristic,
        "error": error,
    }


def parse_images_and_names(html_text, base_url):
    """通用：从页面中提取图片与其邻近的名字/alt。
    返回 list[dict{name, src, src_abs}]。
    """
    if BeautifulSoup:
        soup = BeautifulSoup(html, "html.parser")
        imgs = soup.find_all("img")
        seen = set()
        out = []
        for img in imgs:
            src = img.get("src") or img.get("data-src")
            if not src:
                continue
            src_abs = urljoin(base_url, src)
            alt = img.get("alt") or img.get("title") or ""
            key = (alt, src_abs)
            if key in seen:
                continue
            seen.add(key)
            out.append({"name": alt.strip(), "src": src, "src_abs": src_abs})
        return out
    # fallback: regex-based extraction
    out = []
    seen = set()
    for m in re.finditer(r'<img[^>]*>', html_text, flags=re.I):
        tag = m.group(0)
        src_m = re.search(r'src=["\']?([^"\'>\s]+)', tag, flags=re.I)
        if not src_m:
            continue
        src = src_m.group(1)
        alt_m = re.search(r'alt=["\']?([^"\'>]+)', tag, flags=re.I)
        alt = alt_m.group(1) if alt_m else ''
        src_abs = urljoin(base_url, src)
        key = (alt.strip(), src_abs)
        if key in seen:
            continue
        seen.add(key)
        out.append({"name": html_module.unescape(alt.strip()), "src": src, "src_abs": src_abs})
    return out


def parse_type_chart(html_text):
    """尝试解析页面中的所有表格为二维数组。
    返回 list of tables, each table is list of rows (list of cells text).
    """
    if BeautifulSoup:
        soup = BeautifulSoup(html, "html.parser")
        tables = []
        for table in soup.find_all("table"):
            rows = []
            for tr in table.find_all("tr"):
                cells = []
                for cell in tr.find_all(["th", "td"]):
                    text = " ".join(cell.stripped_strings)
                    cells.append(text)
                if cells:
                    rows.append(cells)
            if rows:
                tables.append(rows)
        return tables
    # fallback: regex-based table extraction
    tables = []
    for tmatch in re.finditer(r'(?is)<table[^>]*>(.*?)</table>', html_text):
        tbody = tmatch.group(1)
        rows = []
        for rmatch in re.finditer(r'(?is)<tr[^>]*>(.*?)</tr>', tbody):
            row_html = rmatch.group(1)
            cells = []
            for cmatch in re.finditer(r'(?is)<t[dh][^>]*>(.*?)</t[dh]>', row_html):
                cell_html = cmatch.group(1)
                text = re.sub(r'<[^>]+>', ' ', cell_html)
                text = html_module.unescape(' '.join(text.split()))
                cells.append(text)
            if cells:
                rows.append(cells)
        if rows:
            tables.append(rows)
    return tables


def parse_type_effect_chart_from_html(html_text):
    """Extract typeEffectChart object from inline JS on the counter calculator page."""
    marker = "const typeEffectChart = {"
    start = html_text.find(marker)
    if start == -1:
        return {}

    brace_start = html_text.find("{", start)
    if brace_start == -1:
        return {}

    depth = 0
    end = -1
    for i in range(brace_start, len(html_text)):
        ch = html_text[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                end = i
                break
    if end == -1:
        return {}

    obj_text = html_text[brace_start:end + 1]
    chart = {}
    entry_pattern = re.compile(
        r"'([^']+)'\s*:\s*\{\s*"
        r"strong:\s*\[(.*?)\]\s*,\s*"
        r"resist:\s*\[(.*?)\]\s*,\s*"
        r"weak:\s*\[(.*?)\]\s*,\s*"
        r"vulnerable:\s*\[(.*?)\]\s*"
        r"\}",
        flags=re.S,
    )

    def parse_js_array_items(text):
        values = []
        for m in re.finditer(r"'([^']*)'", text):
            value = m.group(1).strip()
            if value:
                values.append(value)
        return values

    for m in entry_pattern.finditer(obj_text):
        tname = m.group(1).strip()
        chart[tname] = {
            "strong": parse_js_array_items(m.group(2)),
            "resist": parse_js_array_items(m.group(3)),
            "weak": parse_js_array_items(m.group(4)),
            "vulnerable": parse_js_array_items(m.group(5)),
        }
    return chart


def build_received_damage_single(chart):
    out = []
    for tname, data in chart.items():
        increased = [{"type": x, "multiplier": "2.0"} for x in data.get("weak", []) if x]
        decreased = [{"type": x, "multiplier": "0.5"} for x in data.get("vulnerable", []) if x]
        out.append(
            {
                "defender_type": tname,
                "received_damage_increased": increased,
                "received_damage_decreased": decreased,
            }
        )
    return out


def build_received_damage_dual(chart):
    def build_items(combined, single_value, overlap_value):
        count = {}
        order = []
        for t in combined:
            if not t:
                continue
            if t not in count:
                count[t] = 0
                order.append(t)
            count[t] += 1
        out = []
        for idx, t in enumerate(order):
            c = count[t]
            out.append(
                {
                    "type": t,
                    "count": c,
                    "multiplier": overlap_value if c > 1 else single_value,
                    "index": idx,
                }
            )
        return out

    type_order = [
        "普通", "草", "火", "水", "光", "地", "冰", "龙", "电", "毒",
        "虫", "武", "翼", "萌", "幽", "恶", "机械", "幻",
    ]
    types = [t for t in type_order if t in chart]

    out = []
    for i in range(len(types)):
        for j in range(len(types)):
            if i == j:
                continue
            main_type = types[i]
            sub_type = types[j]
            main_data = chart[main_type]
            sub_data = chart[sub_type]

            weak_combined = (main_data.get("weak", []) + sub_data.get("weak", []))
            vulnerable_combined = (main_data.get("vulnerable", []) + sub_data.get("vulnerable", []))

            weak_items = build_items(weak_combined, "2.0", "3.0")
            vulnerable_items = build_items(vulnerable_combined, "0.5", "0.25")

            weak_set = set([x["type"] for x in weak_items])
            vulnerable_set = set([x["type"] for x in vulnerable_items])
            cancel_set = weak_set.intersection(vulnerable_set)

            weak_items = [x for x in weak_items if x["type"] not in cancel_set]
            weak_items.sort(key=lambda x: (-x["count"], x["index"]))

            vulnerable_items = [x for x in vulnerable_items if x["type"] not in cancel_set]
            vulnerable_items.sort(key=lambda x: (-x["count"], x["index"]))

            out.append(
                {
                    "defender_types": [main_type, sub_type],
                    "received_damage_increased": [
                        {"type": x["type"], "multiplier": x["multiplier"]} for x in weak_items
                    ],
                    "received_damage_decreased": [
                        {"type": x["type"], "multiplier": x["multiplier"]} for x in vulnerable_items
                    ],
                }
            )

    return out


def extract_links(html_text, base_url):
    links = []
    if BeautifulSoup:
        soup = BeautifulSoup(html_text, "html.parser")
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if href.startswith("#"):
                continue
            url = urljoin(base_url, href)
            text = " ".join(a.stripped_strings)
            links.append({"text": text, "href": href, "url": url})
        return links
    for m in re.finditer(r'(?is)<a[^>]+href=["\']?([^"\'>\s]+)["\']?[^>]*>(.*?)</a>', html_text):
        href = m.group(1)
        if href.startswith('#'):
            continue
        url = urljoin(base_url, href)
        text = re.sub(r'<[^>]+>', ' ', m.group(2))
        text = html_module.unescape(' '.join(text.split()))
        links.append({"text": text, "href": href, "url": url})
    return links


def get_wikitext_for_title(title):
    api = "https://wiki.biligame.com/rocom/api.php"
    query = api + "?" + urlencode({
        "action": "query",
        "prop": "revisions",
        "rvprop": "content",
        "titles": title,
        "format": "json",
    })
    try:
        with urllib_request.urlopen(query, timeout=15) as response:
            data = json.load(response)
        pages = data.get("query", {}).get("pages", {})
        for page in pages.values():
            revisions = page.get("revisions")
            if revisions:
                return revisions[0].get("*", "")
    except Exception:
        return ""
    return ""


def get_wikitext_for_titles(titles):
    if not titles:
        return {}
    api = "https://wiki.biligame.com/rocom/api.php"
    query = api + "?" + urlencode({
        "action": "query",
        "prop": "revisions",
        "rvprop": "content",
        "titles": "|".join(titles),
        "format": "json",
    })
    try:
        with urllib_request.urlopen(query, timeout=30) as response:
            data = json.load(response)
    except Exception:
        return {}
    texts = {}
    pages = data.get("query", {}).get("pages", {})
    for page in pages.values():
        revisions = page.get("revisions")
        title = page.get("title", "")
        if revisions and title:
            texts[title] = revisions[0].get("*", "")
    return texts


def extract_pet_attributes(wikitext):
    attributes = []
    if not wikitext:
        return attributes
    for line in wikitext.splitlines():
        line = line.strip()
        if not line.startswith("|") or "=" not in line:
            continue
        key, value = line[1:].split("=", 1)
        key = key.strip()
        value = value.strip()
        if key in {"主属性", "属性", "2属性", "副属性", "类型", "精灵类型"} and value:
            attributes.append({"key": key, "name": value})
    if attributes:
        return attributes

    # fallback: catch any attribute-like field if the template uses a different key
    for line in wikitext.splitlines():
        line = line.strip()
        if not line.startswith("|") or "属性" not in line or "=" not in line:
            continue
        _, value = line[1:].split("=", 1)
        value = value.strip()
        if value:
            attributes.append({"key": "属性", "name": value})
            break
    return attributes


def enrich_pet_entries(pets):
    enriched = []
    titles = []
    for pet in pets:
        link = pet.get("link", "")
        title = unquote(link.rstrip("/").split("/")[-1]) if link else ""
        if title:
            titles.append(title)

    wikitext_by_title = {}
    chunk_size = 10
    for start in range(0, len(titles), chunk_size):
        chunk = titles[start:start + chunk_size]
        wikitext_by_title.update(get_wikitext_for_titles(chunk))

    for pet in pets:
        enriched_pet = dict(pet)
        link = pet.get("link", "")
        title = unquote(link.rstrip("/").split("/")[-1]) if link else ""
        wikitext = wikitext_by_title.get(title, "") if title else ""
        if not wikitext and title:
            wikitext = get_wikitext_for_title(title)
        attributes = extract_pet_attributes(wikitext)
        if attributes:
            enriched_pet["attributes"] = attributes
        else:
            enriched_pet["attributes"] = pet.get("attributes", [])
        enriched_pet["wikitext_title"] = title
        enriched.append(enriched_pet)
    return enriched


def cmd_fetch_save(args):
    html = fetch(args.url)
    outdir = args.outdir or os.path.join(os.path.dirname(__file__), "data")
    os.makedirs(outdir, exist_ok=True)
    filename = os.path.join(outdir, args.filename)
    save_text(html, filename)
    print("Saved HTML ->", filename)


def cmd_attributes(args):
    html = fetch(args.url)
    imgs = parse_images_and_names(html, args.url)
    outdir = args.outdir or os.path.join(os.path.dirname(__file__), "data")
    os.makedirs(outdir, exist_ok=True)
    outpath = os.path.join(outdir, "attributes.json")
    with open(outpath, "w", encoding="utf-8") as f:
        json.dump(imgs, f, ensure_ascii=False, indent=2)
    print("Wrote attributes ->", outpath)


def cmd_typechart(args):
    html = fetch(args.url)
    tables = parse_type_chart(html)
    outdir = args.outdir or os.path.join(os.path.dirname(__file__), "data")
    os.makedirs(outdir, exist_ok=True)
    outpath = os.path.join(outdir, "typechart.json")
    with open(outpath, "w", encoding="utf-8") as f:
        json.dump(tables, f, ensure_ascii=False, indent=2)
    print("Wrote typechart ->", outpath)


def cmd_counter_received(args):
    html_text = fetch(args.url)
    chart = parse_type_effect_chart_from_html(html_text)
    if not chart:
        raise RuntimeError("Could not extract typeEffectChart from page")

    result = {
        "source_url": args.url,
        "source_title": "克制计算器",
        "fields": {
            "received_damage_increased": "受到伤害增加",
            "received_damage_decreased": "受到伤害降低",
        },
        "single_type_rules": build_received_damage_single(chart),
        "dual_type_rules": build_received_damage_dual(chart),
    }

    outpath = args.output or os.path.join(
        os.path.dirname(__file__), "data", "counter_received_damage.json"
    )
    save_json_atomic(result, outpath)
    print("Wrote counter received damage ->", outpath)


def cmd_links(args):
    html = fetch(args.url)
    links = extract_links(html, args.url)
    outdir = args.outdir or os.path.join(os.path.dirname(__file__), "data")
    os.makedirs(outdir, exist_ok=True)
    outpath = os.path.join(outdir, "links.json")
    with open(outpath, "w", encoding="utf-8") as f:
        json.dump(links, f, ensure_ascii=False, indent=2)
    print("Wrote links ->", outpath)


def cmd_pets(args):
    html_text = fetch(args.url)
    outdir = args.outdir or os.path.join(os.path.dirname(__file__), "data")
    os.makedirs(outdir, exist_ok=True)
    pets = []
    def get_wikitext_for_title(title):
        api = "https://wiki.biligame.com/rocom/api.php"
        q = api + "?" + urllib_request.parse.urlencode({
            'action': 'query', 'prop': 'revisions', 'rvprop': 'content', 'titles': title, 'format': 'json'
        })
        try:
            with urllib_request.urlopen(q, timeout=15) as r:
                data = json.load(r)
            pages = data.get('query', {}).get('pages', {})
            for p in pages.values():
                revs = p.get('revisions')
                if revs:
                    return revs[0].get('*', '')
        except Exception:
            return ''
        return ''
    if BeautifulSoup:
        soup = BeautifulSoup(html_text, "html.parser")
        # Try to find images that look like pet artwork and have a link wrapper
        for a in soup.find_all("a", href=True):
            href = a["href"]
            img = a.find("img")
            if not img:
                continue
            # try to find the actual pet article link nearby (not the image file page)
            pet_href = None
            def is_pet_link(h):
                if not h:
                    return False
                if h.startswith(args.url):
                    tail = h[len(args.url):]
                    return ':' not in tail
                if h.startswith('/rocom/'):
                    tail = h[len('/rocom/'):]
                    return ':' not in tail
                return False
            if is_pet_link(href):
                pet_href = href
            else:
                # search in parent and siblings for a suitable link
                for scope in (a.parent, a.parent.parent if a.parent else None):
                    if not scope:
                        continue
                    for la in scope.find_all('a', href=True):
                        if is_pet_link(la['href']):
                            pet_href = la['href']
                            break
                    if pet_href:
                        break
            if not pet_href:
                # fallback to the original href if it looks like a /rocom/ link
                if href.startswith('/rocom/') or href.startswith(args.url):
                    pet_href = href
                else:
                    continue
            src = img.get("src") or img.get("data-src") or ""
            if "立绘" not in (img.get("alt") or "") and "立绘" not in src:
                # still accept if image size looks like artwork (contains 180px)
                if "180px" not in src:
                    continue
            name = (img.get("alt") or a.get_text(strip=True) or href.split("/")[-1]).strip()
            # find nearby attribute icons (small 30px icons)
            attrs = []
            parent = a.parent
            if parent:
                for icon in parent.find_all("img"):
                    isrc = icon.get("src") or icon.get("data-src") or ""
                    if "属性" in (icon.get("alt") or "") or "属性" in isrc or "/30px-" in isrc:
                        alt = icon.get("alt") or ""
                        attrs.append({"name": alt.strip(), "src": isrc, "src_abs": urljoin(args.url, isrc)})
            pets.append({"name": name, "link": urljoin(args.url, pet_href), "art": src, "art_abs": urljoin(args.url, src), "attributes": attrs})
            # try to get attribute from page wikitext
            try:
                title = pet_href.split('/')[-1]
                wikitext = get_wikitext_for_title(urllib_request.parse.unquote(title))
                # try to extract 属性-like fields (主属性 / 副属性 / 2属性 等)
                # prefer explicit keys
                primary = None
                for key in (u'主属性', u'属性', u'2属性', u'副属性'):
                    idx = wikitext.find('|' + key + '=')
                    if idx != -1:
                        val = wikitext[idx + len(key) + 2:]
                        primary = val.splitlines()[0].strip()
                        break
                if primary and not attrs:
                    attrs = [{"name": primary}]
                    pets[-1]['attributes'] = attrs
            except Exception:
                pass
    else:
        # fallback regex: find <a ...><img ...></a>
        for m in re.finditer(r'(?is)(<a[^>]+href=["\']?([^"\'>\s]+)["\']?[^>]*>\s*(<img[^>]+>)\s*</a>)', html_text):
            full, href, imgtag = m.group(1), m.group(2), m.group(3)
            src_m = re.search(r'src=["\']?([^"\'>\s]+)', imgtag, flags=re.I)
            alt_m = re.search(r'alt=["\']?([^"\'>]+)', imgtag, flags=re.I)
            src = src_m.group(1) if src_m else ""
            alt = alt_m.group(1) if alt_m else ""
            if "立绘" not in alt and "180px" not in src:
                continue
            name = alt.strip() or href.split("/")[-1]
            # derive pet_href similar to BeautifulSoup branch
            pet_href = None
            if href.startswith(args.url) or href.startswith('/rocom/'):
                tail = href[len(args.url):] if href.startswith(args.url) else href[len('/rocom/'):]
                if ':' not in tail:
                    pet_href = href
            if not pet_href:
                # search nearby window for a link to /rocom/<title>
                m2 = re.search(r'(/rocom/[^"\'">\s]+)', window)
                if m2:
                    pet_href = m2.group(1)
            if not pet_href:
                pet_href = href
            # try to find attribute icons in nearby 300 chars
            attrs = []
            window = html_text[max(0, m.start()-300):m.end()+300]
            for im in re.finditer(r'(?is)<img[^>]+src=["\']?([^"\'>\s]+)["\']?[^>]*alt=["\']?([^"\'>]+)["\']?', window):
                isrc, ialt = im.group(1), im.group(2)
                if "属性" in ialt or "30px-" in isrc:
                    attrs.append({"name": html_module.unescape(ialt.strip()), "src": isrc, "src_abs": urljoin(args.url, isrc)})
            pets.append({"name": name, "link": urljoin(args.url, pet_href), "art": src, "art_abs": urljoin(args.url, src), "attributes": attrs})
            # try to get attribute from page wikitext
            try:
                title = pet_href.split('/')[-1]
                wikitext = get_wikitext_for_title(urllib_request.parse.unquote(title))
                primary = None
                for key in (u'主属性', u'属性', u'2属性', u'副属性'):
                    idx = wikitext.find('|' + key + '=')
                    if idx != -1:
                        val = wikitext[idx + len(key) + 2:]
                        primary = val.splitlines()[0].strip()
                        break
                if primary and not attrs:
                    attrs = [{"name": primary}]
                    pets[-1]['attributes'] = attrs
            except Exception:
                pass

    outpath = os.path.join(outdir, "pets.json")
    with open(outpath, "w", encoding="utf-8") as f:
        json.dump(pets, f, ensure_ascii=False, indent=2)
    print("Wrote pets ->", outpath)


def cmd_pet_enrich(args):
    inpath = args.input or os.path.join(os.path.dirname(__file__), "data", "pets.json")
    outpath = args.output or os.path.join(os.path.dirname(__file__), "data", "pets_enriched.json")
    with open(inpath, "r", encoding="utf-8") as f:
        pets = json.load(f)
    titles = []
    for pet in pets:
        link = pet.get("link", "")
        title = unquote(link.rstrip("/").split("/")[-1]) if link else ""
        titles.append(title)

    wikitext_by_title = {}
    chunk_size = 10
    enriched = []
    for start in range(0, len(titles), chunk_size):
        chunk_titles = titles[start:start + chunk_size]
        request_titles = [title for title in chunk_titles if title]
        if not request_titles:
            continue
        print(f"Fetching chunk {start // chunk_size + 1}/{(len(titles) + chunk_size - 1) // chunk_size} ...", flush=True)
        wikitext_by_title.update(get_wikitext_for_titles(request_titles))
        for offset, pet in enumerate(pets[start:start + chunk_size]):
            enriched_pet = dict(pet)
            title = chunk_titles[offset] if offset < len(chunk_titles) else ""
            wikitext = wikitext_by_title.get(title, "") if title else ""
            attributes = extract_pet_attributes(wikitext)
            enriched_pet["attributes"] = attributes or pet.get("attributes", [])
            enriched_pet["wikitext_title"] = title
            enriched.append(enriched_pet)
        with open(outpath, "w", encoding="utf-8") as f:
            json.dump(enriched, f, ensure_ascii=False, indent=2)
    with open(outpath, "w", encoding="utf-8") as f:
        json.dump(enriched, f, ensure_ascii=False, indent=2)
    print("Wrote pets_enriched ->", outpath)


def cmd_pet_detail(args):
    inpath = args.input or os.path.join(os.path.dirname(__file__), "data", "pets_enriched.json")
    outpath = args.output or os.path.join(os.path.dirname(__file__), "data", "pets_detailed.json")
    html_dir = args.html_dir or os.path.join(os.path.dirname(__file__), "data", "pets_html")
    os.makedirs(html_dir, exist_ok=True)

    with open(inpath, "r", encoding="utf-8") as f:
        pets = json.load(f)

    only_query = getattr(args, "only_query", "") or ""
    if only_query:
        filtered = []
        for pet in pets:
            title = pet.get("wikitext_title") or unquote(pet.get("link", "").rstrip("/").split("/")[-1])
            name = pet.get("name", "")
            if only_query in title or only_query in name:
                filtered.append(pet)
        pets = filtered

    limit = getattr(args, "limit", None)
    if limit:
        pets = pets[:limit]

    detailed = []
    if os.path.exists(outpath):
        try:
            with open(outpath, "r", encoding="utf-8") as f:
                existing = json.load(f)
            if isinstance(existing, list):
                detailed = existing
        except Exception:
            detailed = []

    completed_keys = set()
    for pet in detailed:
        completed_keys.add((pet.get("name", ""), pet.get("wikitext_title", "")))

    if detailed:
        print(f"Resuming from existing output with {len(detailed)} entries", flush=True)

    remaining = []
    for pet in pets:
        key = (pet.get("name", ""), pet.get("wikitext_title", ""))
        if key not in completed_keys:
            remaining.append(pet)

    total = len(remaining)
    for index, pet in enumerate(remaining, start=1):
        print(f"[{index}/{total}] downloading {pet.get('wikitext_title') or pet.get('name', '')}", flush=True)
        try:
            detail = download_and_parse_pet_page(pet, html_dir)
        except Exception as exc:
            detail = {"html_path": "", "skills": [], "error": str(exc)}
        detailed_pet = dict(pet)
        detailed_pet["html_path"] = detail["html_path"]
        detailed_pet["skills"] = detail["skills"]
        detailed_pet["skill_pools"] = detail["skill_pools"]
        detailed_pet["qualification"] = detail["qualification"]
        detailed_pet["characteristic"] = detail["characteristic"]
        if detail.get("error"):
            detailed_pet["error"] = detail["error"]
        detailed.append(detailed_pet)
        save_json_atomic(detailed, outpath)

    save_json_atomic(detailed, outpath)
    print("Wrote pets_detailed ->", outpath)


def build_parser():
    p = argparse.ArgumentParser(description="Roco Kingdom wiki scraper helpers")
    sub = p.add_subparsers(dest="cmd")

    sp = sub.add_parser("fetch-save", help="Fetch page and save raw HTML")
    sp.add_argument("url")
    sp.add_argument("--outdir", default=None)
    sp.add_argument("--filename", default="page.html")
    sp.set_defaults(func=cmd_fetch_save)

    sp = sub.add_parser("attributes", help="Extract images and names (attributes) from page")
    sp.add_argument("url")
    sp.add_argument("--outdir", default=None)
    sp.set_defaults(func=cmd_attributes)

    sp = sub.add_parser("typechart", help="Parse tables (type chart) from page")
    sp.add_argument("url")
    sp.add_argument("--outdir", default=None)
    sp.set_defaults(func=cmd_typechart)

    sp = sub.add_parser("counter-received", help="Extract received damage increase/decrease multipliers from counter calculator")
    sp.add_argument("url")
    sp.add_argument("--output", default=None)
    sp.set_defaults(func=cmd_counter_received)

    sp = sub.add_parser("links", help="Extract links from page")
    sp.add_argument("url")
    sp.add_argument("--outdir", default=None)
    sp.set_defaults(func=cmd_links)

    sp = sub.add_parser("pets", help="Extract pet entries (name, link, artwork, attributes)")
    sp.add_argument("url")
    sp.add_argument("--outdir", default=None)
    sp.set_defaults(func=cmd_pets)

    sp = sub.add_parser("pet-enrich", help="Enrich existing pets.json with page attributes")
    sp.add_argument("--input", default=None)
    sp.add_argument("--output", default=None)
    sp.set_defaults(func=cmd_pet_enrich)

    sp = sub.add_parser("pet-detail", help="Download each pet page HTML and parse skills")
    sp.add_argument("--input", default=None)
    sp.add_argument("--output", default=None)
    sp.add_argument("--html-dir", default=None)
    sp.add_argument("--only-query", default=None, help="Only process pets whose name or title contains this text")
    sp.add_argument("--limit", type=int, default=None, help="Only process the first N matched pets")
    sp.set_defaults(func=cmd_pet_detail)

    return p


def main(argv=None):
    argv = argv or sys.argv[1:]
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "cmd", None):
        parser.print_help()
        return 2
    args.func(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
