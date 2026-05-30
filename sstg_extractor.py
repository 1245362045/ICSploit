#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SSTG Extractor：从 txt 报文文本中抽象 System State Tracking Graph，并保存状态路径。

用途：
- 不发包，只根据 txt 中的报文序列抽象 SSTG。
- 按协议名读取功能码/状态字段配置，offset 从 TCP/UDP 有效载荷第 0 字节开始计算。
- 支持 protocol_field_cache.json；没有缓存时使用内置默认配置。
- 输出：states.csv、edges.csv、paths.csv、sstg.json、sstg.dot。

输入 txt 支持：
1) 每行一个十六进制报文：
   0001746573742e747874006f6374657400
   00 01 74 65 73 74 2e 74 78 74 00 6f 63 74 65 74 00
2) raw: 前缀：
   raw:hello\n
3) 可选方向前缀，便于区分发送/接收：
   C> 0001...
   S> 0004...
   client: 0001...
   server: 0004...

4) 可选分段符，表示一条新路径/新会话：
   ---
   # session 2

示例：
  python3 sstg_extractor.py --protocol TFTP --input seeds.txt --out sstg_out
  python3 sstg_extractor.py --protocol Modbus --input modbus.txt --cache protocol_field_cache.json --mode sequence
  python3 sstg_extractor.py --protocol DHCP --input dhcp.txt --out dhcp_sstg --path-split blank
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import time
from collections import Counter, defaultdict, deque
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import DefaultDict, Dict, Iterable, List, Optional, Tuple

NO_PACKET = "∅"

PROTOCOLS = [
    "NTP", "DHCP", "TFTP", "CJ188", "Modbus RTU", "BACnet",
    "Modbus", "IEC 104", "DNP3", "S7comm",
]


@dataclass
class FieldSpec:
    name: str
    offset: int
    length: int
    endian: str = "big"
    values: Dict[int, str] = field(default_factory=dict)
    bit_mask: Optional[int] = None
    bit_shift: int = 0
    parser: str = "fixed"  # fixed / dhcp_option53 / bacnet_pdu_type


@dataclass
class ProtocolConfig:
    name: str
    transport: str
    default_port: int
    opcode_field: FieldSpec


BUILTIN_CONFIGS: Dict[str, ProtocolConfig] = {
    "NTP": ProtocolConfig(
        "NTP", "udp", 123,
        FieldSpec("mode", 0, 1, "big", {
            0: "reserved", 1: "sym_active", 2: "sym_passive", 3: "client",
            4: "server", 5: "broadcast", 6: "control", 7: "private",
        }, bit_mask=0x07),
    ),
    "DHCP": ProtocolConfig(
        "DHCP", "udp", 67,
        FieldSpec("dhcp_message_type", 240, 1, "big", {
            1: "DISCOVER", 2: "OFFER", 3: "REQUEST", 4: "DECLINE",
            5: "ACK", 6: "NAK", 7: "RELEASE", 8: "INFORM",
        }, parser="dhcp_option53"),
    ),
    "TFTP": ProtocolConfig(
        "TFTP", "udp", 69,
        FieldSpec("opcode", 0, 2, "big", {
            1: "RRQ", 2: "WRQ", 3: "DATA", 4: "ACK", 5: "ERROR", 6: "OACK",
        }),
    ),
    "CJ188": ProtocolConfig(
        "CJ188", "udp", 0,
        FieldSpec("control", 8, 1, "big"),
    ),
    "Modbus RTU": ProtocolConfig(
        "Modbus RTU", "tcp", 0,
        FieldSpec("function_code", 1, 1, "big", {
            1: "Read Coils", 2: "Read Discrete Inputs", 3: "Read Holding Registers",
            4: "Read Input Registers", 5: "Write Single Coil", 6: "Write Single Register",
            15: "Write Multiple Coils", 16: "Write Multiple Registers",
        }),
    ),
    "BACnet": ProtocolConfig(
        "BACnet", "udp", 47808,
        # BACnet/IP 常见 BVLC 4 字节 + NPDU 2 字节，APDU 第 1 字节高 4 bit 是 PDU Type。
        FieldSpec("pdu_type", 6, 1, "big", {
            0: "Confirmed-REQ", 1: "Unconfirmed-REQ", 2: "SimpleACK", 3: "ComplexACK",
            4: "SegmentACK", 5: "Error", 6: "Reject", 7: "Abort",
        }, bit_mask=0xF0, bit_shift=4, parser="bacnet_pdu_type"),
    ),
    "Modbus": ProtocolConfig(
        "Modbus", "tcp", 502,
        FieldSpec("function_code", 7, 1, "big", {
            1: "Read Coils", 2: "Read Discrete Inputs", 3: "Read Holding Registers",
            4: "Read Input Registers", 5: "Write Single Coil", 6: "Write Single Register",
            15: "Write Multiple Coils", 16: "Write Multiple Registers",
        }),
    ),
    "IEC 104": ProtocolConfig(
        "IEC 104", "tcp", 2404,
        FieldSpec("type_id", 6, 1, "big"),
    ),
    "DNP3": ProtocolConfig(
        "DNP3", "tcp", 20000,
        FieldSpec("function_code", 12, 1, "big"),
    ),
    "S7comm": ProtocolConfig(
        "S7comm", "tcp", 102,
        FieldSpec("function", 17, 1, "big", {
            4: "READ_VAR", 5: "WRITE_VAR", 0xF0: "SETUP_COMM", 0x1A: "REQUEST_DOWNLOAD",
            0x1B: "DOWNLOAD_BLOCK", 0x1C: "DOWNLOAD_ENDED", 0x1D: "START_UPLOAD",
            0x1E: "UPLOAD", 0x1F: "END_UPLOAD", 0x28: "PI_SERVICE", 0x29: "PLC_STOP",
        }),
    ),
}


