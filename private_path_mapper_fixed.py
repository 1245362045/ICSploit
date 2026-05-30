#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
private_path_mapper.py

作用：
1. 读取 SSTG 程序输出的状态路径文件，以及原始 txt 流量文本。
2. 按状态路径输出 txt：每条路径对应一个字典。
   - 字典 key：功能码的值
   - 字典 value：该功能码对应的请求报文
3. 提供函数 load_path_mapping_txt()，可直接手动读取输出 txt。
4. 程序按“私有协议字段抽取方案”编写，不出现具体协议提示。

支持的状态路径输入：
- paths.csv：原 SSTG 程序输出的 path_id, step, state
- sstg.json：原 SSTG 程序输出的 paths 字段
- 普通 txt：每行一条路径，例如：
  1:Read -> 3:Write -> 6:Ack

支持的流量 txt：
- 每行一个十六进制报文：
  010300000002
  01 03 00 00 00 02
- 可带方向前缀：
  C> 010300000002
  send: 010300000002
  tx: 010300000002
- raw: 前缀：
  raw:abcdef
- 空行、---、===、*** 可作为分段符。
"""

from __future__ import annotations

import argparse
import ast
import csv
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


SPLIT_MARKS = {"---", "===", "***"}


def parse_packet_line(line: str) -> Tuple[Optional[str], Optional[bytes], bool, str]:
    """
    解析流量文本中的一行。

    返回：
    - direction：方向，可能为 c/s/client/server/send/recv/tx/rx，也可能为 None
    - packet_bytes：报文字节
    - is_split：是否为路径/会话分隔符
    - packet_text：清洗后的原始报文文本，输出字典时使用
    """
    raw = line.rstrip("\n")
    text = raw.strip()

    if not text:
        return None, None, True, ""

    if text.startswith("#"):
        return None, None, text.lower().startswith(("# session", "# path")), ""

    if text in SPLIT_MARKS:
        return None, None, True, ""

    direction = None
    m = re.match(r"^(C>|S>|client:|server:|send:|recv:|tx:|rx:)\s*(.*)$", text, flags=re.I)
    if m:
        direction = m.group(1).rstrip(":>").lower()
        text = m.group(2).strip()

    if text.lower().startswith("raw:"):
        raw_text = text[4:]
        return direction, raw_text.encode("utf-8", errors="ignore"), False, raw_text

    cleaned = text.replace("\\x", " ").replace("0x", " ").replace("0X", " ")
    hex_text = re.sub(r"[^0-9a-fA-F]", "", cleaned)

    if hex_text and len(hex_text) % 2 == 0:
        try:
            return direction, bytes.fromhex(hex_text), False, hex_text.lower()
        except ValueError:
            pass

    return direction, text.encode("utf-8", errors="ignore"), False, text


def extract_code(packet: bytes, offset: int, length: int, endian: str = "big",
                 bit_mask: Optional[int] = None, bit_shift: int = 0) -> Optional[int]:
    """
    从报文中抽取功能码。
    offset 从报文有效载荷第 0 字节开始计算。
    """
    if offset < 0 or length <= 0:
        return None

    end = offset + length
    if len(packet) < end:
        return None

    value = int.from_bytes(packet[offset:end], endian, signed=False)

    if bit_mask is not None:
        value = (value & bit_mask) >> bit_shift

    return value


def normalize_state_code(state: str) -> Optional[int]:
    """
    从状态字符串中抽取功能码值。

    兼容：
    - "3"
    - "3:xxx"
    - "S(3:xxx)"
    - "OP_3"
    """
    if state is None:
        return None

    s = str(state).strip()
    if not s:
        return None

    m = re.search(r"S\((.*?)\)", s)
    if m:
        s = m.group(1).strip()

    m = re.match(r"^(\d+)\s*:", s)
    if m:
        return int(m.group(1))

    m = re.match(r"^OP_(\d+)$", s, flags=re.I)
    if m:
        return int(m.group(1))

    if s.isdigit():
        return int(s)

    m = re.search(r"\d+", s)
    if m:
        return int(m.group(0))

    return None


def read_state_paths(path_file: str | Path) -> List[List[int]]:
    """
    读取状态路径文件，返回功能码路径列表。
    """
    path = Path(path_file)

    if not path.exists():
        raise FileNotFoundError(f"状态路径文件不存在: {path}")

    suffix = path.suffix.lower()

    if suffix == ".json":
        with path.open("r", encoding="utf-8", errors="ignore") as f:
            data = json.load(f)

        raw_paths = data.get("paths", [])
        result: List[List[int]] = []

        for p in raw_paths:
            codes = []
            for state in p:
                code = normalize_state_code(str(state))
                if code is not None:
                    codes.append(code)
            if codes:
                result.append(codes)

        return result

    if suffix == ".csv":
        grouped: Dict[int, List[Tuple[int, int]]] = defaultdict(list)

        with path.open("r", encoding="utf-8-sig", errors="ignore", newline="") as f:
            reader = csv.DictReader(f)
            fields = reader.fieldnames or []

            if {"path_id", "step", "state"}.issubset(set(fields)):
                for row in reader:
                    code = normalize_state_code(row.get("state", ""))
                    if code is None:
                        continue
                    path_id = int(row["path_id"])
                    step = int(row["step"])
                    grouped[path_id].append((step, code))

                return [
                    [code for _, code in sorted(items, key=lambda x: x[0])]
                    for _, items in sorted(grouped.items(), key=lambda x: x[0])
                    if items
                ]

        raise ValueError("CSV 状态路径文件需要包含 path_id, step, state 三列")

    result = []
    with path.open("r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            text = line.strip()
            if not text or text.startswith("#"):
                continue

            parts = re.split(r"\s*(?:->|,|\s+)\s*", text)
            codes = []

            for part in parts:
                code = normalize_state_code(part)
                if code is not None:
                    codes.append(code)

            if codes:
                result.append(codes)

    return result


def read_flow_packets(flow_txt: str | Path, request_only: bool = True,
                      split_blank: bool = False) -> List[List[Tuple[int, str]]]:
    """
    读取流量 txt，返回会话列表。

    每条报文保存为：
    - 功能码值
    - 原始请求报文文本

    request_only=True 时，只保留常见发送方向：
    c / client / send / tx / 无方向
    """
    return read_flow_packets_with_config(
        flow_txt=flow_txt,
        offset=0,
        length=1,
        endian="big",
        bit_mask=None,
        bit_shift=0,
        request_only=request_only,
        split_blank=split_blank,
    )


def read_flow_packets_with_config(flow_txt: str | Path,
                                  offset: int,
                                  length: int,
                                  endian: str = "big",
                                  bit_mask: Optional[int] = None,
                                  bit_shift: int = 0,
                                  request_only: bool = True,
                                  split_blank: bool = False) -> List[List[Tuple[int, str]]]:
    """
    按字段配置读取流量 txt。
    """
    path = Path(flow_txt)
    if not path.exists():
        raise FileNotFoundError(f"流量文本不存在: {path}")

    sessions: List[List[Tuple[int, str]]] = []
    current: List[Tuple[int, str]] = []

    allow_direction = {None, "c", "client", "send", "tx"}

    with path.open("r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            direction, packet, is_split, packet_text = parse_packet_line(line)

            if is_split and split_blank:
                if current:
                    sessions.append(current)
                    current = []
                continue

            if packet is None:
                continue

            if request_only and direction not in allow_direction:
                continue

            code = extract_code(
                packet=packet,
                offset=offset,
                length=length,
                endian=endian,
                bit_mask=bit_mask,
                bit_shift=bit_shift,
            )

            if code is None:
                continue

            current.append((code, packet_text))

    if current:
        sessions.append(current)

    return sessions


def make_path_dicts(state_paths: List[List[int]],
                    flow_sessions: List[List[Tuple[int, str]]],
                    keep_all_packets: bool = False) -> List[Dict[int, Any]]:
    """
    根据状态路径从流量中匹配请求报文。

    keep_all_packets=False：
      每个功能码只保存第一个匹配报文。
    keep_all_packets=True：
      每个功能码保存匹配到的报文列表。
    """
    all_packets: List[Tuple[int, str]] = []
    for session in flow_sessions:
        all_packets.extend(session)

    code_to_packets: Dict[int, List[str]] = defaultdict(list)
    for code, packet_text in all_packets:
        code_to_packets[code].append(packet_text)

    result: List[Dict[int, Any]] = []

    for path in state_paths:
        one: Dict[int, Any] = {}

        for code in path:
            packets = code_to_packets.get(code, [])

            if keep_all_packets:
                one[code] = packets[:]
            else:
                one[code] = packets[0] if packets else ""

        result.append(one)

    return result


def save_path_mapping_txt(output_txt: str | Path,
                          state_paths: List[List[int]],
                          path_dicts: List[Dict[int, Any]]) -> None:
    """
    保存状态路径和对应字典。
    输出格式方便人工读，也方便 load_path_mapping_txt() 直接读回。
    """
    out = Path(output_txt)
    out.parent.mkdir(parents=True, exist_ok=True)

    with out.open("w", encoding="utf-8") as f:
        for idx, (path, mapping) in enumerate(zip(state_paths, path_dicts), start=1):
            path_text = " -> ".join(str(x) for x in path)
            f.write(f"[PATH_{idx}]\n")
            f.write(f"path = {path_text}\n")
            f.write(f"mapping = {repr(mapping)}\n")
            f.write("\n")


def load_path_mapping_txt(mapping_txt: str | Path) -> List[Dict[str, Any]]:
    """
    手动读取 save_path_mapping_txt() 生成的 txt。

    返回：
    [
      {
        "path_id": "PATH_1",
        "path": [1, 3, 4],
        "mapping": {1: "...", 3: "...", 4: "..."}
      }
    ]
    """
    path = Path(mapping_txt)
    if not path.exists():
        raise FileNotFoundError(f"映射文本不存在: {path}")

    result: List[Dict[str, Any]] = []
    current: Optional[Dict[str, Any]] = None

    with path.open("r", encoding="utf-8", errors="ignore") as f:
        for raw in f:
            line = raw.strip()

            if not line:
                continue

            m = re.match(r"^\[(PATH_\d+)\]$", line)
            if m:
                if current:
                    result.append(current)
                current = {
                    "path_id": m.group(1),
                    "path": [],
                    "mapping": {},
                }
                continue

            if current is None:
                continue

            if line.startswith("path ="):
                path_text = line.split("=", 1)[1].strip()
                current["path"] = [
                    int(x.strip())
                    for x in path_text.split("->")
                    if x.strip().isdigit()
                ]

            elif line.startswith("mapping ="):
                mapping_text = line.split("=", 1)[1].strip()
                current["mapping"] = ast.literal_eval(mapping_text)

    if current:
        result.append(current)

    return result


def build_mapping_file(state_path_file: str | Path,
                       flow_txt: str | Path,
                       output_txt: str | Path,
                       offset: int,
                       length: int,
                       endian: str = "big",
                       bit_mask: Optional[int] = None,
                       bit_shift: int = 0,
                       request_only: bool = True,
                       split_blank: bool = False,
                       keep_all_packets: bool = False) -> List[Dict[int, Any]]:
    """
    一站式调用函数：
    读取状态路径 + 读取流量文本 + 输出路径映射 txt。
    """
    state_paths = read_state_paths(state_path_file)
    flow_sessions = read_flow_packets_with_config(
        flow_txt=flow_txt,
        offset=offset,
        length=length,
        endian=endian,
        bit_mask=bit_mask,
        bit_shift=bit_shift,
        request_only=request_only,
        split_blank=split_blank,
    )

    path_dicts = make_path_dicts(
        state_paths=state_paths,
        flow_sessions=flow_sessions,
        keep_all_packets=keep_all_packets,
    )

    save_path_mapping_txt(
        output_txt=output_txt,
        state_paths=state_paths,
        path_dicts=path_dicts,
    )

    return path_dicts


def main() -> None:
    ap = argparse.ArgumentParser(description="从状态路径和 txt 流量中生成状态路径-请求报文字典。")
    ap.add_argument("--state-path", required=True, help="SSTG 输出的 paths.csv / sstg.json / 普通路径 txt")
    ap.add_argument("--flow", required=True, help="原始 txt 流量文本")
    ap.add_argument("--out", default="state_path_request_mapping.txt", help="输出 txt 文件")

    ap.add_argument("--offset", type=int, required=True, help="功能码字段偏移，从报文第 0 字节开始")
    ap.add_argument("--length", type=int, default=1, help="功能码字段长度，默认 1")
    ap.add_argument("--endian", choices=["big", "little"], default="big", help="字节序，默认 big")
    ap.add_argument("--bit-mask", type=lambda x: int(x, 0), default=None, help="可选 bit mask，例如 0xf0")
    ap.add_argument("--bit-shift", type=int, default=0, help="可选右移位数")

    ap.add_argument("--include-response", action="store_true", help="包含响应方向报文")
    ap.add_argument("--split-blank", action="store_true", help="空行/---/===/*** 作为流量分段")
    ap.add_argument("--keep-all", action="store_true", help="每个功能码保存所有匹配报文列表")

    args = ap.parse_args()

    path_dicts = build_mapping_file(
        state_path_file=args.state_path,
        flow_txt=args.flow,
        output_txt=args.out,
        offset=args.offset,
        length=args.length,
        endian=args.endian,
        bit_mask=args.bit_mask,
        bit_shift=args.bit_shift,
        request_only=not args.include_response,
        split_blank=args.split_blank,
        keep_all_packets=args.keep_all,
    )

    print("[+] 状态路径请求报文映射已生成")
    print(f"输出文件: {Path(args.out).resolve()}")
    print(f"路径数量: {len(path_dicts)}")


if __name__ == "__main__":
    main()

# =========================
# 便捷查询函数：兼容多种 txt 输出格式
# =========================

def _parse_code_list_from_text(text: str) -> List[int]:
    """从 '1 -> 2 -> 3'、'[1, 2, 3]'、'S(1:x) -> S(2:y)' 中提取状态码列表。"""
    text = str(text).strip()
    if not text:
        return []
    try:
        obj = ast.literal_eval(text)
        if isinstance(obj, (list, tuple)):
            out = []
            for x in obj:
                code = normalize_state_code(str(x))
                if code is not None:
                    out.append(code)
            return out
    except Exception:
        pass
    out = []
    for part in re.split(r"\s*(?:->|,|\s+)\s*", text):
        code = normalize_state_code(part)
        if code is not None:
            out.append(code)
    return out


def _normalize_mapping_keys(mapping: Any) -> Dict[int, Any]:
    """把 mapping 字典的 key 统一转成 int，避免 '4' 和 4 查不到。"""
    if not isinstance(mapping, dict):
        return {}
    out: Dict[int, Any] = {}
    for k, v in mapping.items():
        code = normalize_state_code(str(k))
        if code is not None:
            out[code] = v
    return out


def load_path_mapping_txt(mapping_txt: str | Path) -> List[Dict[str, Any]]:
    """
    读取 state_path_request_mapping.txt。

    兼容格式 1：
        [PATH_1]
        path = 4 -> 5
        mapping = {4: '...', 5: '...'}

    兼容格式 2：
        PATH_NAME: PATH_1
        STATE_PATH: [4, 5]
        REQUEST_PACKETS: {4: '...', 5: '...'}

    返回：
        [
          {
            'path_id': 'PATH_1',
            'path': [4, 5],
            'mapping': {4: '...', 5: '...'}
          }
        ]
    """
    path = Path(mapping_txt)
    if not path.exists():
        raise FileNotFoundError(f"映射文本不存在: {path}")

    content = path.read_text(encoding="utf-8", errors="ignore")
    result: List[Dict[str, Any]] = []

    # 格式 1：[PATH_1] + path = + mapping =
    header_re = re.compile(r"^\s*\[(PATH_\d+)\]\s*$", re.I | re.M)
    headers = list(header_re.finditer(content))

    if headers:
        for i, h in enumerate(headers):
            path_id = h.group(1).upper()
            start = h.end()
            end = headers[i + 1].start() if i + 1 < len(headers) else len(content)
            block = content[start:end]

            path_match = re.search(r"^\s*path\s*=\s*(.+?)\s*$", block, re.I | re.M)
            mapping_match = re.search(r"^\s*mapping\s*=\s*(\{.*?\})\s*$", block, re.I | re.M | re.S)

            state_path = _parse_code_list_from_text(path_match.group(1)) if path_match else []
            mapping: Dict[int, Any] = {}
            if mapping_match:
                try:
                    mapping = _normalize_mapping_keys(ast.literal_eval(mapping_match.group(1)))
                except Exception:
                    mapping = {}

            result.append({"path_id": path_id, "path": state_path, "mapping": mapping})

        return result

    # 格式 2：PATH_NAME / STATE_PATH / REQUEST_PACKETS
    blocks = re.split(r"={5,}|\n\s*\n", content)
    for block in blocks:
        block = block.strip()
        if not block:
            continue

        name_match = re.search(r"PATH_NAME\s*[:=]\s*(.+)", block, re.I)
        state_match = re.search(r"STATE_PATH\s*[:=]\s*(.+)", block, re.I)
        req_match = re.search(r"REQUEST_PACKETS\s*[:=]\s*(\{.*\})", block, re.I | re.S)

        if not name_match:
            continue

        path_id = name_match.group(1).strip().upper()
        state_path = _parse_code_list_from_text(state_match.group(1)) if state_match else []

        mapping = {}
        if req_match:
            try:
                mapping = _normalize_mapping_keys(ast.literal_eval(req_match.group(1).strip()))
            except Exception:
                mapping = {}

        result.append({"path_id": path_id, "path": state_path, "mapping": mapping})

    return result


def list_path_names(mapping_txt: str | Path) -> List[str]:
    return [item["path_id"] for item in load_path_mapping_txt(mapping_txt)]


def get_path_detail(mapping_txt: str | Path, path_id: str | int) -> Optional[Dict[str, Any]]:
    """
    获取某条路径详细信息。

    支持：1、'1'、'PATH_1'、'路径1'
    找不到时返回 None。
    """
    if isinstance(path_id, int):
        target = f"PATH_{path_id}"
    else:
        text = str(path_id).strip().upper()
        if text.startswith("PATH_"):
            target = text
        else:
            m = re.search(r"\d+", text)
            target = f"PATH_{int(m.group(0))}" if m else text

    for item in load_path_mapping_txt(mapping_txt):
        if item.get("path_id", "").upper() == target:
            return {
                "path_name": item["path_id"],
                "state_path": item["path"],
                "request_packets": item["mapping"],
            }

    return None


def get_state_path(mapping_txt: str | Path, path_id: str | int) -> Optional[List[int]]:
    detail = get_path_detail(mapping_txt, path_id)
    return None if detail is None else detail["state_path"]


def get_request_packets(mapping_txt: str | Path, path_id: str | int) -> Optional[Dict[int, Any]]:
    detail = get_path_detail(mapping_txt, path_id)
    return None if detail is None else detail["request_packets"]


def get_packet_by_state(mapping_txt: str | Path, path_id: str | int, state_code: int | str) -> Optional[Any]:
    packets = get_request_packets(mapping_txt, path_id)
    if packets is None:
        return None
    code = normalize_state_code(str(state_code))
    if code is None:
        return None
    return packets.get(code)


def print_path_detail(mapping_txt: str | Path, path_id: str | int) -> Optional[Dict[str, Any]]:
    detail = get_path_detail(mapping_txt, path_id)
    if detail is None:
        print(f"Path not found: {path_id}")
        return None

    print("=" * 60)
    print(f"路径名: {detail['path_name']}")
    print("状态路径: " + " -> ".join(str(x) for x in detail["state_path"]))
    print("对应请求报文:")

    for code in detail["state_path"]:
        packet = detail["request_packets"].get(code, "")
        print(f"  功能码 {code}: {packet}")

    print("=" * 60)
    return detail

def get_packets_only(txt_path, path_id):
    """
    只返回报文列表
    不返回功能码

    返回:
    [
        "01020304",
        "05060708"
    ]
    """

    packets = get_request_packets(txt_path, path_id)

    if not packets:
        return []

    return list(packets.values())