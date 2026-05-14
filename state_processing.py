import storage
import dynamic_byte_mutation
import ast
def initialize_state(file_name):
    # 存储结果的列表
    all_lists = []

    # 打开文件
    with open(file_name, 'r') as file:
        # 逐行读取文件内容
        for line in file:
            # 去除行末尾的换行符
            line = line.strip()
            # 将字符串解析成实际的列表
            list_from_line = ast.literal_eval(line)
            # 输出解析后的列表
            print(list_from_line)
            # 将解析后的列表添加到总列表中
            all_lists.append(list_from_line)
    return all_lists

# # 打印总列表
# print(all_lists)

def select_fuzzing(lists):
    # 要求用户输入两个值
    user_value1 = input("请输入请求功能码: ")
    user_value2 = input("请输入响应功能码: ")
    # 将用户输入转换为字符串
    user_str1 = str(user_value1)
    user_str2 = str(user_value2)
    result=None
    for list in lists:
        if list[0] == user_str1 and list[1] == user_str2:
            result=list[2:]
            print(result)
    return result,user_str1

def substring_with_step(s, index, step):
    """
    从 index 开始，截取长度为 step 的子字符串。

    :param s: 原始字符串
    :param index: 起始索引
    :param step: 子字符串长度
    :return: 截取的子字符串
    """
    # 检查参数有效性
    if index < 0 or step < 0:
        raise ValueError("index 和 step 必须是非负数")
    if index >= len(s):
        return ""

    # 使用切片操作截取子字符串
    return s[index:index + step]

def replace_substring(s, index, step, request):
    """
    将字符串 s 中从 index 开始长度为 step 的部分替换为 request，返回新的字符串。

    :param s: 原始字符串
    :param index: 起始索引
    :param step: 替换部分的长度
    :param request: 替换的新字符串
    :return: 替换后的新字符串
    """
    # 检查参数有效性
    if index < 0 or step < 0:
        raise ValueError("index 和 step 必须是非负数")
    if index >= len(s):
        return s + request  # 如果 index 超出字符串 s 的长度，则直接将 request 追加到 s 后

    # 构造新的字符串
    new_string = s[:index] + request + s[index + step:]
    return new_string

def write_list_to_txt(char_list, file_name):
    """
    将字符列表写入到一个 txt 文件中，每个元素占一行。

    :param char_list: 待写入文件的字符列表
    :param file_name: txt 文件名
    """
    if char_list != None:
        with open(file_name, 'w', encoding='utf-8') as file:
            for char in char_list:
                file.write(char + '\n')
            return True
    else:
        print("写入列表不能为None")
        return False


def read_txt_to_list(flag,file_name):
    """
    从 txt 文件中读取内容，并将每行内容存储到一个列表中。

    :param file_name: txt 文件名
    :return: 包含文件内容的字符列表
    """
    if flag==True:
        char_list = []
        constant_fields = storage.get_constant_fields('Protocol format.txt')
        with open(file_name, 'r', encoding='utf-8') as file:
            for line in file:
                line,_=dynamic_byte_mutation.mutate_hex_data(line,0.3,constant_fields)
                request_key_fields = storage.get_request_key_fields('Protocol format.txt')
                index = request_key_fields[0][0]
                step = request_key_fields[0][1]
                if user_request != substring_with_step(line,index,step):
                    line=replace_substring(line, index, step, user_request)
                char_list.append(line.strip())  # 使用 strip() 去除每行末尾的换行符
        return char_list
    else:
        print("无法读取")
# file_name='fuzzing/modbus_System status tracking.txt'
file_name="fuzzing/s7_System status tracking.txt"
all_lists=initialize_state(file_name)
result,user_request = select_fuzzing(all_lists)
flag=write_list_to_txt(result,"fuzzing/state_fuzzing.txt")
print(f"对应的状态路径请求响应有：{result}")
print(f"对应的标志位为：{flag}")
text_data=read_txt_to_list(flag,'fuzzing/state_fuzzing.txt')
print(f"测试用例为:{text_data}")