def normalize_protocol(name: str) -> str:
    wanted = name.strip().lower().replace("_", " ").replace("-", " ")
    aliases = {
        "modbus tcp": "Modbus", "mbtcp": "Modbus", "modbus rtu": "Modbus RTU",
        "iec104": "IEC 104", "iec 60870 5 104": "IEC 104", "s7": "S7comm",
        "s7 comm": "S7comm", "bacnet ip": "BACnet",
    }
    if wanted in aliases:
        return aliases[wanted]
    for p in PROTOCOLS:
        if p.lower() == wanted:
            return p
    raise ValueError(f"未知协议: {name}，支持: {', '.join(PROTOCOLS)}")


def _coerce_values(values: object) -> Dict[int, str]:
    out: Dict[int, str] = {}
    if isinstance(values, dict):
        for k, v in values.items():
            try:
                out[int(k)] = str(v)
            except Exception:
                continue
    return out


def load_config(protocol: str, cache_path: Optional[Path]) -> ProtocolConfig:
    protocol = normalize_protocol(protocol)
    cfg = BUILTIN_CONFIGS[protocol]
    if not cache_path or not cache_path.exists():
        return cfg

    with cache_path.open("r", encoding="utf-8") as f:
        cache = json.load(f)

    entry = cache.get(protocol) or cache.get(protocol.lower())
    if not isinstance(entry, dict):
        return cfg

    op = entry.get("opcode_field") or entry.get("function_code") or entry.get("field")
    if not isinstance(op, dict):
        return cfg

    base = cfg.opcode_field
    field_spec = FieldSpec(
        name=str(op.get("name", base.name)),
        offset=int(op.get("offset", base.offset)),
        length=int(op.get("length", base.length)),
        endian=str(op.get("endian", base.endian)),
        values=_coerce_values(op.get("values", base.values)),
        bit_mask=op.get("bit_mask", base.bit_mask),
        bit_shift=int(op.get("bit_shift", base.bit_shift)),
        parser=str(op.get("parser", base.parser)),
    )
    return ProtocolConfig(
        name=protocol,
        transport=str(entry.get("transport", cfg.transport)),
        default_port=int(entry.get("default_port", cfg.default_port)),
        opcode_field=field_spec,
    )


