import S7_single_main as s7


def generate_hex_variations(hex_string, index, step):

    if len(hex_string) < index + step:
        raise ValueError("The step extends beyond the length of the hex string")

    hex_list = list(hex_string)
    print(hex_list)

    max_value = 16 ** step

    variations = []


    for i in range(max_value):
        new_value_hex = f"{i:0{step}x}"
        new_hex_list = hex_list[:index] + list(new_value_hex) + hex_list[index + step:]
        variations.append(''.join(new_hex_list))
    return variations

def main(data_list):
    # PLC连接设置
    PLC_IP = "192.168.2.1"  # PLC的IP地址
    PLC_RACK = 0  # PLC的机架号
    PLC_SLOT = 1  # PLC的插槽号
    DB_NUMBER = 1  # 数据块号，根据需要调整
    START_ADDRESS = 0  # 起始地址
    FEEDBACK_LENGTH = 100  # 假设反馈报文长度，根据需要调整
    exception_filename = 'fuzzing/s7_exception_packets.txt'

    client = s7.snap7.client.Client()
    client.set_connection_type(3)

    for data_packet in data_list:
        connected = False
        while not connected:
            try:
                # 尝试连接到PLC
                if not client.get_connected():
                    client.connect(PLC_IP, PLC_RACK, PLC_SLOT)
                    print("连接到PLC.")
                connected = True

                # 发送数据包并接收反馈
                s7.send_data_packet(client, DB_NUMBER, START_ADDRESS, data_packet)  # 发送数据包
                print(f"发送数据包: {data_packet}")
                s7.time.sleep(0.05)  # 根据需要调整等待时间以等待PLC处理
                feedback = s7.receive_feedback(client, DB_NUMBER, START_ADDRESS, FEEDBACK_LENGTH)
                result=feedback.hex()
                print(f"接收到的反馈: {result}")

            except Exception as e:
                print(f"发生异常: {e}")
                with open(exception_filename, 'a') as f_exc:
                    f_exc.write(f"{data_packet}  \n")
                client.disconnect()
                print("尝试重新连接...")
                connected = False
                s7.time.sleep(0.05)  # 等待一段时间后重新连接
    client.disconnect()
    print("所有数据包发送完成，断开与PLC的连接。")

results=s7.read_list_from_file("seeds/s7_600.txt")
index = 34
step = 2

variations = generate_hex_variations(results[0], index, step)
for variation in variations:
    print(variation)
main(variations)