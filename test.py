
# import pretreatment

# def add_zeros_string(number, n):
#     """在数字后面添加n个0（字符串方法）"""
#     return int(str(number) + '0' * n)
#
# # 示例使用
# original_number = 140000000006010100000064
# zeros_to_add = 256
# result = add_zeros_string(original_number, zeros_to_add)
# print(f"{original_number} 后面添加 {zeros_to_add} 个0的结果是: {result}")


# hex_data = "1400000001060101000000640000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000"
# pretreatment.write_repeated_string_to_file("packet.txt", hex_data, 1000)


# def find_missing_fields(fixed_fields):
#     occupied_indices = set()
#
#     for index, length in fixed_fields.items():
#         # 当前字段占用的所有索引（index 到 index + length - 1）
#         occupied_indices.update(range(index, index + length))
#
#     if not occupied_indices:
#         return {}
#
#     max_index = max(occupied_indices)
#     all_indices = set(range(max_index + 1))
#     missing_indices = sorted(all_indices - occupied_indices)
#
#     # 创建动态字段字典，默认长度都为1
#     dynamic_fields = {index: 1 for index in missing_indices}
#     return dynamic_fields
#
#
# # 示例输入
# fixed_fields = {2: 3, 5: 1, 6: 1, 8: 3, 11: 1}
#
# # 获取动态字段
# dynamic_fields = find_missing_fields(fixed_fields)
#
# print("动态字段字典:", dynamic_fields)


# from Levenshtein import ratio
# import itertools
# import numpy as np
# import pretreatment
# # def extract_substrings(req, index, length):
# #     """从协议流量列表中提取指定位置和长度的子字符串"""
# #     return [item[index:index + length] for item in req if len(item) >= index + length]
#
# #提取协功能码部分，并计算相似度分数
# def LevenshteinSimilarityScore(value_list,index,step):
#     # value_list=[str(item) for item in value_list]
#     keyword=[]
#     SimilarityScore=[]
#     for el in value_list:
#         keyword.append(el[index:index+step])
#     combination_list = list(itertools.combinations(keyword, 2))  # 生成所有可能的两两组合列表
#     for each_com in combination_list:
#         SimilarityScore.append(ratio(each_com[0], each_com[1]))
#     SimilarityScore = np.array(SimilarityScore)
#     if len(SimilarityScore) == 0:
#         return 0
#     return SimilarityScore.mean()
#
#
# # 使用示例
# if __name__ == "__main__":
#     req, res = pretreatment.parse_pcapng("modbus_500.pcapng", 502)
#     index = 0
#     length = 2
#     req_hex = [data.hex() for data in req]
#     substrings = LevenshteinSimilarityScore(req_hex, index, length)
#
#     print(f"熵值: {substrings}")


# from Levenshtein import ratio
# import itertools
# import numpy as np

#
# def filter_function_codes(req_hex, candidate_dict):
#     """
#     过滤候选功能码字段，保留相似度大于0.4的字段
#     :param req_hex: 请求的十六进制字符串列表
#     :param candidate_dict: 候选功能码字典 {索引: 长度}
#     :return: 过滤后的新字典
#     """
#     filtered_dict = {}
#
#     for index, length in candidate_dict.items():
#         # 计算实际索引和长度（乘以2）
#         actual_index = index * 2
#         actual_length = length * 2
#
#         # 计算相似度分数
#         score = LevenshteinSimilarityScore(req_hex, actual_index, actual_length)
#
#         # 如果分数大于0.4则保留
#         if score > 0.4:
#             filtered_dict[index] = length
#
#     return filtered_dict
#
#
# # 示例使用
# if __name__ == "__main__":
#     # 示例数据
#     req_hex = [
#         "0103040001000108",  # 功能码01
#         "0103040002000207",  # 功能码01
#         "0f03040003000306",  # 功能码0f
#     ]
#
#     # 候选功能码字段 {索引: 长度}
#     candidate_dict = {0: 1, 1: 1, 7: 1}
#
#     # 过滤功能码
#     result = filter_function_codes(req_hex, candidate_dict)
#     print("过滤后的功能码字段:", result)






# def concatenate_substrings(list1, list2, index, length):
#     result_list = []
#     min_len = min(len(list1), len(list2))
#
#     for i in range(min_len):
#         # 转换为字符串处理非字符串输入
#         str1 = str(list1[i]) if list1[i] is not None else ""
#         str2 = str(list2[i]) if list2[i] is not None else ""
#
#         # 处理索引越界
#         start1 = min(index, len(str1))
#         end1 = min(index + length, len(str1))
#         substr1 = str1[start1:end1]
#
#         start2 = min(index, len(str2))
#         end2 = min(index + length, len(str2))
#         substr2 = str2[start2:end2]
#
#         result_list.append(substr1 + substr2)
#
#     return result_list

#
# # 示例使用
# if __name__ == "__main__":
#     # 示例数据
#     list1 = ["abcdef", "ghijkl", "mnopqr"]
#     list2 = ["123456", "789012", "345678"]
#
#     # 拼接索引1开始，长度2的子串
#     result = concatenate_substrings(list1, list2, 1, 2)
#     print("拼接结果:", result)  # 输出: ['bc23', 'ij90', 'no45']


