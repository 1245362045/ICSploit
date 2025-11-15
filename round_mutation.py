import random

# 读取包含十六进制数的文本文件
def read_hex_file(input_file):
    with open(input_file, 'r') as file:
        hex_data_list = file.readlines()
    return hex_data_list

# 实施随机变异策略
def mutate_hex_data(hex_data, mutation_rate):
    mutated_data = ""
    for char in hex_data:
        if random.random() < mutation_rate:
            # mutation_type = random.choice(['replace', 'delete', 'insert'])
            #
            # if mutation_type == 'replace':
            mutated_data += random.choice('0123456789abcdef')
            # elif mutation_type == 'delete':
            #     continue
            # elif mutation_type == 'insert':
            #     mutated_data += random.choice('0123456789ABCDEF')
        else:
            mutated_data += char
    return mutated_data

# 将变异后的数据保存到新文件
def save_mutated_hex_file(output_file, mutated_data_list):
    with open(output_file, 'w') as file:
        for data in mutated_data_list:
            file.write(data+"\n")

def mutator(input_file ="seeds/modbus_multiple_format.txt", output_file = "seeds/modbus_mutation.txt" , mutation_rate= 0.1):
    # input_file = "seeds/modbus_multiple_format.txt"  # 替换为包含原始十六进制数据的文本文件路径
    # output_file = "mutation/mutation.txt"  # 替换为要保存变异数据的文本文件路径
    # mutation_rate = 0.1  # 变异率，可以根据需要进行调整

    original_hex_data_list = read_hex_file(input_file)
    mutated_hex_data_list = [mutate_hex_data(data.strip(), mutation_rate) for data in original_hex_data_list]
    print(mutated_hex_data_list)
    save_mutated_hex_file(output_file, mutated_hex_data_list)

    print("Mutation complete. Mutated data saved to", output_file)

if __name__ == "__main__":
    print("这是一个测试信息，只有在直接运行这个模块时才会出现。")
    mutator()