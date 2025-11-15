from pymodbus.client import ModbusTcpClient
from pymodbus.exceptions import ModbusException, ModbusIOException, ConnectionException
import time
import mutation
import round_mutation


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

# 尝试连接到PLC
def attempt_connection(ip, port):
    client = ModbusTcpClient(ip, port=port)
    try:
        if not client.connect():
            print("无法连接到PLC")
            return None
    except Exception as e:
        print(f"连接到PLC时出现异常: {e}")
        return None
    return client


# 发送Modbus数据并接收响应
def send_modbus_data(modbus_client, data_hex, pkt_number):
    data = data_hex.strip()
    message = bytes.fromhex(data)  # 将十六进制字符串转换为字节
    result = None  # 初始化为None
    try:
        # 发送字节消息
        modbus_client.socket.send(message)

        # 接收响应
        response = modbus_client.socket.recv(1024)
        response_hex = response.hex()

        print(f"第{pkt_number}个数据包回复正常: {response_hex}")
        result =response_hex
    except Exception as e:
        error_message = f"数据包 {pkt_number} : {data} - 错误类型: {e}"
        # 检查异常类型并追加具体信息
        if isinstance(e, ModbusIOException):
            error_message += " - Modbus I/O 异常"
        elif isinstance(e, ConnectionException):
            error_message += " - 连接异常"
        elif isinstance(e, ModbusException):
            error_message += " - 通用Modbus异常"
        else:
            error_message += " - 未知异常"

        # 打印并记录异常信息
        with open(exception_filename, 'a') as f_exc:
            f_exc.write(f"{data},    {error_message}  \n")

        print(error_message)
        raise e  # 再抛出异常，以便上层处理重连逻辑
    return result

def division_to_percentage(num1, num2):
    if num2 == 0:
        return "除数不能为零"
    result = num1 / num2
    percentage = "{:.2%}".format(result)
    return percentage


# 主函数
def send():

    with open(exception_filename, 'w') :
        pass
    acc_number = 0
    packet_number = 0
    TCAR=0
    for mutated_hex_data in mutated_hex_data_list:
        modbus_client = attempt_connection(ip_address, port)
        if modbus_client is None:
            continue
        reqkeyword=get_keyword(mutated_hex_data,req_index,req_step)
        packet_number += 1
        # print(packet_number)
        print(f"发送第{packet_number}个数据包: {mutated_hex_data}")

        try:
            result = send_modbus_data(modbus_client, mutated_hex_data, packet_number)
            if result !=None:
                rspkeyword=get_keyword(result,rsp_index,rsp_step)
            acc_number+=1
            # print(acc_number)
            Function_code=[reqkeyword,rspkeyword]
            print(Function_code)
            add_to_list(Function_list,Function_code,result)
            print(Function_list)
            time.sleep(0.1)  # 等待PLC响应
        except Exception as ex:
            print(f"发生错误，尝试重新连接: {ex}")
            modbus_client.close()
            modbus_client = attempt_connection(ip_address, port)

            if modbus_client is None:
                print("重新连接失败，终止程序")
                break

            try:
                send_modbus_data(modbus_client,mutated_hex_data, packet_number)
            except Exception as ex2:
                print("重发数据仍然失败，继续发送下一个数据包")
                continue
        modbus_client.close()
    TCAR=division_to_percentage(acc_number,packet_number)
    print(TCAR)
    # print(Function_list)
    save_list_to_file(Function_list, 'fuzzing/modbus_System status tracking.txt')


# 运行主函数
if __name__ == "__main__":
    # mutation.mutator(input_file="seeds/modbus_multiple_format.txt", output_file="seeds/modbus_mutation.txt", mutation_rate=0.3)
    round_mutation.mutator(input_file="seeds/modbus_multiple_format.txt", output_file="seeds/modbus_mutation.txt",mutation_rate=0)
    # 你的PLC的ip地址和端口
    ip_address = '192.168.2.1'  # PLC IP地址
    port = 502  # PLC端口号
    Function_list = read_list_from_file('fuzzing/modbus_System status tracking.txt')
    # 保存异常和回复信息的文本文件名
    exception_filename = 'fuzzing/modbus_exception_packets.txt'
    req_index = 14
    rsp_index = 14
    req_step = 2
    rsp_step = 2
    mutated_hex_data_list, original_hex_data_list = read_elements_from_file('seeds/modbus_mutation.txt')
    print(mutated_hex_data_list)
    print(original_hex_data_list)
    send()
