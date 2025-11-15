import random
import storage
import time

# 读取包含十六进制数的文本文件
def read_hex_file(input_file):
    with open(input_file, 'r') as file:
        hex_data_list = file.readlines()
    return hex_data_list

#变异策略
def mutate_hex_data(hex_data, mutation_rate, constant_fields):
    seed_value = time.time_ns()
    random.seed(seed_value)
    mutated_data = ""
    i = 0
    j = 0
    while i < len(hex_data):
        # 检查当前位置是否处于任何一个constant field中
        in_constant_field = False
        start=constant_fields[j][0]
        length=constant_fields[j][1]
        if i==constant_fields[j][0]+constant_fields[j][1]:
            j+=1
        if start <= i < start + length:
            in_constant_field = True


        if in_constant_field:
            # 如果当前位置在constant field中，直接添加字符，不进行突变
            mutated_data += hex_data[i]
            i += 1
            continue

        if random.random() < mutation_rate:
            mutation_type = random.choice(['replace', 'delete', 'insert'])

            if mutation_type == 'replace':
                mutated_data += random.choice('0123456789abcdef')
            elif mutation_type == 'delete':
                i += 1
                continue
            elif mutation_type == 'insert':
                mutated_data += random.choice('0123456789abcdef')

        else:
            mutated_data += hex_data[i]

        i += 1

    return mutated_data,hex_data


# 将变异后的数据保存到新文件
def save_mutated_hex_file(output_file, mutated_hex_data_list,original_data_list):
    with open(output_file, 'w') as f:
        for mutated_data, original_data in zip(mutated_hex_data_list, original_data_list):
            f.write(f"{mutated_data},{original_data}\n")

def mutator(input_file ="seeds/s7_600.txt", output_file = "seeds/s7_mutation.txt" , mutation_rate= 0.3):
    # input_file = "seeds/modbus_multiple_format.txt"  # 替换为包含原始十六进制数据的文本文件路径
    # output_file = "mutation/modbus_mutation.txt"  # 替换为要保存变异数据的文本文件路径
    # mutation_rate = 0.1  # 变异率，可以根据需要进行调整

    original_hex_data_list = read_hex_file(input_file)
    constant_fields = storage.get_constant_fields('Protocol format.txt')
    all_results = [mutate_hex_data(data.strip(), mutation_rate, constant_fields) for data in original_hex_data_list]
    mutated_hex_data_list,original_data_list = map(list, zip(*all_results))
    # mutated_hex_data_list,hex_data_list = [mutate_hex_data(data.strip(), mutation_rate,constant_fields) for data in original_hex_data_list]
    save_mutated_hex_file(output_file, mutated_hex_data_list,original_data_list)

    print("Mutation complete. Mutated data saved to", output_file)

if __name__ == "__main__":
    mutator()
    print("这是一个测试信息，只有在直接运行这个模块时才会出现。")