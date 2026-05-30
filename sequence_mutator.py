import random


def sequence_mutation(lst,position=2,step=2):
    """
    对列表中的每个元素，在每个插入位置随机复制1-8次，然后输出所有可能结果

    参数:
        lst (list): 输入的列表

    返回:
        list: 包含所有可能插入结果的列表，每个结果包括：
             - 被复制的元素
             - 复制次数
             - 插入位置
             - 生成的新列表
    """

    if not lst:
        return []

    results = []
    fc_list = []
    # 遍历列表中的每个元素（使用set避免重复处理相同元素）
    for element in set(lst):
        # 遍历所有可能的插入位置
        el=element[position:position+step]
        if el not in fc_list:
            fc_list.append(el)
        else:
            continue
        for insert_pos in range(len(lst) + 1):
            # 每个位置都随机决定复制次数(1-8次)
            copy_times = random.randint(1, 8)
            copied_elements = [element] * copy_times

            # 创建新列表并插入
            new_lst = lst.copy()
            new_lst[insert_pos:insert_pos] = copied_elements

            results.append({
                'element': element,
                'copies': copy_times,
                'position': insert_pos,
                'new_list': new_lst
            })

    return results


# 示例使用
if __name__ == "__main__":
    original_list = ['420624200014', '420624200114', '420724200014']
    print("原始列表:", original_list)

    all_results = sequence_mutation(original_list)

    # 打印所有结果
    print(f"\n共生成 {len(all_results)} 种可能结果:")
    for i, result in enumerate(all_results, 1):
        print(f"\n结果 {i}:")
        print(f"操作: 将元素 {result['element']} 复制 {result['copies']} 次插入到位置 {result['position']}")
        print("生成列表:", result['new_list'])