# from itertools import product
#
#
# def extract_hex_parts(hex_list, positions):
#     """
#     从十六进制字符串列表中提取指定位置的部分
#     :param hex_list: 十六进制字符串列表
#     :param positions: 位置字典 {索引: 长度}
#     :return: 字典 {索引: [各部分字符串]}
#     """
#     parts_dict = {}
#     for index, length in positions.items():
#         parts = []
#         for hex_str in hex_list:
#             start = index
#             end = start + length
#             part = hex_str[start:end] if end <= len(hex_str) else hex_str[start:]
#             parts.append(part)
#         parts_dict[index] = parts
#     return parts_dict


# from itertools import product


# def extract_separate_positions(hex_list, positions_dict):
#     """
#     独立提取每个位置的子串
#     :return: 字典 {索引: [子串1, 子串2, ...]}
#     """
#     result = {}
#     for index, length in positions_dict.items():
#         result[index] = [hex_str[index:index + length] for hex_str in hex_list]
#     return result
#
#
# def generate_all_combinations(req_hex, res_hex, cfunction_req, cfunction_res):
#     """
#     生成所有请求和响应位置的一一对应组合
#     :return: 所有可能的组合列表
#     """
#     # 1. 独立提取请求和响应的每个位置
#     req_parts = extract_separate_positions(req_hex, cfunction_req)
#     res_parts = extract_separate_positions(res_hex, cfunction_res)
#
#     # 2. 生成所有请求位置×响应位置的组合
#     all_results = []
#     for req_index, req_values in req_parts.items():
#         for res_index, res_values in res_parts.items():
#             # 一一对应拼接
#             combined = [req + res for req, res in zip(req_values, res_values)]
#             all_results.append({
#                 'req_pos': req_index,
#                 'res_pos': res_index,
#                 'combined': combined
#             })
#
#     return all_results
#
#
# # 示例使用
# if __name__ == "__main__":
#     req_hex = ["0103040001000108", "0103040002000207", "0f03040003000306"]
#     res_hex = ["0101040001000109", "0101040002000208", "0f01040003000307"]
#
#     # # 情况1
#     cfunction_req = {1: 2}
#     cfunction_res = {0: 1, 1: 1}
#     # print("情况1结果:")
#     # for group in generate_all_combinations(req_hex, res_hex, cfunction_req, cfunction_res):
#     #     print(f"请求位置{group['req_pos']}+响应位置{group['res_pos']}: {group['combined']}")
#     req_parts = extract_separate_positions(req_hex, cfunction_req)
#     res_parts = extract_separate_positions(res_hex, cfunction_res)
#     print(req_parts,res_parts)
#     # 情况2
#     # cfunction_req = {0: 2, 1: 1}
#     # cfunction_res = {0: 1, 7: 1}
#     # print("\n情况2结果:")
#     # for group in generate_all_combinations(req_hex, res_hex, cfunction_req, cfunction_res):
#     #     print(f"请求位置{group['req_pos']}+响应位置{group['res_pos']}: {group['combined']}")

# from statistics import mean
# from Levenshtein import ratio
# list1 = ["hello", "world", "python","hello"]
# list2 = ["hello", "world", "pyhton","hello"]
#
# # individual_results = [ratio(a, b) == 1 for a, b in zip(list1, list2)]
# individual_results = mean([ratio(a, b) == 1 for a, b in zip(list1, list2)]) > 0.7
#
# print(individual_results)


#写入读取测试
from scapy.all import *
from scapy.layers.inet import TCP, IP,UDP
def parse_pcapng(file_path,port):
    # 读取pcapng文件
    packets = rdpcap(file_path)

    requests = []  # 存储请求报文载荷
    responses = []  # 存储响应报文载荷
    # 自动检测协议类型
    protocol_type = None  # 'tcp' 或 'udp'

    for pkt in packets:
        if IP not in pkt:
            continue  # 不是 IP 数据包

            # 自动检测协议类型（只在第一次检测时设置）
        if protocol_type is None:
            if TCP in pkt:
                protocol_type = 'tcp'
            elif UDP in pkt:
                protocol_type = 'udp'
            else:
                continue  # 不是 TCP 或 UDP 数据包
                # 根据检测到的协议类型进行解析

        if (protocol_type == 'tcp' and TCP in pkt) or (protocol_type == 'udp' and UDP in pkt):
            transport_layer = pkt[TCP] if protocol_type == 'tcp' else pkt[UDP]
            if Raw in pkt:
                payload = bytes(pkt[Raw].load)

                # 根据端口判断是请求还是响应
                if transport_layer.dport == port:
                    requests.append(payload)
                elif transport_layer.sport == port:
                    responses.append(payload)
    print(f"检测到的协议类型: {protocol_type.upper() if protocol_type else '未知'}")
    return requests


def write_hex_strings_to_file(filename, hex_strings_list, mode='w'):
    """
    将十六进制字符串列表写入文件，每行一个字符串

    Args:
        filename (str): 目标文件名（如 "output.txt"）
        hex_strings_list (list): 包含十六进制字符串的列表
        mode (str): 文件写入模式，默认 'w'（覆盖），可选 'a'（追加）
    """
    with open(filename, mode) as f:
        for hex_str in hex_strings_list:
            f.write(hex_str + '\n')
    print(f"数据已写入 {filename}（模式: {'覆盖' if mode == 'w' else '追加'}）")

req = parse_pcapng("s7,problem3.pcapng",102)
req_hex = [data.hex() for data in req]
write_hex_strings_to_file("s7.txt", req_hex)