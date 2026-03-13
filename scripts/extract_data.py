#!/usr/bin/env python3
"""从原始数据文件中提取机械设计手册内容，生成 Web 前端所需的 JSON 数据。"""

import csv
import io
import json
import math
import os
import re
import subprocess

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', '新版电子手册')
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'web', 'public', 'data')


def extract_tree():
    """从 .gal 数据库提取目录树。"""
    gal_path = os.path.join(DATA_DIR, '新编机械设计手册.gal')
    result = subprocess.run(
        ['mdb-export', gal_path, 'DrawingDir'],
        capture_output=True, text=True, check=True
    )
    reader = csv.DictReader(io.StringIO(result.stdout))
    rows = list(reader)

    nodes = {}
    for r in rows:
        did = int(r['DirID'])
        nodes[did] = {
            'id': did,
            'name': r['DirName'],
            'parent': int(r['ParDirID']),
            'path': r['DirPath'],
            'content_key': r['DirContent'],
            'type': int(r['DirType']),
            'children': [],
        }

    for did, node in nodes.items():
        pid = node['parent']
        if pid in nodes:
            nodes[pid]['children'].append(did)

    roots = [did for did, n in nodes.items() if n['parent'] == 0 or n['parent'] not in nodes]
    return nodes, roots


def extract_content():
    """从 .cnt 和 .cnx 提取内容，返回 {gallery_key: text_content} 映射。"""
    cnt_path = os.path.join(DATA_DIR, '新编机械设计手册.cnt')
    cnx_path = os.path.join(DATA_DIR, '新编机械设计手册.cnx')

    with open(cnt_path, 'rb') as f:
        cnt_bytes = f.read()

    with open(cnx_path, 'rb') as f:
        cnx_text = f.read().decode('gbk', errors='replace')
    cnx_lines = cnx_text.strip().split('\r\n')

    content_map = {}
    for i in range(0, len(cnx_lines) - 1, 2):
        path_line = cnx_lines[i]
        offset_line = cnx_lines[i + 1]

        match = re.match(r'\\Gallery\\(.+?)\.htz,\[(\d+)\]', path_line)
        if not match:
            continue
        gallery_key = match.group(1)

        start, end = map(int, offset_line.split(','))
        chunk = cnt_bytes[start:end]
        text = chunk.decode('gbk', errors='replace').strip()
        # \r\n = 段落分隔, 单独 \r = 单元格分隔（行列都用 \r）
        # 先按 \r\n 分段，每段内按 \r 分单元格，再检测列数重建行
        text = text.replace('\r\n', '\x00')
        sections = text.split('\x00')
        output_parts = []
        for section in sections:
            section = section.strip()
            if not section:
                continue
            cells = section.split('\r')
            # 去掉尾部空 cell
            while cells and not cells[-1].strip():
                cells.pop()
            if not cells:
                continue
            if len(cells) <= 1:
                # 纯文本段落
                output_parts.append(cells[0])
            else:
                # 多个 cell → 尝试重建表格行
                formatted = _rebuild_table_rows(cells)
                output_parts.append(formatted)
        content_map[gallery_key] = '\n'.join(output_parts)

    return content_map