class OpcodeParser:
    def __init__(self, config: ProtocolConfig) -> None:
        self.config = config
        self.field = config.opcode_field

    def parse_int(self, data: bytes) -> Optional[int]:
        if not data:
            return None
        if self.field.parser == "dhcp_option53":
            return self._parse_dhcp_option53(data)
        if self.field.parser == "bacnet_pdu_type":
            return self._parse_fixed(data)
        return self._parse_fixed(data)

    def _parse_fixed(self, data: bytes) -> Optional[int]:
        end = self.field.offset + self.field.length
        if self.field.offset < 0 or self.field.length <= 0 or len(data) < end:
            return None
        value = int.from_bytes(data[self.field.offset:end], self.field.endian, signed=False)
        if self.field.bit_mask is not None:
            value = (value & int(self.field.bit_mask)) >> self.field.bit_shift
        return value

    def _parse_dhcp_option53(self, data: bytes) -> Optional[int]:
        # DHCP options normally start at 240: BOOTP fixed header 236 + magic cookie 4.
        # 也兼容缺少 magic cookie 的截断文本，从 offset 开始扫描。
        start = 240 if len(data) >= 240 else max(0, self.field.offset)
        i = start
        while i < len(data):
            code = data[i]
            if code == 255:  # End
                break
            if code == 0:  # Pad
                i += 1
                continue
            if i + 1 >= len(data):
                break
            opt_len = data[i + 1]
            val_start = i + 2
            val_end = val_start + opt_len
            if val_end > len(data):
                break
            if code == 53 and opt_len >= 1:
                return data[val_start]
            i = val_end
        return self._parse_fixed(data)

    def parse_symbol(self, data: bytes) -> str:
        value = self.parse_int(data)
        if value is None:
            return NO_PACKET
        name = self.field.values.get(value, f"OP_{value}")
        return f"{value}:{name}"


@dataclass(frozen=True)
class State:
    symbol: str

    def __str__(self) -> str:
        return f"S({self.symbol})"


@dataclass
class Edge:
    src: str
    dst: str
    count: int = 0


