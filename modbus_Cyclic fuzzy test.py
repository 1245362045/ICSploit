import state_processing
import modbus_single_main
import time


# 主函数
def send():
    modbus_client = modbus_single_main.attempt_connection(ip_address, port)
    if modbus_client is None:
        return

    packet_number = 0
    for text_data in text_datas:
        packet_number += 1

        print(f"发送第{packet_number}个数据包: {text_data}")
        try:
            result = modbus_single_main.send_modbus_data(modbus_client, text_data, packet_number)
            time.sleep(0.1)  # 等待PLC响应
        except Exception as ex:
            print(f"发生错误，尝试重新连接: {ex}")
            modbus_client.close()
            modbus_client = modbus_single_main.attempt_connection(ip_address, port)

            if modbus_client is None:
                print("重新连接失败，终止程序")
                break

            try:
                modbus_single_main.send_modbus_data(modbus_client,text_data, packet_number)
            except Exception as ex2:
                print("重发数据仍然失败，继续发送下一个数据包")
                continue

    modbus_client.close()


if __name__ == "__main__":
    # 你的PLC的ip地址和端口
    ip_address = '192.168.2.1'  # PLC IP地址
    port = 502  # PLC端口号
    all_lists = state_processing.initialize_state("fuzzing/modbus_System status tracking.txt")
    result, user_request = state_processing.select_fuzzing(all_lists)
    flag = state_processing.write_list_to_txt(result, "fuzzing/state_fuzzing.txt")
    print(f"对应的状态路径请求响应有：{result}")
    print(f"对应的标志位为：{flag}")
    text_datas = state_processing.read_txt_to_list(flag, 'fuzzing/state_fuzzing.txt')
    print(f"测试用例为:{text_datas}")
    send()