def _detect_col_count(cells):
    """从扁平 cell 列表中推断列数。

    使用数值自相关：正确列数下，相距 cols 的 cell 属于同一列，
    数值差异最小。对纯文本无数值的 section 返回 0。
    """
    n = len(cells)
    if n <= 3:
        return 0

    # 解析所有 cell 为数值
    nums = []
    for c in cells:
        s = c.strip()
        if not s or s in ('-', '—'):
            nums.append(None)
            continue
        try:
            nums.append(float(s))
        except ValueError:
            nums.append(None)

    best_cols = 0
    best_score = float('inf')

    for cols in range(2, min(41, n // 2 + 1)):
        total_diff = 0.0
        count = 0
        for i in range(n - cols):
            v1 = nums[i]
            v2 = nums[i + cols]
            if v1 is not None and v2 is not None and v1 != 0 and v2 != 0:
                total_diff += abs(
                    math.log(abs(v1) + 0.001) - math.log(abs(v2) + 0.001)
                )
                count += 1

        if count < max(10, n * 0.05):
            continue
        avg_diff = total_diff / count
        # 对大列数加 log 惩罚，防止窄值域表格误选大列数
        score = avg_diff * math.log(cols + 1)
        if score < best_score:
            best_score = score
            best_cols = cols

    return best_cols if best_cols > 0 else 0


def _find_data_start(cells, cols):
    """找到数据行的起始位置（跳过不对齐的表头）。

    扫描所有可能的起始位置，选择使前两行数值比例最高的位置。
    """
    n = len(cells)

    def _is_num(s):
        s = s.strip()
        if not s or s in ('-', '—'):
            return True
        try:
            float(s)
            return True
        except ValueError:
            return False

    best_d = 0
    best_score = -1
    search_range = min(n - cols * 2, cols * 3)
    if search_range <= 0:
        return 0

    for d in range(search_range):
        if d + cols * 2 > n:
            break
        row1 = cells[d:d + cols]
        row2 = cells[d + cols:d + cols * 2]
        num1 = sum(1 for c in row1 if _is_num(c))
        num2 = sum(1 for c in row2 if _is_num(c))
        score = num1 + num2
        if score > best_score:
            best_score = score
            best_d = d

    # 只有当数值行确实比全部从头开始好时才偏移
    if best_score >= cols * 1.6:
        return best_d
    return 0


def _detect_col_count_text(cells):
    """纯文本表格的列数检测（自相关失败时的备用方案）。

    目前纯文本表格缺乏可靠的列数检测信号，暂时返回 0
    让这些内容以纯文本形式显示。
    """
    return 0


def _rebuild_table_rows(cells):
    """将扁平的 cell 列表重建为 \\n 分隔行、\\t 分隔列的文本。"""
    cols = _detect_col_count(cells)
    if cols < 2:
        # 自相关失败，尝试文本模式检测
        cols = _detect_col_count_text(cells)
    if cols < 2:
        # 仍然无法检测列数，每个 cell 作为独立段落
        return '\n'.join(c for c in cells if c.strip())

    # 找到数据行起始位置
    data_start = _find_data_start(cells, cols)

    rows = []
    # 表头部分：不按 cols 分行，每个 cell 拼成一行
    if data_start > 0:
        header_cells = cells[:data_start]
        # 尝试把表头也按 cols 对齐；如果不能整除，合并为一行
        if len(header_cells) == cols:
            rows.append('\t'.join(header_cells))
        elif len(header_cells) % cols == 0:
            for i in range(0, len(header_cells), cols):
                rows.append('\t'.join(header_cells[i:i + cols]))
        else:
            # 表头 cell 数与 cols 不匹配，把多余部分合并输出
            rows.append('\t'.join(header_cells))

    # 数据部分
    for i in range(data_start, len(cells), cols):
        row_cells = cells[i:i + cols]
        rows.append('\t'.join(row_cells))

    return '\n'.join(rows)


def build_output(nodes, roots, content_map):
    """将目录树和内容合并，输出前端所需的 JSON。"""

    def make_content_key(node):
        path = node['path'].lstrip('\\')
        key = node['content_key']
        if not key:
            return None
        return f"{path}\\{key}"

    def build_node(did):
        node = nodes[did]
        result = {
            'id': node['id'],
            'name': node['name'],
        }
        children = [build_node(cid) for cid in sorted(node['children'])]
        if children:
            result['children'] = children
        else:
            ck = make_content_key(node)
            if ck and ck in content_map:
                result['contentId'] = ck
        return result

    tree = [build_node(r) for r in sorted(roots)]

    # 内容按章节目录分组，拆成多个小文件按需加载
    # chapter_key = 路径第一段 (如 NEW01, SEW, 02 等)
    # 统一为大写以避免 macOS 大小写不敏感文件系统冲突
    chapters = {}
    for did, node in nodes.items():
        ck = make_content_key(node)
        if ck and ck in content_map and not node['children']:
            chapter = ck.split('\\')[0] if '\\' in ck else 'misc'
            chapter = chapter.upper()
            if chapter not in chapters:
                chapters[chapter] = {}
            chapters[chapter][ck] = content_map[ck]

    # 搜索索引：id + name + preview
    search_index = []
    for did, node in nodes.items():
        if node['children']:
            continue
        ck = make_content_key(node)
        entry = {'id': node['id'], 'name': node['name']}
        if ck and ck in content_map:
            entry['contentId'] = ck
            entry['preview'] = content_map[ck][:300]
        search_index.append(entry)

    return tree, chapters, search_index


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print('Extracting directory tree...')
    nodes, roots = extract_tree()
    print(f'  {len(nodes)} nodes, {len(roots)} roots')

    print('Extracting content...')
    content_map = extract_content()
    print(f'  {len(content_map)} entries')

    print('Building output...')
    tree, chapters, search_index = build_output(nodes, roots, content_map)

    tree_path = os.path.join(OUTPUT_DIR, 'tree.json')
    with open(tree_path, 'w', encoding='utf-8') as f:
        json.dump(tree, f, ensure_ascii=False)
    print(f'  tree.json: {os.path.getsize(tree_path) / 1024 / 1024:.1f} MB')

    # 按章节拆分内容文件
    chapters_dir = os.path.join(OUTPUT_DIR, 'chapters')
    os.makedirs(chapters_dir, exist_ok=True)
    chapter_list = []
    for ch_name, ch_contents in chapters.items():
        ch_path = os.path.join(chapters_dir, f'{ch_name}.json')
        with open(ch_path, 'w', encoding='utf-8') as f:
            json.dump(ch_contents, f, ensure_ascii=False)
        size = os.path.getsize(ch_path)
        chapter_list.append({'name': ch_name, 'count': len(ch_contents), 'size': size})
        print(f'  chapters/{ch_name}.json: {size / 1024:.0f} KB ({len(ch_contents)} entries)')

    # 章节清单
    manifest_path = os.path.join(OUTPUT_DIR, 'chapters-manifest.json')
    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(chapter_list, f, ensure_ascii=False)

    search_path = os.path.join(OUTPUT_DIR, 'search-index.json')
    with open(search_path, 'w', encoding='utf-8') as f:
        json.dump(search_index, f, ensure_ascii=False)
    print(f'  search-index.json: {os.path.getsize(search_path) / 1024 / 1024:.1f} MB')

    print('Done!')


if __name__ == '__main__':
    main()
