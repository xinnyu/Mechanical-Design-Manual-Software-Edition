#!/usr/bin/env python3
"""从原始数据文件中提取机械设计手册内容，生成 Web 前端所需的 JSON 数据。"""

import csv
import io
import json
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
        # 用字节偏移在原始 bytes 上切片，然后再解码
        chunk = cnt_bytes[start:end]
        text = chunk.decode('gbk', errors='replace').strip()
        # 关键：\r\n = 段落/行换行, 单独的 \r = 表格单元格分隔
        # 先保护 \r\n，把单独的 \r 转为 \t（tab），再恢复 \r\n -> \n
        text = text.replace('\r\n', '\x00')
        text = text.replace('\r', '\t')
        text = text.replace('\x00', '\n')
        content_map[gallery_key] = text

    return content_map


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
    chapters = {}
    for did, node in nodes.items():
        ck = make_content_key(node)
        if ck and ck in content_map and not node['children']:
            chapter = ck.split('\\')[0] if '\\' in ck else 'misc'
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