class SSTG:
    def __init__(self) -> None:
        self.nodes: Counter[str] = Counter()
        self.edges: Dict[Tuple[str, str], Edge] = {}
        self.paths: List[List[str]] = []

    def add_path(self, path: List[str]) -> None:
        clean = [p for p in path if p and p != NO_PACKET]
        if not clean:
            return
        self.paths.append(clean)
        for node in clean:
            self.nodes[node] += 1
        for src, dst in zip(clean, clean[1:]):
            key = (src, dst)
            if key not in self.edges:
                self.edges[key] = Edge(src, dst, 0)
            self.edges[key].count += 1

    def to_dict(self, protocol: str, field: FieldSpec) -> Dict[str, object]:
        return {
            "protocol": protocol,
            "field": asdict(field),
            "nodes": [{"state": n, "count": c} for n, c in self.nodes.most_common()],
            "edges": [asdict(e) for e in sorted(self.edges.values(), key=lambda x: (-x.count, x.src, x.dst))],
            "paths": self.paths,
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        }

    def save(self, out_dir: Path, protocol: str, field: FieldSpec) -> None:
        out_dir.mkdir(parents=True, exist_ok=True)
        data = self.to_dict(protocol, field)

        with (out_dir / "sstg.json").open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        with (out_dir / "states.csv").open("w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(["state", "count"])
            for state, count in self.nodes.most_common():
                w.writerow([state, count])

        with (out_dir / "edges.csv").open("w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(["src", "dst", "count"])
            for edge in sorted(self.edges.values(), key=lambda x: (-x.count, x.src, x.dst)):
                w.writerow([edge.src, edge.dst, edge.count])

        with (out_dir / "paths.csv").open("w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(["path_id", "step", "state"])
            for path_id, path in enumerate(self.paths, 1):
                for step, state in enumerate(path, 1):
                    w.writerow([path_id, step, state])

        with (out_dir / "sstg.dot").open("w", encoding="utf-8") as f:
            f.write("digraph SSTG {\n")
            f.write('  rankdir=LR;\n  node [shape=box, style="rounded"];\n')
            for state, count in self.nodes.most_common():
                label = f"{state}\\ncount={count}"
                f.write(f'  "{state}" [label="{label}"];\n')
            for edge in sorted(self.edges.values(), key=lambda x: (-x.count, x.src, x.dst)):
                f.write(f'  "{edge.src}" -> "{edge.dst}" [label="{edge.count}"];\n')
            f.write("}\n")


def parse_packet_line(line: str) -> Tuple[Optional[str], Optional[bytes], bool]:
    raw_line = line.rstrip("\n")
    stripped = raw_line.strip()
    if not stripped:
        return None, None, True
    if stripped.startswith("#"):
        return None, None, stripped.startswith("# session") or stripped.startswith("# path")
    if stripped in {"---", "===", "***"}:
        return None, None, True

    direction = None
    m = re.match(r"^(C>|S>|client:|server:|send:|recv:|tx:|rx:)\s*(.*)$", stripped, flags=re.I)
    if m:
        direction = m.group(1).rstrip(":>").lower()
        stripped = m.group(2).strip()

    if stripped.lower().startswith("raw:"):
        return direction, stripped[4:].encode("utf-8", errors="ignore"), False

    cleaned = stripped.replace("\\x", " ").replace("0x", " ").replace("0X", " ")
    cleaned = re.sub(r"[^0-9a-fA-F]", "", cleaned)
    if cleaned and len(cleaned) % 2 == 0:
        try:
            return direction, bytes.fromhex(cleaned), False
        except ValueError:
            pass
    return direction, stripped.encode("utf-8", errors="ignore"), False


def read_paths(input_path: Path, parser: OpcodeParser, split_blank: bool) -> List[List[str]]:
    paths: List[List[str]] = []
    current: List[str] = []

    with input_path.open("r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            _direction, packet, is_split = parse_packet_line(line)
            if is_split and split_blank:
                if current:
                    paths.append(current)
                    current = []
                continue
            if packet is None:
                continue
            symbol = parser.parse_symbol(packet)
            current.append(symbol)

    if current:
        paths.append(current)
    return paths


def main() -> None:
    ap = argparse.ArgumentParser(description="从 txt 报文序列抽象 SSTG 状态图并保存。")
    ap.add_argument("--protocol", required=True, help=f"协议名：{', '.join(PROTOCOLS)}")
    ap.add_argument("--input", required=True, help="输入 txt 报文文件")
    ap.add_argument("--out", default=None, help="输出目录，默认 sstg_out_<protocol>_<timestamp>")
    ap.add_argument("--cache", default="protocol_field_cache.json", help="协议字段缓存 JSON，可选")
    ap.add_argument("--path-split", choices=["blank", "none"], default="blank", help="blank 表示空行/--- 分割路径；none 表示全文件一条路径")
    args = ap.parse_args()

    input_path = Path(args.input).expanduser().resolve()
    if not input_path.exists():
        raise FileNotFoundError(f"输入文件不存在: {input_path}")

    cache_path = Path(args.cache).expanduser().resolve() if args.cache else None
    if cache_path and not cache_path.exists():
        cache_path = None

    config = load_config(args.protocol, cache_path)
    parser = OpcodeParser(config)
    out_dir = Path(args.out or f"sstg_out_{config.name.replace(' ', '_')}_{int(time.time())}").expanduser().resolve()

    paths = read_paths(input_path, parser, split_blank=(args.path_split == "blank"))
    sstg = SSTG()
    for path in paths:
        sstg.add_path(path)
    sstg.save(out_dir, config.name, config.opcode_field)

    print("[+] SSTG 已生成")
    print(f"协议: {config.name}")
    print(f"功能码字段: name={config.opcode_field.name}, offset={config.opcode_field.offset}, length={config.opcode_field.length}, endian={config.opcode_field.endian}, parser={config.opcode_field.parser}")
    print(f"路径数: {len(sstg.paths)}")
    print(f"状态数: {len(sstg.nodes)}")
    print(f"边数: {len(sstg.edges)}")
    print(f"输出目录: {out_dir}")
    print(f"  - {out_dir / 'sstg.json'}")
    print(f"  - {out_dir / 'states.csv'}")
    print(f"  - {out_dir / 'edges.csv'}")
    print(f"  - {out_dir / 'paths.csv'}")
    print(f"  - {out_dir / 'sstg.dot'}")


if __name__ == "__main__":
    main()
