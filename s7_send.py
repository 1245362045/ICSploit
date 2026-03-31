import snap7
import time
import pretreatment
#
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
def send(text_datas):
    # PLC连接设置
    PLC_IP = "192.168.2.1"  # PLC的IP地址
    PLC_RACK = 0  # PLC的机架号
    PLC_SLOT = 1  # PLC的插槽号
    DB_NUMBER = 1  # 数据块号，根据需要调整
    START_ADDRESS = 0  # 起始地址
    FEEDBACK_LENGTH = 100  # 假设反馈报文长度，根据需要调整
    client = snap7.client.Client()
    client.set_connection_type(3)

    for data_packet in text_datas:
        connected = False
        while not connected:
           num = 1
           try:
                # 尝试连接到PLC
                if not client.get_connected():
                    client.connect(PLC_IP, PLC_RACK, PLC_SLOT)
                    print("连接到PLC.")
                connected = True
                send_data_packet(client, DB_NUMBER, START_ADDRESS, data_packet)
                # 发送数据包并接收反馈
                # send_data_packet(client, DB_NUMBER, START_ADDRESS, data_packet)  # 发送数据包
                print(f"发送数据包: {data_packet}")
                time.sleep(0.05)  # 根据需要调整等待时间以等待PLC处理
                feedback = receive_feedback(client, DB_NUMBER, START_ADDRESS, FEEDBACK_LENGTH)
                result=feedback.hex()
                print(f"接收到的反馈: {result}")
           except Exception as e:
                print(f"请求数据包：{data_packet} 发生异常: {e}")
                client.disconnect()
                print("尝试重新连接...")
                num += 1
                if num == 4:
                    break
                connected = False
                time.sleep(0.05)  # 等待一段时间后重新连接

    client.disconnect()
    print("所有数据包发送完成，断开与PLC的连接。")

if __name__ == "__main__":
    # 示例调用
    req_restored = pretreatment.read_hex_strings_from_file("s7.txt")
    print("req 数据：", req_restored)
    for i in range(30):
    # # text_datas=
        send(req_restored)