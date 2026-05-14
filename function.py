import ast

# 2. 将字典写入txt文件
def write_dict_to_txt(fcode_dict,filename="protocol_data.txt"):
    with open(filename, 'w') as file:
        for protocol_function, values in fcode_dict.items():
            # 写入每个Protocol function及其对应的值
            file.write(f"Protocol function :  {protocol_function}\n")
            for val in values:
                file.write(f"\t val:  {val}\n")

# 3. 从txt文件读取内容并恢复字典
def read_dict_from_txt(filename="protocol_data.txt"):
    result = {}
    with open(filename, 'r') as file:
        lines = file.readlines()
        current_protocol = None
        current_values = []
        for line in lines:
            if line.startswith("Protocol function :"):
                # 当前行表示一个新的Protocol function
                if current_protocol:
                    result[current_protocol] = current_values
                current_protocol = line.split(":")[1].strip()
                current_values = []
            elif line.startswith("\t val:"):
                # 当前行表示一个val项
                val = ast.literal_eval(line.split(":")[1].strip())
                current_values.append(val)
        # 最后一个Protocol function
        if current_protocol:
            result[current_protocol] = current_values
    return result

# 执行写入操作
# write_dict_to_txt()

# # 执行读取操作
# loaded_dict = read_dict_from_txt()
# print(loaded_dict)
