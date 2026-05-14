import random
import re


def read_protocol_format(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        return [line.rstrip() for line in f]


def parse_protocol_format(format_text):
    protocol_rules = {}
    current_function = None

    for line in format_text:
        line = line.strip()

        match_func = re.search(r"Protocol function\s*:\s*([0-9A-Fa-f]+)", line)
        if match_func:
            current_function = match_func.group(1).upper()
            protocol_rules[current_function] = []
            continue

        match_val = re.search(
            r"val:\s*\[(\d+),\s*'(\w+)',\s*([0-9.]+)\]",
            line
        )
        if match_val and current_function is not None:
            protocol_rules[current_function].append([
                int(match_val.group(1)),
                match_val.group(2),
                float(match_val.group(3))
            ])

    return protocol_rules



def mutate_char(c):
    """
    对单个十六进制字符执行变异:
    80% replace
    10% delete
    10% insert
    """

    hex_chars = '0123456789abcdef'

    mutation_type = random.choices(
        ['replace', 'delete', 'insert'],
        weights=[0.8, 0.1, 0.1],
        k=1
    )[0]

    # 替换
    if mutation_type == 'replace':
        new_char = random.choice(hex_chars.replace(c.lower(), ''))
        return new_char

    # 删除
    elif mutation_type == 'delete':
        return ''

    # 插入
    elif mutation_type == 'insert':
        inserted_char = random.choice(hex_chars)

        # 保留原字符并插入新字符
        # 可前插也可后插
        return c + inserted_char


def mutate_payload(payload, protocol_rules, function_index=8):
    payload = payload.lower()

    byte_start = function_index * 2
    byte_end = byte_start + 2

    if byte_end > len(payload):
        return payload

    function_code = payload[byte_start:byte_end].upper()

    if function_code not in protocol_rules:
        return payload

    payload_list = list(payload)
    pos = 0

    for char_count, state, score in protocol_rules[function_code]:
        end_pos = min(pos + char_count, len(payload_list))

        if state == "Static":
            pos += char_count
            continue

        if state == "Dynamic":
            for i in range(pos, end_pos):
                r = random.random()
                if r > score:
                    if random.random() < 0.5:
                        payload_list[i] = mutate_char(payload_list[i])

            pos += char_count

    return "".join(payload_list)

def run_mutation(data_file, payload, function_index):
    """
    执行协议payload变异

    参数:
        data_file: 协议规则文本文件
        payload: 原始payload(hex字符串)
        function_index: Protocol function所在字节位置(从0开始)

    返回:
        mutated_payload: 变异后的payload
    """

    # 读取协议格式文本
    format_text = read_protocol_format(data_file)

    # 解析规则
    protocol_rules = parse_protocol_format(format_text)

    # 执行变异
    mutated_payload = mutate_payload(
        payload,
        protocol_rules,
        function_index
    )

    # 输出信息
    # print("协议规则:")
    # print(protocol_rules)
    #
    # print("原始 payload:", payload)
    #
    # print("变异 payload:", mutated_payload)

    return mutated_payload

def read_hex_file(input_file):
    with open(input_file, 'r') as file:
        hex_data_list = file.readlines()
    return hex_data_list


def write_hex_file(data_list, output_file):
    with open(output_file, "w", encoding="utf-8") as f:
        for item in data_list:
            f.write(str(item))


if __name__ == "__main__":
    input_file="seeds/modbus_format.txt"
    data_file = "protocol_data.txt"
    payload = "380b00000006ff0401f40064"
    # Protocol function字节位置
    function_index = 8
    original_hex_data_list = read_hex_file(input_file)

    all_results = [run_mutation(data_file, data, function_index) for data in original_hex_data_list]
    # #
    print(all_results)
    write_hex_file(all_results,"seeds/modbus_mutation.txt")
    # mutated_payload = run_mutation(
    #     data_file,
    #     payload,
    #     function_index
    # )
