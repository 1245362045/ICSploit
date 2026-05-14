import snap7
import time
import dynamic_byte_mutation
#获取变异数据和原始数据
def read_elements_from_file(file_path):
    list1 = []
    list2 = []

    # 读取文件
    with open(file_path, 'r', encoding='utf-8') as file:
        for line in file:
            # 去掉行末的换行符并分割每一行
            elements = line.strip().split(',')
            # 检查是否真的有两个元素
            if len(elements) == 2:
                # 添加到对应的列表
                list1.append(elements[0])
                list2.append(elements[1])

    # 返回两个列表
    return list1, list2


#获取报文关键字值
def get_keyword(data,index,step):
    data=str(data)
    return data[index:index+step]

def add_to_list(lists, key, value):
    compare_list=[]
    for list in lists:
        key_list=[list[0],list[1]]
        compare_list.append(key_list)
    if key not in compare_list:
        key.append(value)
        lists.append(key)
    else:
        index=compare_list.index(key)
        lists[index].append(value)


def read_list_from_file(filename):
    # 创建一个空字典来存储结果
    result_list = []

    # 打开文件
    with open(filename, 'r') as file:
        # 遍历文件的每一行
        for line in file:
            # 去除行尾的换行符
            line = line.strip()
            result_list.append(line)
    return result_list


def save_list_to_file(lists, file_path):
    with open(file_path, 'w', encoding='utf-8') as file:
        for list in lists:
            file.write(f"{list}\n")


# 发送数据包
def send_data_packet(client, db_number, start_address, data):
    # 将十六进制字符串转换为字节串
    if len(data) % 2 != 0:
        data = data + '0'
    data_bytes = bytes.fromhex(data)
    client.db_write(db_number, start_address, data_bytes)


# 接收PLC反馈
def receive_feedback(client, db_number, start_address, length):
    feedback_raw = client.db_read(db_number, start_address, length)
    return feedback_raw




# 主程序
def main():
    # PLC连接设置
    PLC_IP = "192.168.2.1"  # PLC的IP地址
    PLC_RACK = 0  # PLC的机架号
    PLC_SLOT = 1  # PLC的插槽号
    DB_NUMBER = 1  # 数据块号，根据需要调整
    START_ADDRESS = 0  # 起始地址
    FEEDBACK_LENGTH = 100  # 假设反馈报文长度，根据需要调整
    req_index = 34
    rsp_index = 38
    req_step = 2
    rsp_step = 2
    Function_list = read_list_from_file('fuzzing/s7_System status tracking.txt')
    exception_filename = 'fuzzing/s7_exception_packets.txt'
    mutated_hex_data_list,original_hex_data_list = read_elements_from_file('seeds/s7_mutation.txt')
    client = snap7.client.Client()
    client.set_connection_type(3)
    with open(exception_filename, 'w'):
        pass
    for data_packet in mutated_hex_data_list:
        reqkeyword = get_keyword(data_packet, req_index, req_step)
        # print(reqkeyword)
        connected = False
        while not connected:
            num=1
            try:
                # 尝试连接到PLC
                if not client.get_connected():
                    client.connect(PLC_IP, PLC_RACK, PLC_SLOT)
                    print("连接到PLC.")
                connected = True

                # 发送数据包并接收反馈
                send_data_packet(client, DB_NUMBER, START_ADDRESS, data_packet)  # 发送数据包
                print(f"发送数据包: {data_packet}")
                time.sleep(0.05)  # 根据需要调整等待时间以等待PLC处理
                feedback = receive_feedback(client, DB_NUMBER, START_ADDRESS, FEEDBACK_LENGTH)
                result=feedback.hex()
                print(f"接收到的反馈: {result}")
                rspkeyword = get_keyword(result, rsp_index, rsp_step)
                Function_code = [reqkeyword, rspkeyword]
                add_to_list(Function_list, Function_code, result)


            except Exception as e:
                print(f"发生异常: {e}")
                with open(exception_filename, 'a') as f_exc:
                    f_exc.write(f"{data_packet}  \n")
                client.disconnect()
                print("尝试重新连接...")
                num+=1
                if num == 4:
                    break
                connected = False

                time.sleep(0.05)  # 等待一段时间后重新连接
    save_list_to_file(Function_list, 'fuzzing/s7_System status tracking.txt')
    client.disconnect()
    print("所有数据包发送完成，断开与PLC的连接。")


if __name__ == "__main__":
    dynamic_byte_mutation.mutator(input_file="seeds/s7_600.txt", output_file="seeds/s7_mutation.txt", mutation_rate=0.3)
    main()
